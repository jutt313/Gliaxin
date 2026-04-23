import asyncio
import json
import math
import os
import re
import uuid
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api_key_auth import verify_api_key, require_write
from database import get_pool
from worker import embed_query, process_pending
from logger import get_logger

log = get_logger("gliaxin.memory")

router = APIRouter(prefix="/v1/memory", tags=["memory"])

VALID_CATEGORIES = {"job", "ideas", "problems", "personal", "decisions", "other"}
VALID_MEMORY_TYPES = {"episodic", "semantic", "procedural"}
CURRENT_INVENTORY_CLOSURE_TAGS = {
    "lifecycle/problem-resolved", "lifecycle/task-completed", "lifecycle/plan-step-done",
    "lifecycle/workaround-removed", "lifecycle/incident-status-changed", "lifecycle/feature-live",
    "lifecycle/migration-deployed", "lifecycle/access-rule-changed", "lifecycle/ownership-changed",
    "lifecycle/deadline-status-changed", "lifecycle/decision-changed",
}


class TurnMessage(BaseModel):
    role: str
    content: str


class AddMemoryBody(BaseModel):
    end_user_id: str
    agent_id: Optional[str] = None
    scope: Optional[str] = "agent"
    messages: Optional[list[TurnMessage]] = None
    content: Optional[str] = None
    metadata: Optional[dict] = None


class ForgetBody(BaseModel):
    end_user_id: str


class ResolveBody(BaseModel):
    conflict_id: str
    decision: Optional[str] = None
    resolution: Optional[str] = None


class ReprocessBody(BaseModel):
    end_user_id: str


def _row_to_jsonable(row) -> dict:
    out = {}
    for k, v in dict(row).items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            out[k] = str(v)
        else:
            out[k] = v
    return out


def _coerce_page_size(page_size: Optional[int], limit: Optional[int], default: int = 50) -> int:
    return page_size or limit or default


def _normalize_resolution(body: ResolveBody) -> tuple[str, str]:
    raw_value = (body.resolution or body.decision or "").strip()
    mapping = {"confirm": "confirm", "keep_new": "confirm", "reject": "reject", "keep_old": "reject"}
    normalized = mapping.get(raw_value)
    if not normalized:
        raise HTTPException(status_code=400, detail="resolution must be keep_old/keep_new or decision must be confirm/reject")
    return raw_value, normalized


