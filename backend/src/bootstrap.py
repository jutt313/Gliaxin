"""
Bootstrap: ensure the personal Project and default Vault exist on startup.
Reads OSS_PROJECT_ID from env — if the project doesn't exist, creates it.
Creates one Vault with end_user_id=NULL for personal (non-multi-tenant) use.
"""

import os
import uuid
from database import get_pool
from logger import get_logger

log = get_logger("gliaxin.bootstrap")


async def ensure_personal_project() -> None:
    project_id = os.getenv("OSS_PROJECT_ID", "").strip()
    if not project_id:
        raise RuntimeError("OSS_PROJECT_ID must be set in .env")

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            'SELECT project_id FROM "Project" WHERE project_id = $1',
            project_id,
        )
        if not existing:
            name = os.getenv("OSS_PROJECT_NAME", "Personal")
            await conn.execute(
                '''INSERT INTO "Project" (project_id, name, project_type)
                   VALUES ($1, $2, 'personal')
                   ON CONFLICT DO NOTHING''',
                project_id, name,
            )
            log.info("personal project created", project_id=project_id)
        else:
            log.info("personal project already exists", project_id=project_id)

        vault = await conn.fetchrow(
            'SELECT vault_id FROM "Vault" WHERE project_id = $1 AND end_user_id IS NULL',
            project_id,
        )
        if not vault:
            vault_id = str(uuid.uuid4())
            await conn.execute(
                '''INSERT INTO "Vault" (vault_id, project_id)
                   VALUES ($1, $2)
                   ON CONFLICT DO NOTHING''',
                vault_id, project_id,
            )
            log.info("default vault created", vault_id=vault_id)
        else:
            log.info("default vault already exists", vault_id=str(vault["vault_id"]))
