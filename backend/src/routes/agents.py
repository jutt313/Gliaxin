import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from database import get_pool
from api_key_auth import verify_api_key

public_router = APIRouter(prefix="/v1/agent", tags=["agent"])


@public_router.post("/register")
async def register_agent(body: dict, auth: dict = Depends(verify_api_key)):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    project_id = auth["project_id"]
    pool = await get_pool()

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            '''SELECT agent_id, name, created_at FROM "Agent"
               WHERE project_id = $1 AND name = $2 AND deleted_at IS NULL''',
            project_id, name,
        )
        if existing:
            return {
                "agent_id": str(existing["agent_id"]),
                "name": existing["name"],
                "created_at": existing["created_at"].isoformat(),
                "registered": False,
            }

        agent_id = str(uuid.uuid4())
        row = await conn.fetchrow(
            '''INSERT INTO "Agent" (agent_id, project_id, name)
               VALUES ($1, $2, $3)
               RETURNING agent_id, name, created_at''',
            agent_id, project_id, name,
        )

    return {
        "agent_id": str(row["agent_id"]),
        "name": row["name"],
        "created_at": row["created_at"].isoformat(),
        "registered": True,
    }


@public_router.get("/list")
async def list_agents(auth: dict = Depends(verify_api_key)):
    project_id = auth["project_id"]
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''SELECT agent_id, name, created_at FROM "Agent"
               WHERE project_id = $1 AND deleted_at IS NULL
               ORDER BY created_at DESC''',
            project_id,
        )
    agents = [{"agent_id": str(r["agent_id"]), "name": r["name"], "created_at": r["created_at"].isoformat()} for r in rows]
    return {"agents": agents, "total": len(agents)}


@public_router.delete("/{agent_id}")
async def delete_agent(agent_id: str, auth: dict = Depends(verify_api_key)):
    project_id = auth["project_id"]
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''SELECT agent_id FROM "Agent"
               WHERE agent_id = $1 AND project_id = $2 AND deleted_at IS NULL''',
            agent_id, project_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        await conn.execute(
            'UPDATE "Agent" SET deleted_at = now() WHERE agent_id = $1',
            agent_id,
        )
    return {"deleted": True, "agent_id": agent_id}


@public_router.get("/shared")
async def get_shared_memories(
    end_user_id: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    auth: dict = Depends(verify_api_key),
):
    project_id = auth["project_id"]
    pool = await get_pool()
    async with pool.acquire() as conn:
        vault = await conn.fetchrow(
            'SELECT vault_id FROM "Vault" WHERE project_id = $1 AND end_user_id = $2',
            project_id, end_user_id,
        )
        if not vault:
            vault = await conn.fetchrow(
                'SELECT vault_id FROM "Vault" WHERE project_id = $1 AND end_user_id IS NULL',
                project_id,
            )
        if not vault:
            return {"memories": [], "total": 0}

        rows = await conn.fetch(
            '''SELECT memory_id, content, category, memory_type, importance,
                      slot, agent_id, created_at
               FROM "LayerB"
               WHERE vault_id = $1 AND scope = 'project' AND status = 'active'
               ORDER BY memory_type = 'procedural' DESC, importance DESC, created_at DESC
               LIMIT $2''',
            str(vault["vault_id"]), limit,
        )

    memories = [{
        "memory_id":   str(r["memory_id"]),
        "content":     r["content"],
        "category":    r["category"],
        "memory_type": r["memory_type"],
        "importance":  r["importance"],
        "slot":        r["slot"],
        "agent_id":    str(r["agent_id"]) if r["agent_id"] else None,
        "created_at":  r["created_at"].isoformat(),
    } for r in rows]
    return {"memories": memories, "total": len(memories)}
