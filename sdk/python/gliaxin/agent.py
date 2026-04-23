"""
Agent namespace — all /v1/agent/* endpoints.
"""
from ._http import HttpClient
from .types import Agent, AgentList, RegisterResult, DeleteResult, Memory, MemoryList


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


class AgentNamespace:
    def __init__(self, http: HttpClient):
        self._http = http

    async def register(self, name: str) -> RegisterResult:
        """
        Create a named agent within your project.

        Idempotent — registering the same name returns the existing agent
        without creating a duplicate.

        Args:
            name: Unique agent name within your project.

        Returns:
            RegisterResult with agent_id, name, created_at, registered.
            registered=True if newly created, False if already existed.

        Example:
            agent = await g.agent.register("support-bot")
            print(agent.agent_id, agent.registered)
        """
        data = await self._http.post("/v1/agent/register", {"name": name})
        return RegisterResult(
            agent_id=data["agent_id"],
            name=data["name"],
            created_at=data["created_at"],
            registered=data["registered"],
        )

    async def list(self) -> AgentList:
        """
        List all active agents in your project.

        Returns:
            AgentList with agents and total.

        Example:
            result = await g.agent.list()
            for a in result.agents:
                print(a.name, a.agent_id)
        """
        data = await self._http.get("/v1/agent/list")
        return AgentList(
            agents=[
                Agent(
                    agent_id=a["agent_id"],
                    name=a["name"],
                    created_at=a["created_at"],
                )
                for a in data["agents"]
            ],
            total=data["total"],
        )

    async def delete(self, agent_id: str) -> DeleteResult:
        """
        Soft-delete an agent. The agent will no longer appear in list
        or register calls.

        Args:
            agent_id: UUID of the agent to delete.

        Returns:
            DeleteResult with deleted=True and agent_id.

        Example:
            result = await g.agent.delete("agent-uuid")
            print(result.deleted)  # True
        """
        data = await self._http.delete(f"/v1/agent/{agent_id}")
        return DeleteResult(deleted=data["deleted"], agent_id=data["agent_id"])

    async def shared(self, end_user_id: str, limit: int = 50) -> MemoryList:
        """
        Get all project-scoped active memories for a user, visible to
        every agent in the project. Sorted by importance — procedural first.

        Use this at the start of an agent turn to load user context.

        Args:
            end_user_id: The user to retrieve shared memories for.
            limit:       Max results (default 50, max 100).

        Returns:
            MemoryList with memories sorted by importance.

        Example:
            context = await g.agent.shared("user_123")
            memory_text = "\\n".join(
                f"[{m.category}] {m.content}"
                for m in context.memories
            )
            # Inject memory_text into your LLM system prompt
        """
        data = await self._http.get("/v1/agent/shared", {
            "end_user_id": end_user_id,
            "limit": limit,
        })
        return MemoryList(
            memories=[_parse_memory(m) for m in data["memories"]],
            total=data["total"],
            page=1,
            pages=1,
        )