def _query_targets_current_problem_inventory(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    explicit_patterns = (
        r"\b(current|open|active|remaining|unresolved|ongoing)\s+(problems?|issues?|bugs?|incidents?)\b",
        r"\b(problems?|issues?|bugs?|incidents?)\s+(are\s+)?(still\s+)?(open|active|remaining|unresolved|ongoing)\b",
        r"\bwhat\s+(problems?|issues?|bugs?|incidents?)\s+(are\s+)?(still\s+)?(open|active|remaining|left)\b",
    )
    if any(re.search(p, normalized) for p in explicit_patterns):
        return True
    tokens = set(re.findall(r"\w+", normalized))
    return bool(tokens & {"problem", "problems", "issue", "issues", "bug", "bugs"}) and \
           bool(tokens & {"current", "open", "active", "remaining", "remain", "left", "unresolved", "ongoing"})


def _query_targets_current_work_inventory(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    explicit_patterns = (
        r"\bwhat\s+(is|work(?:'s| is)?)\s+left\b",
        r"\bwhat\s+work\s+is\s+left\b",
        r"\bwhat\s+tasks?\s+(are\s+)?left\b",
        r"\bwhat\s+is\s+remaining\b",
        r"\bwhat\s+remains\b",
        r"\bremaining\s+work\b",
    )
    if any(re.search(p, normalized) for p in explicit_patterns):
        return True
    tokens = set(re.findall(r"\w+", normalized))
    return "left" in tokens and bool(tokens & {"work", "task", "tasks", "todo", "todos", "remaining", "remain"})


def _has_current_inventory_closure_tag(memory: dict) -> bool:
    return any(tag in CURRENT_INVENTORY_CLOSURE_TAGS for tag in (memory.get("tags") or []))


async def _get_or_create_vault(conn, project_id: str, end_user_id: str) -> str:
    row = await conn.fetchrow(
        'SELECT vault_id FROM "Vault" WHERE project_id = $1 AND end_user_id = $2',
        project_id, end_user_id,
    )
    if row:
        await conn.execute('UPDATE "Vault" SET last_active_at = now() WHERE vault_id = $1', row["vault_id"])
        return str(row["vault_id"])
    vault_id = str(uuid.uuid4())
    await conn.execute(
        'INSERT INTO "Vault" (vault_id, project_id, end_user_id, last_active_at) VALUES ($1, $2, $3, now())',
        vault_id, project_id, end_user_id,
    )
    return vault_id


async def _get_vault_or_404(conn, project_id: str, end_user_id: str) -> str:
    row = await conn.fetchrow(
        'SELECT vault_id FROM "Vault" WHERE project_id = $1 AND end_user_id = $2',
        project_id, end_user_id,
    )
    if not row:
        # Fallback: personal project default vault (end_user_id IS NULL)
        row = await conn.fetchrow(
            'SELECT vault_id FROM "Vault" WHERE project_id = $1 AND end_user_id IS NULL',
            project_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Vault not found for this end_user_id")
    return str(row["vault_id"])


def _run_worker_bg(vault_id: Optional[str] = None) -> None:
    if os.getenv("TESTING"):
        return
    try:
        asyncio.ensure_future(process_pending(vault_id))
    except RuntimeError:
        pass


VALID_SCOPES = {"agent", "project"}
VALID_ROLES  = {"user", "assistant"}


async def _validate_agent(conn, project_id: str, agent_id: str) -> None:
    agent = await conn.fetchrow(
        'SELECT project_id FROM "Agent" WHERE agent_id = $1 AND deleted_at IS NULL',
        agent_id,
    )
    if not agent or str(agent["project_id"]) != project_id:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/add")
async def add_memory(body: AddMemoryBody, auth: dict = Depends(verify_api_key)):
    require_write(auth)
    if not body.end_user_id:
        raise HTTPException(status_code=400, detail="end_user_id is required")

    has_turn = body.messages is not None and len(body.messages) > 0
    has_legacy = body.content and body.content.strip()

    if not has_turn and not has_legacy:
        raise HTTPException(status_code=400, detail="messages or content is required")

    scope = (body.scope or "agent").strip()
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="scope must be 'agent' or 'project'")

    if has_turn:
        if not body.agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required for turn-based ingest")
        for msg in body.messages:
            if msg.role not in VALID_ROLES:
                raise HTTPException(status_code=400, detail=f"role must be 'user' or 'assistant', got '{msg.role}'")
            if not msg.content or not msg.content.strip():
                raise HTTPException(status_code=400, detail="each message must have non-empty content")

    project_id = auth["project_id"]
    pool = await get_pool()

    async with pool.acquire() as conn:
        vault_id = await _get_or_create_vault(conn, project_id, body.end_user_id)

        if body.agent_id:
            await _validate_agent(conn, project_id, body.agent_id)

        metadata_json = json.dumps(body.metadata) if body.metadata else None

        if has_turn:
            turn_id = str(uuid.uuid4())
            raw_ids = []
            for idx, msg in enumerate(body.messages):
                raw_id = str(uuid.uuid4())
                await conn.execute(
                    '''INSERT INTO "LayerA"
                       (raw_id, vault_id, project_id, agent_id, content, processing_status,
                        metadata, turn_id, role, message_index, scope_hint)
                       VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8,$9,$10,$11)''',
                    raw_id, vault_id, project_id, body.agent_id,
                    msg.content.strip(), "pending", metadata_json,
                    turn_id, msg.role, idx, scope,
                )
                raw_ids.append(raw_id)
            await conn.execute(
                '''INSERT INTO "AuditLog" (log_id, project_id, vault_id, agent_id, action, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb)''',
                str(uuid.uuid4()), project_id, vault_id, body.agent_id, "add",
                json.dumps({"turn_id": turn_id, "raw_ids": raw_ids, "scope": scope}),
            )
        else:
            raw_id = str(uuid.uuid4())
            await conn.execute(
                '''INSERT INTO "LayerA"
                   (raw_id, vault_id, project_id, agent_id, content, processing_status, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)''',
                raw_id, vault_id, project_id, body.agent_id,
                body.content.strip(), "pending", metadata_json,
            )
            await conn.execute(
                '''INSERT INTO "AuditLog" (log_id, project_id, vault_id, agent_id, action, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb)''',
                str(uuid.uuid4()), project_id, vault_id, body.agent_id, "add",
                json.dumps({"raw_id": raw_id}),
            )

    _run_worker_bg(vault_id)

    if has_turn:
        return {"turn_id": turn_id, "raw_ids": raw_ids, "status": "queued"}
    return {"raw_id": raw_id, "status": "queued"}


@router.get("/search")
async def search_memory(
    end_user_id: str = Query(...),
    query: str = Query(...),
    limit: int = Query(5, ge=1, le=50),
    include_resolved: Optional[bool] = Query(None),
    agent_id: Optional[str] = Query(None),
    auth: dict = Depends(verify_api_key),
):
    if not query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    project_id = auth["project_id"]
    pool = await get_pool()

    async with pool.acquire() as conn:
        vault_id = await _get_vault_or_404(conn, project_id, end_user_id)
        if agent_id:
            await _validate_agent(conn, project_id, agent_id)

        try:
            embedding = await embed_query(query)
        except Exception as exc:
            log.error("embedding failed", error=str(exc))
            raise HTTPException(status_code=503, detail="Search temporarily unavailable")

        vec_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
        kw_pattern = f"%{query.strip()}%"
        candidate_limit = max(limit * 10, 100)

        select_cols = (
            'memory_id, content, category, memory_type, importance, status, '
            'slot, agent_id, scope, tags, created_at, parent_id, related_ids, '
            '(embedding <=> $1::vector) AS distance'
        )

        current_problem_inventory = _query_targets_current_problem_inventory(query)
        current_work_inventory = _query_targets_current_work_inventory(query)
        effective_include_resolved = include_resolved
        if effective_include_resolved is None:
            effective_include_resolved = not (current_problem_inventory or current_work_inventory)

        statuses = ["active", "resolved"] if effective_include_resolved else ["active"]
        vec_where = 'vault_id = $2 AND status = ANY($3)'
        kw_where = 'vault_id = $2 AND status = ANY($3) AND content ILIKE $4'
        vec_params: list[Any] = [vec_str, vault_id, statuses]
        kw_params: list[Any] = [vec_str, vault_id, statuses, kw_pattern]

        if agent_id:
            vec_where += " AND (agent_id = $4 OR scope = 'project')"
            vec_params.append(agent_id)
            kw_where += " AND (agent_id = $5 OR scope = 'project')"
            kw_params.append(agent_id)
        else:
            vec_where += " AND scope = 'project'"
            kw_where += " AND scope = 'project'"

        vec_sql = f'SELECT {select_cols} FROM "LayerB" WHERE {vec_where} ORDER BY embedding <=> $1::vector LIMIT {candidate_limit}'
        kw_sql  = f'SELECT {select_cols} FROM "LayerB" WHERE {kw_where} ORDER BY importance DESC, embedding <=> $1::vector LIMIT {candidate_limit}'

        vec_rows = await conn.fetch(vec_sql, *vec_params)
        kw_rows  = await conn.fetch(kw_sql, *kw_params)

        merged: dict[str, dict] = {}
        for r in vec_rows:
            m = _row_to_jsonable(r)
            m["kw_match"] = False
            merged[m["memory_id"]] = m
        for r in kw_rows:
            m = _row_to_jsonable(r)
            mid = m["memory_id"]
            if mid in merged:
                merged[mid]["kw_match"] = True
            else:
                m["kw_match"] = True
                merged[mid] = m

        query_tokens = {w.lower() for w in re.sub(r"[^\w\s]", " ", query).split() if len(w) >= 2}
        for m in merged.values():
            if not m.get("kw_match") and query_tokens:
                content_lower = (m.get("content") or "").lower()
                slot_text = (m.get("slot") or "").replace("_", " ").lower()
                tags_text = " ".join(m.get("tags") or []).lower()
                combined = f"{content_lower} {slot_text} {tags_text}"
                m["token_match"] = any(tok in combined for tok in query_tokens)
                m["tag_match"] = any(
                    tok == seg
                    for tok in query_tokens
                    for tag in (m.get("tags") or [])
                    for seg in tag.lower().replace("/", " ").split()
                )
            else:
                m["token_match"] = bool(m.get("kw_match"))
                m["tag_match"] = bool(m.get("kw_match"))

        results = list(merged.values())
        results = [
            m for m in results
            if m.get("kw_match") or m.get("token_match") or m.get("tag_match")
            or float(m.get("distance") or 1.0) < 0.88
        ]
        if current_problem_inventory or current_work_inventory:
            results = [m for m in results if not _has_current_inventory_closure_tag(m)]

        import datetime as _dt
        now_utc = _dt.datetime.now(_dt.timezone.utc)

        def _score(m: dict) -> float:
            dist = float(m.get("distance") or 1.0)
            imp  = float(m.get("importance") or 0.0)
            kw   = 0.20 if m.get("kw_match") else 0.0
            tag  = 0.15 if m.get("tag_match") else 0.0
            tok  = 0.10 if m.get("token_match") else 0.0
            proc = 0.05 if m.get("memory_type") == "procedural" else 0.0
            res  = 0.20 if m.get("status") == "resolved" else 0.0
            recency = 0.0
            created = m.get("created_at")
            if created:
                try:
                    if isinstance(created, str):
                        created = _dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_days = (now_utc - created).days
                    if age_days <= 7:
                        recency = 0.05
                    elif age_days <= 30:
                        recency = 0.02
                except Exception:
                    pass
            return dist - (imp * 0.25) - kw - tag - tok - proc - recency + res

        results.sort(key=_score)
        results = results[:limit]

        if results:
            matched_results = list(results)
            seen_ids = {m["memory_id"] for m in results}
            relation_scope = " AND scope = 'project'"
            if agent_id:
                relation_scope = " AND (scope = 'project' OR agent_id = $4)"

            parent_ids = [m["parent_id"] for m in matched_results if m.get("parent_id") and m["parent_id"] not in seen_ids]
            if parent_ids:
                parent_params: list[Any] = [vault_id, ["active", "resolved"], parent_ids]
                if agent_id:
                    parent_params.append(agent_id)
                parent_rows = await conn.fetch(
                    f'''SELECT memory_id, content, category, memory_type, importance,
                               status, slot, agent_id, scope, tags, created_at, parent_id, related_ids
                        FROM "LayerB"
                        WHERE vault_id = $1 AND status = ANY($2) AND memory_id = ANY($3::text[])
                          {relation_scope}''',
                    *parent_params,
                )
                for row in parent_rows:
                    m = _row_to_jsonable(row)
                    if m["memory_id"] not in seen_ids:
                        seen_ids.add(m["memory_id"])
                        results.append(m)

            if len(results) < limit:
                remaining = limit - len(results)
                related_ids = [
                    str(rid) for m in matched_results for rid in (m.get("related_ids") or [])
                    if str(rid) not in seen_ids
                ]
                if related_ids:
                    related_params: list[Any] = [vault_id, ["active", "resolved"], related_ids]
                    if agent_id:
                        related_params.append(agent_id)
                    related_rows = await conn.fetch(
                        f'''SELECT memory_id, content, category, memory_type, importance,
                                   status, slot, agent_id, scope, tags, created_at, parent_id, related_ids
                            FROM "LayerB"
                            WHERE vault_id = $1 AND status = ANY($2) AND memory_id = ANY($3::text[])
                              {relation_scope}
                            LIMIT {remaining}''',
                        *related_params,
                    )
                    for row in related_rows:
                        m = _row_to_jsonable(row)
                        if m["memory_id"] not in seen_ids:
                            seen_ids.add(m["memory_id"])
                            results.append(m)

        await conn.execute(
            '''INSERT INTO "AuditLog" (log_id, project_id, vault_id, agent_id, action, metadata)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb)''',
            str(uuid.uuid4()), project_id, vault_id, agent_id, "search",
            json.dumps({"query": query, "hits": len(results)}),
        )

    cleaned = []
    for m in results:
        m.pop("distance", None); m.pop("kw_match", None)
        m.pop("token_match", None); m.pop("tag_match", None)
        m.pop("parent_id", None); m.pop("related_ids", None)
        cleaned.append(m)
    return {"memories": cleaned}


@router.get("/get")
async def get_memories(
    end_user_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    limit: Optional[int] = Query(None, ge=1, le=100),
    category: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    auth: dict = Depends(verify_api_key),
):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="invalid category")
    if memory_type and memory_type not in VALID_MEMORY_TYPES:
        raise HTTPException(status_code=400, detail="invalid memory_type")

    project_id = auth["project_id"]
    pool = await get_pool()
    effective_page_size = _coerce_page_size(page_size, limit)

    async with pool.acquire() as conn:
        vault_id = await _get_vault_or_404(conn, project_id, end_user_id)
        if agent_id:
            await _validate_agent(conn, project_id, agent_id)

        where = ['vault_id = $1', 'status = $2']
        params: list[Any] = [vault_id, "active"]
        idx = 3
        if category:
            where.append(f"category = ${idx}"); params.append(category); idx += 1
        if memory_type:
            where.append(f"memory_type = ${idx}"); params.append(memory_type); idx += 1
        if agent_id:
            where.append(f"(scope = 'project' OR agent_id = ${idx})"); params.append(agent_id); idx += 1
        else:
            where.append("scope = 'project'")

        where_clause = " AND ".join(where)
        total = await conn.fetchval(f'SELECT COUNT(*) FROM "LayerB" WHERE {where_clause}', *params)
        offset = (page - 1) * effective_page_size
        rows = await conn.fetch(
            f'''SELECT memory_id, content, category, memory_type, importance,
                       slot, status, scope, agent_id, tags, created_at
                FROM "LayerB" WHERE {where_clause}
                ORDER BY created_at DESC LIMIT {effective_page_size} OFFSET {offset}''',
            *params,
        )

    pages = max(1, math.ceil((total or 0) / effective_page_size))
    return {"memories": [_row_to_jsonable(r) for r in rows], "total": total or 0, "page": page, "pages": pages}


@router.get("/timeline")
async def timeline(
    end_user_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    limit: Optional[int] = Query(None, ge=1, le=100),
    as_of: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    auth: dict = Depends(verify_api_key),
):
    project_id = auth["project_id"]
    pool = await get_pool()
    effective_page_size = _coerce_page_size(page_size, limit)
    offset = (page - 1) * effective_page_size

    async with pool.acquire() as conn:
        vault_id = await _get_vault_or_404(conn, project_id, end_user_id)
        if agent_id:
            await _validate_agent(conn, project_id, agent_id)

        scope_sql = "AND scope = 'project'"
        if agent_id:
            scope_sql = "AND (scope = 'project' OR agent_id = $2)"

        if as_of:
            try:
                as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="as_of must be ISO format")
            params: list[Any] = [vault_id, as_of_dt]
            if agent_id:
                scope_sql = "AND (scope = 'project' OR agent_id = $3)"
                params.append(agent_id)
            total = await conn.fetchval(
                f'''SELECT COUNT(*) FROM "LayerB"
                   WHERE vault_id = $1 AND valid_from <= $2 AND (valid_until IS NULL OR valid_until >= $2) {scope_sql}''',
                *params,
            )
            row_params = params + [effective_page_size, offset]
            lim_i = len(row_params) - 1
            off_i = len(row_params)
            rows = await conn.fetch(
                f'''SELECT memory_id, content, category, memory_type, importance,
                          slot, status, scope, agent_id, valid_from, valid_until, created_at, superseded_by
                   FROM "LayerB"
                   WHERE vault_id = $1 AND valid_from <= $2 AND (valid_until IS NULL OR valid_until >= $2) {scope_sql}
                   ORDER BY created_at DESC LIMIT ${lim_i} OFFSET ${off_i}''',
                *row_params,
            )
        else:
            params = [vault_id]
            if agent_id:
                scope_sql = "AND (scope = 'project' OR agent_id = $2)"
                params.append(agent_id)
            total = await conn.fetchval(f'SELECT COUNT(*) FROM "LayerB" WHERE vault_id = $1 {scope_sql}', *params)
            row_params = params + [effective_page_size, offset]
            lim_i = len(row_params) - 1
            off_i = len(row_params)
            rows = await conn.fetch(
                f'''SELECT memory_id, content, category, memory_type, importance,
                          slot, status, scope, agent_id, valid_from, valid_until, created_at, superseded_by
                   FROM "LayerB" WHERE vault_id = $1 {scope_sql}
                   ORDER BY created_at DESC LIMIT ${lim_i} OFFSET ${off_i}''',
                *row_params,
            )

    pages = max(1, math.ceil((total or 0) / effective_page_size))
    return {"memories": [_row_to_jsonable(r) for r in rows], "total": total or 0, "page": page, "pages": pages, "as_of": as_of}


