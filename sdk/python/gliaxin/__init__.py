"""
Gliaxin Python SDK
==================
Persistent, structured memory for AI agents.

    pip install gliaxin

Quick start:

    import asyncio
    from gliaxin import Gliaxin

    g = Gliaxin("glx_YOUR_KEY")

    async def main():
        # Add a memory
        result = await g.memory.add("user_123", "User prefers dark mode")
        print(result.raw_id)

        # Retrieve memories
        memories = await g.memory.get("user_123")
        for m in memories.memories:
            print(m.category, m.importance, m.content)

        # Semantic search
        results = await g.memory.search("user_123", "UI preferences")
        for m in results:
            print(m.content)

        # Load agent context
        context = await g.agent.shared("user_123")
        system_prompt = "\\n".join(
            f"[{m.category}] {m.content}" for m in context.memories
        )

    asyncio.run(main())
"""

from .client import Gliaxin, GliaxinWrapper
from .exceptions import (
    GliaxinError,
    AuthError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
)
from .types import (
    Memory,
    MemoryList,
    AddResult,
    AddTurnResult,
    ForgetResult,
    ReprocessResult,
    Conflict,
    ConflictList,
    ResolveResult,
    Agent,
    AgentList,
    RegisterResult,
    DeleteResult,
)

__version__ = "0.1.0"
__all__ = [
    "Gliaxin",
    "GliaxinWrapper",
    "GliaxinError",
    "AuthError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "Memory",
    "MemoryList",
    "AddResult",
    "AddTurnResult",
    "ForgetResult",
    "ReprocessResult",
    "Conflict",
    "ConflictList",
    "ResolveResult",
    "Agent",
    "AgentList",
    "RegisterResult",
    "DeleteResult",
]
