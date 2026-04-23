"""
Memory namespace — all /v1/memory/* endpoints.
"""
from typing import Optional
from ._http import HttpClient
from .types import (
    AddResult, AddTurnResult, Memory, MemoryList, ForgetResult,
    Conflict, ConflictList, ResolveResult, ReprocessResult,
    RawRecord, RawList, FixResult,
)


def _parse_memory(r: dict) -> Memory:
    return Memory(
        memory_id=r["memory_id"],
        content=r["content"],
        category=r["category"],
        memory_type=r["memory_type"],
        importance=r["importance"],
        slot=r.get("slot"),
        status=r.get("status", "active"),
        scope=r.get("scope", "project"),
        agent_id=r.get("agent_id"),
        created_at=r.get("created_at", ""),
    )


def _parse_conflict(r: dict) -> Conflict:
    return Conflict(
        conflict_id=r["conflict_id"],
        slot=r.get("slot"),
        old_memory=r.get("old_memory", {}),
        new_memory=r.get("new_memory", {}),
        status=r["status"],
        created_at=r["created_at"],
    )


class MemoryNamespace:
    def __init__(self, http: HttpClient):
        self._http = http

    async def add_turn(
        self,
        end_user_id: str,
        agent_id: str,
        messages: list[dict],
        scope: str = "agent",
        metadata: Optional[dict] = None,
    ) -> AddTurnResult:
        """
        Save a full conversation turn (user + assistant) attributed to an agent.

        This is the primary ingest method for wrapper-based memory.
        Both sides of the turn are stored as raw evidence; the worker
        extracts durable memories from the full context.

        Args:
            end_user_id: Your user's ID.
            agent_id:    Required. UUID of the registered agent writing this memory.
            messages:    Ordered list of {"role": "user"|"assistant", "content": "..."}.
                         Must contain at least one message.
            scope:       "agent" (private, default) or "project" (shared across agents).
            metadata:    Optional extra data attached to all raw rows.

        Returns:
            AddTurnResult with turn_id, raw_ids, and status="queued".

        Example:
            result = await g.memory.add_turn(
                "user_123", agent_id,
                messages=[
                    {"role": "user", "content": "I prefer dark mode"},
                    {"role": "assistant", "content": "Noted, I'll keep that in mind."},
                ],
            )
            print(result.turn_id)
        """
        body: dict = {
            "end_user_id": end_user_id,
            "agent_id": agent_id,
            "messages": messages,
            "scope": scope,
        }
        if metadata:
            body["metadata"] = metadata
        data = await self._http.post("/v1/memory/add", body)
        return AddTurnResult(
            turn_id=data["turn_id"],
            raw_ids=data["raw_ids"],
            status=data["status"],
        )

    async def add(
        self,
        end_user_id: str,
        content: str,
        agent_id: Optional[str] = None,
    ) -> AddResult:
        """
        [Deprecated] Store a single raw message.

        Prefer add_turn() which captures the full conversation turn and
        requires an agent_id for proper memory isolation.

        Args:
            end_user_id: Your user's ID.
            content:     The raw memory text.
            agent_id:    Optional agent UUID.

        Returns:
            AddResult with raw_id and status="queued".
        """
        body: dict = {"end_user_id": end_user_id, "content": content}
        if agent_id:
            body["agent_id"] = agent_id
        data = await self._http.post("/v1/memory/add", body)
        return AddResult(raw_id=data["raw_id"], status=data["status"])

    async def get(
        self,
        end_user_id: str,
        page: int = 1,
        page_size: int = 50,
        category: Optional[str] = None,
        memory_type: Optional[str] = None,
    ) -> MemoryList:
        """
        List all active memories for a user, ordered by importance descending.

        Args:
            end_user_id: The user whose memories to retrieve.
            page:        Page number (default 1).
            page_size:   Results per page (default 50, max 100).
            category:    Filter by: job, ideas, problems, personal, decisions, other.
            memory_type: Filter by: episodic, semantic, procedural.

        Returns:
            MemoryList with memories, total, page, pages.

        Example:
            result = await g.memory.get("user_123")
            for m in result.memories:
                print(m.category, m.content)
        """
        params: dict = {"end_user_id": end_user_id, "page": page, "page_size": page_size}
        if category:
            params["category"] = category
        if memory_type:
            params["memory_type"] = memory_type
        data = await self._http.get("/v1/memory/get", params)
        return MemoryList(
            memories=[_parse_memory(m) for m in data["memories"]],
            total=data["total"],
            page=data["page"],
            pages=data["pages"],
        )

    async def search(
        self,
        end_user_id: str,
        q: str,
        limit: int = 10,
        agent_id: Optional[str] = None,
        category: Optional[str] = None,
        min_importance: Optional[float] = None,
    ) -> list[Memory]:
        """
        Semantic search over a user's memories using vector similarity.

        When agent_id is provided, returns that agent's private memories
        plus all project-scoped shared memories.

        Args:
            end_user_id:    The user to search memories for.
            q:              Natural language query.
            limit:          Max results (default 10, max 50).
            agent_id:       Optional. Filter to this agent's memories + shared memories.
            category:       Filter results to a single category.
            min_importance: Only return memories above this importance threshold.

        Returns:
            List of Memory objects ranked by relevance.
        """
        params: dict = {"end_user_id": end_user_id, "query": q, "limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if category:
            params["category"] = category
        if min_importance is not None:
            params["min_importance"] = min_importance
        data = await self._http.get("/v1/memory/search", params)
        return [_parse_memory(m) for m in data["memories"]]

    async def timeline(
        self,
        end_user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> MemoryList:
        """
        Full memory history including disputed/superseded entries, ordered
        by creation time. Useful for auditing or building an as-of view.

        Args:
            end_user_id: The user whose timeline to retrieve.
            page:        Page number (default 1).
            page_size:   Results per page (default 50, max 100).

        Returns:
            MemoryList with all memories in chronological order.

        Example:
            history = await g.memory.timeline("user_123")
            for m in history.memories:
                print(m.created_at, m.status, m.content)
        """
        params = {"end_user_id": end_user_id, "page": page, "page_size": page_size}
        data = await self._http.get("/v1/memory/timeline", params)
        return MemoryList(
            memories=[_parse_memory(m) for m in data["memories"]],
            total=data["total"],
            page=data["page"],
            pages=data["pages"],
        )

    async def forget(self, end_user_id: str) -> ForgetResult:
        """
        Permanently delete all memories and the vault for a user.
        Irreversible. Use for GDPR right-to-erasure requests.

        Args:
            end_user_id: The user whose entire memory vault to delete.

        Returns:
            ForgetResult with deleted=True.

        Example:
            result = await g.memory.forget("user_123")
            print(result.deleted)  # True
        """
        data = await self._http.delete("/v1/memory/forget", {"end_user_id": end_user_id})
        return ForgetResult(deleted=data["deleted"])

    async def conflicts(
        self,
        end_user_id: str,
        status: str = "pending",
    ) -> ConflictList:
        """
        List memory conflicts for a user.

        A conflict is created when two memories share the same slot
        (e.g. preferred_language). The new memory waits as 'disputed'
        while the old one stays 'active'.

        Args:
            end_user_id: The user whose conflicts to list.
            status:      Filter by: pending, resolved, dismissed (default: pending).

        Returns:
            ConflictList with conflicts and total.

        Example:
            result = await g.memory.conflicts("user_123")
            for c in result.conflicts:
                print(c.slot, c.old_memory, c.new_memory)
        """
        params = {"end_user_id": end_user_id, "status": status}
        data = await self._http.get("/v1/memory/conflicts", params)
        return ConflictList(
            conflicts=[_parse_conflict(c) for c in data["conflicts"]],
            total=data["total"],
        )

    async def resolve(
        self,
        conflict_id: str,
        resolution: str,
    ) -> ResolveResult:
        """
        Resolve a memory conflict.

        Args:
            conflict_id: UUID of the conflict to resolve.
            resolution:  "keep_old" or "keep_new".

        Returns:
            ResolveResult with resolved=True and the winner's content.

        Example:
            result = await g.memory.resolve("conflict-uuid", "keep_new")
            print(result.winner)
        """
        data = await self._http.post("/v1/memory/resolve", {
            "conflict_id": conflict_id,
            "resolution": resolution,
        })
        return ResolveResult(resolved=data["resolved"], winner=data.get("winner", ""))

    async def raw(
        self,
        end_user_id: str,
        page: int = 1,
        page_size: int = 50,
        agent_id: Optional[str] = None,
    ) -> RawList:
        """
        Read Layer A verbatim records — the exact words the user said.

        No AI processing. Returns raw content + timestamps straight from
        the immutable store. Useful for debugging, auditing, or when the
        agent needs the literal transcript rather than extracted facts.

        Args:
            end_user_id: The user whose raw records to retrieve.
            page:        Page number (default 1).
            page_size:   Results per page (default 50, max 200).
            agent_id:    Optional filter — only records from this agent.

        Returns:
            RawList with records, total, page, pages.

        Example:
            result = await g.memory.raw("user_123")
            for r in result.records:
                print(r.created_at, r.content)
        """
        params: dict = {"end_user_id": end_user_id, "page": page, "page_size": page_size}
        if agent_id:
            params["agent_id"] = agent_id
        data = await self._http.get("/v1/memory/raw", params)
        records = [
            RawRecord(
                raw_id=r["raw_id"],
                content=r["content"],
                processing_status=r["processing_status"],
                agent_id=r.get("agent_id"),
                created_at=r.get("created_at", ""),
                metadata=r.get("metadata"),
            )
            for r in data["records"]
        ]
        return RawList(records=records, total=data["total"], page=data["page"], pages=data["pages"])

    async def fix(self, memory_id: str, reason: Optional[str] = None) -> FixResult:
        """
        Report a specific Layer B memory as wrong or inaccurate.

        Deletes the bad processed record and resets the linked raw
        Layer A entry to pending so the worker re-extracts it cleanly.
        Use this when the agent detects that an extracted memory is
        wrong and needs to be rebuilt from the original raw content.

        Args:
            memory_id: UUID of the Layer B memory to fix.
            reason:    Optional description of what is wrong (logged to audit).

        Returns:
            FixResult with queued=True, memory_id, raw_id.

        Example:
            result = await g.memory.fix("mem-uuid", reason="Wrong category assigned")
            print(result.queued)   # True
            print(result.raw_id)   # the raw record that will be re-extracted
        """
        body: dict = {"memory_id": memory_id}
        if reason:
            body["reason"] = reason
        data = await self._http.post("/v1/memory/fix", body)
        return FixResult(queued=data["queued"], memory_id=data["memory_id"], raw_id=data["raw_id"])

    async def reprocess(self, end_user_id: str) -> ReprocessResult:
        """
        Re-run Gemini extraction and embedding on all raw records for a user.
        Use when the model is upgraded or to rebuild LayerB from scratch.

        Args:
            end_user_id: The user whose vault to reprocess.

        Returns:
            ReprocessResult with the number of records queued.

        Example:
            result = await g.memory.reprocess("user_123")
            print(f"{result.queued} records queued")
        """
        data = await self._http.post("/v1/memory/reprocess", {"end_user_id": end_user_id})
        return ReprocessResult(queued=data["queued"])