@router.delete("/forget")
async def forget(body: ForgetBody, auth: dict = Depends(verify_api_key)):
    require_write(auth)
    project_id = auth["project_id"]
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            vault_id = await _get_vault_or_404(conn, project_id, body.end_user_id)
            await conn.execute('DELETE FROM "Conflict" WHERE vault_id = $1', vault_id)
            await conn.execute('DELETE FROM "AuditLog" WHERE vault_id = $1', vault_id)
            await conn.execute('DELETE FROM "LayerB" WHERE vault_id = $1', vault_id)
            await conn.execute('DELETE FROM "LayerA" WHERE vault_id = $1', vault_id)
            await conn.execute('DELETE FROM "Vault" WHERE vault_id = $1', vault_id)
    return {"deleted": True}


@router.get("/conflicts")
async def list_conflicts(
    end_user_id: str = Query(...),
    status: str = Query("pending"),
    agent_id: Optional[str] = Query(None),
    auth: dict = Depends(verify_api_key),
):
    if status not in ("pending", "resolved", "dismissed"):
        raise HTTPException(status_code=400, detail="invalid status")
    project_id = auth["project_id"]
    pool = await get_pool()
    async with pool.acquire() as conn:
        vault_id = await _get_vault_or_404(conn, project_id, end_user_id)
        visibility_sql = (
            "AND o.scope = 'project' AND n.scope = 'project'" if not agent_id
            else "AND (o.scope = 'project' OR o.agent_id = $3) AND (n.scope = 'project' OR n.agent_id = $3)"
        )
        params: list[Any] = [vault_id, status]
        if agent_id:
            params.append(agent_id)
        rows = await conn.fetch(
            f'''SELECT c.conflict_id, c.slot, c.detected_at, c.resolved_at, c.status,
                      c.clarifying_question, c.topic_tags,
                      o.memory_id AS old_memory_id, o.content AS old_content,
                      n.memory_id AS new_memory_id, n.content AS new_content
               FROM "Conflict" c
               JOIN "LayerB" o ON o.memory_id = c.old_memory_id
               JOIN "LayerB" n ON n.memory_id = c.new_memory_id
               WHERE c.vault_id = $1 AND c.status = $2 {visibility_sql}
               ORDER BY c.detected_at DESC''',
            *params,
        )
    conflicts = [{
        "conflict_id": str(r["conflict_id"]),
        "slot": r["slot"], "status": r["status"],
        "clarifying_question": r["clarifying_question"],
        "topic_tags": list(r["topic_tags"] or []),
        "detected_at": r["detected_at"].isoformat() if r["detected_at"] else None,
        "resolved_at": r["resolved_at"].isoformat() if r["resolved_at"] else None,
        "old_memory": {"memory_id": str(r["old_memory_id"]), "content": r["old_content"]},
        "new_memory": {"memory_id": str(r["new_memory_id"]), "content": r["new_content"]},
    } for r in rows]
    return {"conflicts": conflicts, "total": len(conflicts)}


