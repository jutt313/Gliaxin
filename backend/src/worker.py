import asyncio
import json
import re
import traceback
import uuid
from typing import Any, Callable, Optional

import asyncpg
from dotenv import load_dotenv

from database import get_pool
from logger import get_logger
from metrics import record_worker_outcome
from notify import push as notify, user_id_for_project
from providers import get_provider

load_dotenv()

log = get_logger("gliaxin.worker")

_process_lock: Optional[asyncio.Lock] = None
EXTRACTOR_VERSION = "v4"

CONTEXT_RECENT_LIMIT  = 30
CONTEXT_SIMILAR_LIMIT = 30
TAG_NORM_THRESHOLD    = 0.15

VALID_CATEGORIES = {"job", "ideas", "problems", "personal", "decisions", "other"}
VALID_MEMORY_TYPES = {"episodic", "semantic", "procedural"}

CONFLICT_DISTANCE_THRESHOLD  = 0.30
RELATION_PARENT_MAX_DISTANCE = 0.45
RELATION_NEARBY_MAX_DISTANCE = 0.65
MAX_RELATED_MEMORIES         = 5
CLUSTER_SUMMARY_THRESHOLD    = 5

_TRANSIENT_SIGNALS = ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "quota", "rate")


async def _with_retry(fn: Callable, *args, max_retries: int = 3, base_delay: float = 1.5, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            err = str(exc).lower()
            is_transient = any(s.lower() in err for s in _TRANSIENT_SIGNALS)
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                log.warning("transient error, retrying", attempt=attempt + 1, delay=delay, error=str(exc)[:120])
                await asyncio.sleep(delay)
                last_exc = exc
            else:
                raise
    raise last_exc  # type: ignore


# ── Prompts ──────────────────────────────────────────────────────────────────

_LEGACY_EXTRACT_PROMPT = """You are a memory extraction AI for Gliaxin, a developer productivity tool.
The user is typically a software developer building AI apps, APIs, or web applications.
Always interpret technical terms in that context.

Analyze this raw input and return JSON only — no markdown, no prose.

Input: "{content}"

Your job: extract one durable, self-contained fact worth remembering long-term about this user.

Rules:
- Ignore transient session actions: "user checked logs", "screenshot taken", single-word inputs, pure questions.
- If nothing durable can be extracted, return importance 0.0 and summary null.
- summary must be self-contained — a reader with no context must understand it fully.
- tags MUST use hierarchical format "main/subtag" (e.g. "ui/dark-mode", "backend/database", "personal/preference").
- 2–4 tags per memory.

Return exactly this schema:
{{
  "summary": "detailed self-contained fact, or null",
  "category": "job|ideas|problems|personal|decisions|other",
  "memory_type": "episodic|semantic|procedural",
  "importance": 0.0,
  "slot": "snake_case_slot or null",
  "tags": ["main/subtag1", "main2/subtag2"]
}}"""

_TURN_EXTRACT_PROMPT = """You are a memory extraction AI for Gliaxin, a developer productivity tool.
The user is typically a software developer building AI apps, APIs, or web applications.

═══ EXISTING MEMORIES ═══
{existing_memories_block}

═══ EXISTING TAG VOCABULARY ═══
{tag_vocab_block}

═══ CURRENT CONVERSATION TURN ═══
{turn_text}

═══ YOUR JOB ═══
Extract up to 3 durable memories from the CURRENT TURN.

Rules:
- Extract ONLY durable facts: preferences, decisions, instructions, project context, accepted outcomes.
- Do NOT store: generic world knowledge, math facts, filler ("ok", "thanks").
- summary must be SELF-CONTAINED and ENRICHED with relevant existing context.
- Tags MUST use hierarchical "main/subtag" format. 2–4 tags per memory.
- REUSE existing tags and slots wherever they apply.
- If a turn closes an earlier task/problem/plan, write the new current-state memory using the same slot framing.
- If this memory extends an existing memory, set parent_id to that memory's ID. Otherwise null.
- If the turn has nothing durable, return [].

Each memory object schema:
{{
  "summary": "detailed self-contained enriched fact about the user",
  "category": "job|ideas|problems|personal|decisions|other",
  "memory_type": "episodic|semantic|procedural",
  "importance": 0.0,
  "slot": "snake_case_slot or null",
  "tags": ["main/subtag", "main2/subtag2"],
  "parent_id": "existing memory ID if this memory extends another, or null"
}}

Return a JSON array of 0 to 3 objects. Return [] if nothing durable found."""

_CONTRADICTION_PROMPT = """You are checking whether two memory statements about the same person directly contradict each other.

Memory A: "{a}"
Memory B: "{b}"

Do these two statements directly contradict each other? Answer with JSON only:
{{
  "contradicts": true or false,
  "clarifying_question": "short question to resolve the contradiction, or null if no contradiction"
}}

A contradiction means one statement makes the other false (e.g. "likes purple" vs "dislikes purple").
Near-duplicates or statements on different topics do NOT contradict."""

_CLUSTER_SUMMARY_PROMPT = """You are summarising a cluster of related memories about one user.

Parent concept: {parent_content}

The cluster has {count} detail memories:
{detail_block}

Write one concise summary sentence that captures the key pattern or insight across all these details.
Return plain text only — no JSON, no markdown, no quotes."""

_LIFECYCLE_TRANSITION_PROMPT = """You are checking whether a new memory closes or replaces an older memory about the same project/user state.

Old memory:
- category: "{old_category}"
- tags: {old_tags}
- content: "{old_memory}"

New memory:
- category: "{new_category}"
- tags: {new_tags}
- content: "{new_memory}"

Return JSON only:
{{
  "transition": "none" | "resolved" | "superseded",
  "reason_tag": null | "lifecycle/problem-resolved" | "lifecycle/task-completed" | "lifecycle/plan-step-done" | "lifecycle/workaround-removed" | "lifecycle/incident-status-changed" | "lifecycle/feature-live" | "lifecycle/migration-deployed" | "lifecycle/access-rule-changed" | "lifecycle/ownership-changed" | "lifecycle/deadline-status-changed" | "lifecycle/decision-changed"
}}

Use "resolved" when the old memory described an open problem, pending task, planned step, workaround, or incident now closed/done.
Use "superseded" when the old memory was a prior decision, rule, owner, deadline, or status the new memory replaces.
Use "none" if the new memory is just related context, a detail, a duplicate, or not clearly closing/replacing the old memory."""

LIFECYCLE_REASON_TAGS = {
    "lifecycle/problem-resolved", "lifecycle/task-completed", "lifecycle/plan-step-done",
    "lifecycle/workaround-removed", "lifecycle/incident-status-changed", "lifecycle/feature-live",
    "lifecycle/migration-deployed", "lifecycle/access-rule-changed", "lifecycle/ownership-changed",
    "lifecycle/deadline-status-changed", "lifecycle/decision-changed",
}


def _strip_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _normalize_candidate(data: dict) -> Optional[dict]:
    category = data.get("category") if data.get("category") in VALID_CATEGORIES else "other"
    memory_type = data.get("memory_type") if data.get("memory_type") in VALID_MEMORY_TYPES else "semantic"
    try:
        importance = max(0.0, min(1.0, float(data.get("importance", 0.5))))
    except (TypeError, ValueError):
        importance = 0.5
    slot = data.get("slot")
    slot = slot.strip() if isinstance(slot, str) and slot.strip() else None
    summary = data.get("summary")
    if not summary or not str(summary).strip():
        return None
    raw_tags = data.get("tags") or []
    tags = [str(t).strip().lower() for t in raw_tags if t and str(t).strip()][:8]
    raw_parent = data.get("parent_id")
    parent_id = raw_parent.strip() if isinstance(raw_parent, str) and raw_parent.strip() else None
    return {
        "category": category, "memory_type": memory_type, "importance": importance,
        "slot": slot, "summary": str(summary).strip(), "tags": tags, "parent_id": parent_id,
    }


async def _embed(text: str) -> list[float]:
    provider = get_provider()

    async def _call():
        return await provider.embed(text, task_type="RETRIEVAL_DOCUMENT")

    vec = await _with_retry(_call)
    return vec


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


async def _tool_search_memories_fn(conn, vault_id: str):
    """Returns a search callable scoped to this vault for provider tool calling."""
    async def _search(query: str, tags: list[str]) -> str:
        embedding = await _embed(query)
        vec = _format_vector(embedding)
        if tags:
            rows = await conn.fetch(
                '''SELECT content, tags, slot, category,
                          (embedding <=> $2::vector) AS distance
                   FROM "LayerB"
                   WHERE vault_id = $1 AND status = 'active'
                     AND ((embedding <=> $2::vector) < 0.6 OR tags && $3::text[])
                   ORDER BY embedding <=> $2::vector LIMIT 15''',
                vault_id, vec, tags,
            )
        else:
            rows = await conn.fetch(
                '''SELECT content, tags, slot, category,
                          (embedding <=> $2::vector) AS distance
                   FROM "LayerB"
                   WHERE vault_id = $1 AND status = 'active'
                   ORDER BY embedding <=> $2::vector LIMIT 15''',
                vault_id, vec,
            )
        if not rows:
            return "No memories found for this query."
        lines = [f"{i}. [{r['category']}] {r['content']} (tags: {', '.join(r['tags'] or [])})"
                 for i, r in enumerate(rows, 1)]
        return "\n".join(lines)
    return _search


async def _extract_metadata(content: str) -> Optional[dict]:
    provider = get_provider()
    prompt = _LEGACY_EXTRACT_PROMPT.format(content=content.replace('"', '\\"'))

    async def _call():
        return await provider.generate_json(prompt, temperature=0.2)

    raw = _strip_json(await _with_retry(_call))
    data = json.loads(raw)
    candidate = _normalize_candidate(data)
    if candidate is None:
        return None
    raw_summary = data.get("summary")
    try:
        raw_imp = float(data.get("importance", 0.5))
    except (TypeError, ValueError):
        raw_imp = 0.5
    candidate["skip"] = not raw_summary or not str(raw_summary).strip() or (raw_imp == 0.0 and not raw_summary)
    return candidate


async def _normalize_tags_to_vocab(new_tags: list[str], vocab: list[str]) -> list[str]:
    if not vocab or not new_tags:
        return new_tags
    normalized = []
    try:
        new_embeddings = await asyncio.gather(*[_embed(t) for t in new_tags])
        vocab_embeddings = await asyncio.gather(*[_embed(t) for t in vocab])
        for tag, new_emb in zip(new_tags, new_embeddings):
            best_match = tag
            best_dist = TAG_NORM_THRESHOLD
            for vtag, v_emb in zip(vocab, vocab_embeddings):
                dot = sum(a * b for a, b in zip(new_emb, v_emb))
                dist = 1.0 - dot
                if dist < best_dist:
                    best_dist = dist
                    best_match = vtag
            normalized.append(best_match)
    except Exception as exc:
        log.warning("tag normalization failed, using original tags", error=str(exc))
        return new_tags
    return normalized


async def _fetch_vault_context(conn, vault_id: str, turn_text: str) -> dict:
    turn_embedding = await _embed(turn_text)
    vec = _format_vector(turn_embedding)
    recent_rows = await conn.fetch(
        '''SELECT memory_id, content, tags, slot, category FROM "LayerB"
           WHERE vault_id = $1 AND status = 'active'
           ORDER BY created_at DESC LIMIT $2''',
        vault_id, CONTEXT_RECENT_LIMIT,
    )
    similar_rows = await conn.fetch(
        '''SELECT memory_id, content, tags, slot, category,
                  (embedding <=> $2::vector) AS distance
           FROM "LayerB"
           WHERE vault_id = $1 AND status = 'active'
           ORDER BY embedding <=> $2::vector LIMIT $3''',
        vault_id, vec, CONTEXT_SIMILAR_LIMIT,
    )
    tag_rows = await conn.fetch(
        '''SELECT DISTINCT unnest(tags) AS tag FROM "LayerB"
           WHERE vault_id = $1 AND status = 'active' ORDER BY tag''',
        vault_id,
    )
    seen: set[str] = set()
    memories: list[dict] = []
    for row in list(similar_rows) + list(recent_rows):
        mid = str(row["memory_id"])
        if mid not in seen:
            seen.add(mid)
            memories.append({
                "memory_id": mid, "content": row["content"],
                "tags": list(row["tags"] or []), "slot": row["slot"], "category": row["category"],
            })
    tag_vocab = [r["tag"] for r in tag_rows]
    log.info("vault context fetched", vault_id=vault_id, context_memories=len(memories), tag_vocab_size=len(tag_vocab))
    return {"memories": memories, "tag_vocab": tag_vocab, "turn_embedding": turn_embedding}


async def _extract_turn(conn, vault_id: str, turn_rows: list[dict], scope_hint: str) -> list[dict]:
    turn_lines = []
    for row in sorted(turn_rows, key=lambda r: (r.get("message_index") or 0)):
        role = row.get("role") or "user"
        turn_lines.append(f"{role.upper()}: {row['content']}")
    turn_text = "\n".join(turn_lines)

    log.info("extracting metadata (turn)", messages=len(turn_rows), turn_length=len(turn_text))

    ctx = await _fetch_vault_context(conn, vault_id, turn_text)
    existing_memories = ctx["memories"]
    tag_vocab = ctx["tag_vocab"]

    if existing_memories:
        mem_lines = []
        for m in existing_memories:
            tag_str = ", ".join(m["tags"]) if m["tags"] else "—"
            slot_str = f" [slot: {m['slot']}]" if m["slot"] else ""
            mem_lines.append(f"• [id:{m['memory_id']}][{m['category']}]{slot_str} {m['content']} (tags: {tag_str})")
        existing_memories_block = "\n".join(mem_lines)
    else:
        existing_memories_block = "(no existing memories yet — this is the first turn)"

    tag_vocab_block = ", ".join(tag_vocab) if tag_vocab else "(no tags yet)"
    prompt = _TURN_EXTRACT_PROMPT.format(
        existing_memories_block=existing_memories_block,
        tag_vocab_block=tag_vocab_block,
        turn_text=turn_text,
    )

    provider = get_provider()
    search_fn = await _tool_search_memories_fn(conn, vault_id)

    async def _call():
        return await provider.generate_turn_json(prompt, search_fn=search_fn, max_tool_calls=3)

    raw_text = await _with_retry(_call)
    raw = _strip_json(raw_text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("turn extraction JSON parse failed", raw_preview=raw[:200])
        return []

    if not isinstance(data, list):
        data = [data] if isinstance(data, dict) else []

    raw_candidates = [c for item in data[:3] if (c := _normalize_candidate(item))]
    candidates = []
    for candidate in raw_candidates:
        if candidate.get("tags") and tag_vocab:
            candidate["tags"] = await _normalize_tags_to_vocab(candidate["tags"], tag_vocab)
        candidates.append(candidate)

    log.info("candidates finalized", count=len(candidates))
    return candidates


async def _check_contradiction(content_a: str, content_b: str) -> tuple[bool, Optional[str]]:
    provider = get_provider()
    prompt = _CONTRADICTION_PROMPT.format(
        a=content_a.replace('"', '\\"'),
        b=content_b.replace('"', '\\"'),
    )
    try:
        raw = _strip_json(await provider.generate_json(prompt, temperature=0.1))
        data = json.loads(raw)
        contradicts = bool(data.get("contradicts", False))
        question = data.get("clarifying_question") or None
        if question and not str(question).strip():
            question = None
        return contradicts, question
    except Exception as exc:
        log.warning("contradiction check failed", error=str(exc))
        return False, None


async def _check_lifecycle_transition(
    old_memory: str, old_category: str, old_tags: list[str],
    new_memory: str, new_category: str, new_tags: list[str],
) -> tuple[str, Optional[str]]:
    provider = get_provider()
    prompt = _LIFECYCLE_TRANSITION_PROMPT.format(
        old_memory=old_memory.replace('"', '\\"'), old_category=old_category,
        old_tags=json.dumps(old_tags or []),
        new_memory=new_memory.replace('"', '\\"'), new_category=new_category,
        new_tags=json.dumps(new_tags or []),
    )
    try:
        raw = _strip_json(await provider.generate_json(prompt, temperature=0.1))
        data = json.loads(raw)
        transition = str(data.get("transition") or "none").strip().lower()
        if transition not in {"none", "resolved", "superseded"}:
            transition = "none"
        reason_tag = data.get("reason_tag")
        if reason_tag not in LIFECYCLE_REASON_TAGS:
            reason_tag = None
        return transition, reason_tag
    except Exception as exc:
        log.warning("lifecycle transition check failed", error=str(exc))
        return "none", None


async def _maybe_summarize_cluster(
    conn, parent_id: str, raw_id: str, vault_id: str,
    project_id: str, agent_id: Optional[str], scope: str,
) -> None:
    sibling_count = await conn.fetchval(
        '''SELECT COUNT(*) FROM "LayerB"
           WHERE parent_id = $1 AND status = 'active' AND is_cluster_summary = false''',
        parent_id,
    )
    if (sibling_count or 0) <= CLUSTER_SUMMARY_THRESHOLD:
        return

    parent_row = await conn.fetchrow('SELECT content FROM "LayerB" WHERE memory_id = $1', parent_id)
    if not parent_row:
        return

    sibling_rows = await conn.fetch(
        '''SELECT content FROM "LayerB"
           WHERE parent_id = $1 AND status = 'active' AND is_cluster_summary = false
           ORDER BY created_at ASC''',
        parent_id,
    )
    detail_contents = [r["content"] for r in sibling_rows]
    detail_block = "\n".join(f"- {c}" for c in detail_contents)

    provider = get_provider()
    prompt = _CLUSTER_SUMMARY_PROMPT.format(
        parent_content=parent_row["content"],
        count=len(detail_contents),
        detail_block=detail_block,
    )

    async def _call():
        return await provider.generate_text(prompt, temperature=0.2)

    summary_text = await _with_retry(_call)
    if not summary_text:
        return

    existing = await conn.fetchrow(
        '''SELECT memory_id FROM "LayerB"
           WHERE parent_id = $1 AND is_cluster_summary = true AND status = 'active' ''',
        parent_id,
    )
    new_emb = await _embed(summary_text)
    new_vec = _format_vector(new_emb)

    if existing:
        await conn.execute(
            'UPDATE "LayerB" SET content = $1, embedding = $2::vector WHERE memory_id = $3',
            summary_text, new_vec, str(existing["memory_id"]),
        )
        log.info("cluster summary updated", parent_id=parent_id, siblings=len(detail_contents))
    else:
        summary_id = str(uuid.uuid4())
        await conn.execute(
            '''INSERT INTO "LayerB" (
                memory_id, raw_id, vault_id, project_id, agent_id,
                content, embedding, category, memory_type, scope,
                slot, importance, status, extractor_version, tags,
                parent_id, related_ids, is_cluster_summary
            ) VALUES ($1,$2,$3,$4,$5,$6,$7::vector,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17::text[],$18)''',
            summary_id, raw_id, vault_id, project_id, agent_id,
            summary_text, new_vec, "other", "semantic", scope,
            None, 0.9, "active", EXTRACTOR_VERSION, [], parent_id, [], True,
        )
        log.info("cluster summary created", parent_id=parent_id, summary_id=summary_id)


async def _insert_layer_b_candidate(
    conn, candidate: dict, raw_id: str, vault_id: str,
    project_id: str, agent_id: Optional[str], scope: str,
) -> tuple[str, int]:
    embedding = await _embed(candidate["summary"])
    vec = _format_vector(embedding)
    memory_id = str(uuid.uuid4())
    slot = candidate.get("slot")
    tags = list(candidate.get("tags") or [])
    importance = float(candidate.get("importance", 0.5))

    conflict_rows: list[tuple[str, str, Optional[str], list[str]]] = []

    if slot:
        slot_active = await conn.fetch(
            '''SELECT memory_id, content FROM "LayerB"
               WHERE vault_id = $1 AND slot = $2 AND status = 'active' ''',
            vault_id, slot,
        )
        for row in slot_active:
            if row["content"].strip() == candidate["summary"].strip():
                continue
            contradicts, question = await _check_contradiction(row["content"], candidate["summary"])
            if contradicts:
                conflict_rows.append((str(row["memory_id"]), slot, question, tags))

    checked_ids = {r[0] for r in conflict_rows}
    semantic_candidates = await conn.fetch(
        '''SELECT memory_id, content, slot FROM "LayerB"
           WHERE vault_id = $1 AND status = 'active'
             AND (embedding <=> $2::vector) < $3
           ORDER BY embedding <=> $2::vector LIMIT 5''',
        vault_id, vec, CONFLICT_DISTANCE_THRESHOLD,
    )
    for row in semantic_candidates:
        mid = str(row["memory_id"])
        if mid in checked_ids or row["content"].strip() == candidate["summary"].strip():
            continue
        contradicts, question = await _check_contradiction(row["content"], candidate["summary"])
        if contradicts:
            conflict_rows.append((mid, row["slot"] or None, question, tags))
            checked_ids.add(mid)

    relation_rows = await conn.fetch(
        '''SELECT memory_id, (embedding <=> $2::vector) AS distance FROM "LayerB"
           WHERE vault_id = $1 AND status = 'active' AND is_cluster_summary = false
             AND (embedding <=> $2::vector) < $3
           ORDER BY embedding <=> $2::vector LIMIT 25''',
        vault_id, vec, RELATION_NEARBY_MAX_DISTANCE,
    )
    nearby_rows = [
        {"memory_id": str(r["memory_id"]), "distance": float(r["distance"])}
        for r in relation_rows if str(r["memory_id"]) not in checked_ids
    ]

    parent_id = None
    for row in nearby_rows:
        if row["distance"] < RELATION_PARENT_MAX_DISTANCE:
            parent_id = row["memory_id"]
            break

    gemini_parent_id = candidate.get("parent_id")
    if gemini_parent_id and not parent_id:
        parent_exists = await conn.fetchval(
            '''SELECT 1 FROM "LayerB"
               WHERE memory_id = $1 AND vault_id = $2 AND status = 'active' ''',
            gemini_parent_id, vault_id,
        )
        if parent_exists:
            parent_id = gemini_parent_id

    related_ids: list[str] = []
    for row in nearby_rows:
        mid = row["memory_id"]
        dist = row["distance"]
        if mid == parent_id:
            continue
        if RELATION_PARENT_MAX_DISTANCE <= dist < RELATION_NEARBY_MAX_DISTANCE:
            related_ids.append(mid)
        if len(related_ids) >= MAX_RELATED_MEMORIES:
            break

    await conn.execute(
        '''INSERT INTO "LayerB" (
            memory_id, raw_id, vault_id, project_id, agent_id,
            content, embedding, category, memory_type, scope,
            slot, importance, status, extractor_version, tags,
            parent_id, related_ids, is_cluster_summary
        ) VALUES ($1,$2,$3,$4,$5,$6,$7::vector,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17::text[],$18)''',
        memory_id, raw_id, vault_id, project_id, agent_id,
        candidate["summary"], vec,
        candidate["category"], candidate["memory_type"], scope,
        slot, importance, "active", EXTRACTOR_VERSION,
        tags, parent_id, related_ids, False,
    )

    if related_ids:
        await conn.execute(
            '''UPDATE "LayerB"
               SET related_ids = array_append(related_ids, $1::text)
               WHERE memory_id = ANY($2::text[])
                 AND NOT ($1::text = ANY(related_ids))''',
            memory_id, related_ids,
        )

    for old_memory_id, slot_label, clarifying_question, topic_tags in conflict_rows:
        await conn.execute(
            'UPDATE "LayerB" SET status = $1, valid_until = now() WHERE memory_id = $2',
            "superseded", old_memory_id,
        )
        await conn.execute(
            '''INSERT INTO "Conflict" (
                conflict_id, vault_id, old_memory_id, new_memory_id,
                slot, clarifying_question, topic_tags, status, resolved_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,'resolved', now())''',
            str(uuid.uuid4()), vault_id, old_memory_id, memory_id,
            slot_label, clarifying_question, topic_tags,
        )
        log.info("conflict auto-resolved: new wins", old_id=old_memory_id, new_id=memory_id)

    nearby_active = await conn.fetch(
        '''SELECT memory_id, content, category, tags FROM "LayerB"
           WHERE vault_id = $1 AND status = 'active' AND memory_id <> $3
             AND is_cluster_summary = false AND (embedding <=> $2::vector) < 0.55
           ORDER BY embedding <=> $2::vector LIMIT 5''',
        vault_id, vec, memory_id,
    )
    for old_row in nearby_active:
        old_memory_id = str(old_row["memory_id"])
        transition, reason_tag = await _check_lifecycle_transition(
            str(old_row["content"]), str(old_row["category"]), list(old_row["tags"] or []),
            candidate["summary"], candidate["category"], tags,
        )
        if transition == "resolved":
            await conn.execute(
                '''UPDATE "LayerB"
                   SET status = 'resolved',
                       resolved_at = COALESCE(resolved_at, now()),
                       tags = CASE
                           WHEN $3::text IS NULL OR $3::text = ANY(tags) THEN tags
                           ELSE array_append(tags, $3::text)
                       END,
                       related_ids = CASE
                           WHEN $2::text = ANY(related_ids) THEN related_ids
                           ELSE array_append(related_ids, $2::text)
                       END
                   WHERE memory_id = $1 AND status = 'active' ''',
                old_memory_id, memory_id, reason_tag,
            )
            log.info("memory resolved by newer state", old_id=old_memory_id, new_id=memory_id, reason_tag=reason_tag)
        elif transition == "superseded":
            await conn.execute(
                '''UPDATE "LayerB"
                   SET status = 'superseded', superseded_by = $2,
                       valid_until = COALESCE(valid_until, now()),
                       tags = CASE
                           WHEN $3::text IS NULL OR $3::text = ANY(tags) THEN tags
                           ELSE array_append(tags, $3::text)
                       END,
                       related_ids = CASE
                           WHEN $2::text = ANY(related_ids) THEN related_ids
                           ELSE array_append(related_ids, $2::text)
                       END
                   WHERE memory_id = $1 AND status = 'active' ''',
                old_memory_id, memory_id, reason_tag,
            )
            log.info("memory superseded by newer state", old_id=old_memory_id, new_id=memory_id, reason_tag=reason_tag)

    if parent_id:
        await _maybe_summarize_cluster(conn, parent_id, raw_id, vault_id, project_id, agent_id, scope)

    return memory_id, len(conflict_rows)


async def _process_turn(conn, turn_rows: list[dict]) -> None:
    ordered_rows = sorted(turn_rows, key=lambda r: (r.get("message_index") or 0, str(r["raw_id"])))
    representative = ordered_rows[0]
    vault_id   = str(representative["vault_id"])
    project_id = str(representative["project_id"])
    agent_id   = str(representative["agent_id"]) if representative["agent_id"] else None
    scope_hint = representative.get("scope_hint") or "agent"
    scope      = scope_hint if scope_hint in ("agent", "project") else "agent"
    turn_id    = representative.get("turn_id")
    raw_ids    = [str(r["raw_id"]) for r in ordered_rows]

    log.info("processing turn", turn_id=turn_id, messages=len(turn_rows), scope=scope)

    try:
        candidates = await _extract_turn(conn, vault_id, ordered_rows, scope_hint)

        if not candidates:
            log.info("turn produced no memories", turn_id=turn_id)
            await conn.execute(
                'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = ANY($2)',
                "done", raw_ids,
            )
            record_worker_outcome("skipped_low_value")
            return

        anchor_raw_id = raw_ids[0]
        total_conflicts = 0

        async with conn.transaction():
            for candidate in candidates:
                memory_id, n_conflicts = await _insert_layer_b_candidate(
                    conn, candidate, anchor_raw_id, vault_id, project_id, agent_id, scope,
                )
                total_conflicts += n_conflicts
                log.info("candidate inserted", memory_id=memory_id, conflicts=n_conflicts)

            await conn.execute(
                'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = ANY($2)',
                "done", raw_ids,
            )

        log.info("turn processed", turn_id=turn_id, memories=len(candidates), conflicts=total_conflicts)
        record_worker_outcome("processed", len(candidates))
        if total_conflicts:
            record_worker_outcome("conflicts_created", total_conflicts)

    except asyncpg.ForeignKeyViolationError:
        log.info("turn skipped — row deleted before LayerB insert", turn_id=turn_id)
        record_worker_outcome("skipped")
    except Exception as exc:
        err_str = str(exc)
        is_transient = any(x in err_str for x in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))
        if is_transient:
            log.warning("transient error — will retry", turn_id=turn_id, error=str(exc))
            record_worker_outcome("retry")
            try:
                await conn.execute(
                    'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = ANY($2)',
                    "pending", raw_ids,
                )
            except Exception:
                pass
        else:
            log.error("fatal turn processing error", turn_id=turn_id, error=str(exc), exc_info=True)
            record_worker_outcome("failed")
            try:
                await conn.execute(
                    'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = ANY($2)',
                    "failed", raw_ids,
                )
            except Exception:
                pass


async def _process_one(conn, raw_row: dict) -> None:
    raw_id     = str(raw_row["raw_id"])
    vault_id   = str(raw_row["vault_id"])
    project_id = str(raw_row["project_id"])
    agent_id   = str(raw_row["agent_id"]) if raw_row["agent_id"] else None
    content    = raw_row["content"]
    scope      = "project"

    log.info("processing memory (legacy)", raw_id=raw_id, content_preview=content[:60])

    try:
        meta = await _extract_metadata(content)

        if meta is None or meta.get("skip"):
            log.info("skipping low-value memory", raw_id=raw_id)
            await conn.execute(
                'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = $2',
                "done", raw_id,
            )
            record_worker_outcome("skipped_low_value")
            return

        async with conn.transaction():
            memory_id, n_conflicts = await _insert_layer_b_candidate(
                conn, meta, raw_id, vault_id, project_id, agent_id, scope,
            )
            await conn.execute(
                'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = $2',
                "done", raw_id,
            )

        log.info("memory processed (legacy)", raw_id=raw_id, memory_id=memory_id, conflicts=n_conflicts)
        record_worker_outcome("processed")
        if n_conflicts:
            record_worker_outcome("conflicts_created", n_conflicts)

    except asyncpg.ForeignKeyViolationError:
        log.info("skipped — raw row deleted before LayerB insert", raw_id=raw_id)
        record_worker_outcome("skipped")
    except Exception as exc:
        err_str = str(exc)
        is_transient = any(x in err_str for x in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))
        if is_transient:
            log.warning("transient error — will retry", raw_id=raw_id, error=str(exc))
            record_worker_outcome("retry")
            try:
                await conn.execute(
                    'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = $2',
                    "pending", raw_id,
                )
            except Exception:
                pass
        else:
            log.error("fatal processing error", raw_id=raw_id, error=str(exc), exc_info=True)
            record_worker_outcome("failed")
            try:
                await conn.execute(
                    'UPDATE "LayerA" SET processing_status = $1 WHERE raw_id = $2',
                    "failed", raw_id,
                )
            except Exception:
                pass