@router.post("/resolve")
async def resolve_conflict(body: ResolveBody, auth: dict = Depends(verify_api_key)):
    require_write(auth)
    raw_resolution, decision = _normalize_resolution(body)
    project_id = auth["project_id"]
    pool = await get_pool()
    async with pool.acquire() as conn:
        conflict = await conn.fetchrow(
            '''SELECT c.conflict_id, c.vault_id, c.old_memory_id, c.new_memory_id, c.status,
                      old_mem.content AS old_content, new_mem.content AS new_content, v.project_id
               FROM "Conflict" c
               JOIN "Vault" v ON v.vault_id = c.vault_id
               JOIN "LayerB" old_mem ON old_mem.memory_id = c.old_memory_id
               JOIN "LayerB" new_mem ON new_mem.memory_id = c.new_memory_id
               WHERE c.conflict_id = $1''',
            body.conflict_id,
        )
        if not conflict:
            raise HTTPException(status_code=404, detail="Conflict not found")
        if str(conflict["project_id"]) != project_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if conflict["status"] != "pending":
            raise HTTPException(status_code=409, detail="Conflict already resolved")

        vault_id = str(conflict["vault_id"])
        old_id = str(conflict["old_memory_id"])
        new_id = str(conflict["new_memory_id"])
        winner = str(conflict["new_content"] if decision == "confirm" else conflict["old_content"])

        async with conn.transaction():
            if decision == "confirm":
                await conn.execute('UPDATE "LayerB" SET status = $1 WHERE memory_id = $2', "active", new_id)
                await conn.execute(
                    'UPDATE "LayerB" SET status = $1, superseded_by = $2, valid_until = now() WHERE memory_id = $3',
                    "superseded", new_id, old_id,
                )
                await conn.execute(
                    'UPDATE "Conflict" SET status = $1, resolved_at = now() WHERE conflict_id = $2',
                    "resolved", body.conflict_id,
                )
            else:
                await conn.execute(
                    'UPDATE "LayerB" SET status = $1, valid_until = now() WHERE memory_id = $2',
                    "superseded", new_id,
                )
                await conn.execute(
                    'UPDATE "Conflict" SET status = $1, resolved_at = now() WHERE conflict_id = $2',
                    "dismissed", body.conflict_id,
                )
            await conn.execute(
                '''INSERT INTO "AuditLog" (log_id, project_id, vault_id, action, metadata)
                   VALUES ($1, $2, $3, $4, $5::jsonb)''',
                str(uuid.uuid4()), project_id, vault_id, "resolve",
                json.dumps({"conflict_id": body.conflict_id, "decision": decision}),
            )
    return {"resolved": True, "winner": winner}


@router.post("/reprocess")
async def reprocess(body: ReprocessBody, auth: dict = Depends(verify_api_key)):
    require_write(auth)
    project_id = auth["project_id"]
    pool = await get_pool()
    async with pool.acquire() as conn:
        vault_id = await _get_vault_or_404(conn, project_id, body.end_user_id)
        count = await conn.fetchval(
            '''UPDATE "LayerA" SET processing_status = 'pending'
               WHERE vault_id = $1 AND processing_status IN ('done', 'failed')
               RETURNING count(*)''',
            vault_id,
        )
        await conn.execute(
            '''INSERT INTO "AuditLog" (log_id, project_id, vault_id, action, metadata)
               VALUES ($1, $2, $3, $4, $5::jsonb)''',
            str(uuid.uuid4()), project_id, vault_id, "reprocess",
            json.dumps({"reset_count": count or 0}),
        )
    _run_worker_bg(vault_id)
    return {"queued": count or 0}