def _get_process_lock() -> asyncio.Lock:
    global _process_lock
    if _process_lock is None:
        _process_lock = asyncio.Lock()
    return _process_lock


async def process_pending(vault_id: Optional[str] = None) -> None:
    lock = _get_process_lock()
    if lock.locked():
        log.debug("process_pending already running, skipping")
        return
    async with lock:
        await _run_pending(vault_id)


async def _run_pending(vault_id: Optional[str] = None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            if vault_id:
                turn_rows = await conn.fetch(
                    '''WITH complete_turns AS (
                           SELECT turn_id FROM "LayerA"
                           WHERE turn_id IS NOT NULL AND vault_id = $1
                           GROUP BY turn_id
                           HAVING bool_and(processing_status = 'pending')
                           LIMIT 20
                       )
                       UPDATE "LayerA" la SET processing_status = 'processing'
                       FROM complete_turns ct WHERE la.turn_id = ct.turn_id
                         AND la.processing_status = 'pending'
                       RETURNING la.raw_id, la.vault_id, la.project_id, la.agent_id,
                                 la.content, la.turn_id, la.role, la.message_index, la.scope_hint''',
                    vault_id,
                )
            else:
                turn_rows = await conn.fetch(
                    '''WITH complete_turns AS (
                           SELECT turn_id FROM "LayerA"
                           WHERE turn_id IS NOT NULL
                           GROUP BY turn_id
                           HAVING bool_and(processing_status = 'pending')
                           LIMIT 20
                       )
                       UPDATE "LayerA" la SET processing_status = 'processing'
                       FROM complete_turns ct WHERE la.turn_id = ct.turn_id
                         AND la.processing_status = 'pending'
                       RETURNING la.raw_id, la.vault_id, la.project_id, la.agent_id,
                                 la.content, la.turn_id, la.role, la.message_index, la.scope_hint'''
                )

        async with conn.transaction():
            if vault_id:
                legacy_rows = await conn.fetch(
                    '''WITH claimed AS (
                           SELECT raw_id FROM "LayerA"
                           WHERE processing_status = 'pending' AND turn_id IS NULL AND vault_id = $1
                           ORDER BY created_at ASC LIMIT 100 FOR UPDATE SKIP LOCKED
                       )
                       UPDATE "LayerA" la SET processing_status = 'processing'
                       FROM claimed WHERE la.raw_id = claimed.raw_id
                       RETURNING la.raw_id, la.vault_id, la.project_id, la.agent_id, la.content''',
                    vault_id,
                )
            else:
                legacy_rows = await conn.fetch(
                    '''WITH claimed AS (
                           SELECT raw_id FROM "LayerA"
                           WHERE processing_status = 'pending' AND turn_id IS NULL
                           ORDER BY created_at ASC LIMIT 100 FOR UPDATE SKIP LOCKED
                       )
                       UPDATE "LayerA" la SET processing_status = 'processing'
                       FROM claimed WHERE la.raw_id = claimed.raw_id
                       RETURNING la.raw_id, la.vault_id, la.project_id, la.agent_id, la.content'''
                )

    turns_by_id: dict[str, list[dict]] = {}
    for r in turn_rows:
        tid = r["turn_id"]
        turns_by_id.setdefault(tid, []).append(dict(r))

    total_claimed = len(turns_by_id) + len(legacy_rows)
    if total_claimed:
        log.info("processing pending work", turns=len(turns_by_id), legacy=len(legacy_rows))
        record_worker_outcome("claimed", total_claimed)
    else:
        log.debug("no pending memories")

    sem = asyncio.Semaphore(5)

    async def _do_turn(rows: list[dict]) -> None:
        async with sem:
            async with pool.acquire() as c:
                await _process_turn(c, rows)

    async def _do_legacy(row: dict) -> None:
        async with sem:
            async with pool.acquire() as c:
                await _process_one(c, row)

    tasks = [_do_turn(g) for g in turns_by_id.values()] + [_do_legacy(dict(r)) for r in legacy_rows]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            log.error("unexpected task error", task_index=i, error=str(r))


async def embed_query(text: str) -> list[float]:
    provider = get_provider()
    return await provider.embed(text, task_type="RETRIEVAL_QUERY")
