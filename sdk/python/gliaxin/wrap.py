"""
GliaxinWrapper — one-line turn-aware memory for any LLM.

Usage:
    from gliaxin import Gliaxin

    g = Gliaxin("glx_YOUR_KEY")

    # Provide YOUR LLM as any async callable: (messages: list[dict]) -> str
    async def my_llm(messages):
        # OpenAI, Anthropic, Gemini, Ollama, LiteLLM — anything
        response = await openai_client.chat.completions.create(
            model="gpt-4o", messages=messages
        )
        return response.choices[0].message.content

    # agent_name is required — the wrapper auto-registers it on first use
    client = g.wrap(my_llm, agent_name="support-bot")

    # Memory is automatic. Both user and assistant turns are saved.
    reply = await client.chat(user_id="user_123", message="What's my favourite colour?")
    print(reply)

What happens under the hood on every chat() call:
    1. Auto-register the agent (idempotent — safe to call every time)
    2. Search user's memories using that agent's identity
    3. Inject relevant memories silently into the system prompt
    4. Call your LLM with the enriched messages
    5. Save the full turn (user + assistant) attributed to the agent
"""
from typing import Callable, Awaitable, Optional


class GliaxinWrapper:
    """
    Wraps any async LLM callable with automatic turn-based memory.

    The agent is registered automatically on the first chat() call.
    Both user message and assistant reply are saved as a turn.

    Args:
        gliaxin:        The Gliaxin client instance.
        llm_fn:         Any async callable: (messages: list[dict]) -> str.
        agent_name:     Required. Human-readable agent name used for registration.
        scope:          Memory scope for saved turns: "agent" (private, default)
                        or "project" (shared across all agents in the project).
        context_limit:  Max memories injected per call (default 10).
        auto_register:  Auto-register the agent on first call (default True).
        auto_save:      Save the full turn after each call (default True).
        system_prefix:  Text prepended before the injected memory block.
    """

    def __init__(
        self,
        gliaxin,
        llm_fn: Callable[[list[dict]], Awaitable[str]],
        *,
        agent_name: str,
        scope: str = "agent",
        context_limit: int = 10,
        auto_register: bool = True,
        auto_save: bool = True,
        system_prefix: str = "You have access to the following memories about this user:",
    ):
        self._g = gliaxin
        self._llm = llm_fn
        self._agent_name = agent_name
        self._scope = scope
        self._context_limit = context_limit
        self._auto_register = auto_register
        self._auto_save = auto_save
        self._system_prefix = system_prefix
        self._agent_id: Optional[str] = None

    async def _ensure_registered(self) -> str:
        if self._agent_id is None:
            result = await self._g.agent.register(self._agent_name)
            self._agent_id = result.agent_id
        return self._agent_id

    async def chat(
        self,
        user_id: str,
        message: str,
        *,
        history: Optional[list[dict]] = None,
        system: Optional[str] = None,
    ) -> str:
        """
        Send a message with automatic memory injection and full-turn auto-save.

        Args:
            user_id:  Your end-user's ID.
            message:  The user's message text.
            history:  Optional prior turns as [{"role": ..., "content": ...}].
            system:   Optional base system prompt. Memory context is appended.

        Returns:
            The assistant's reply as a plain string.
        """
        agent_id = await self._ensure_registered() if self._auto_register else self._agent_id

        memories = await self._g.memory.search(
            user_id, message, limit=self._context_limit, agent_id=agent_id,
        )

        messages = self._build_messages(message, memories, history, system)

        reply = await self._llm(messages)

        if self._auto_save and agent_id:
            await self._save_turn(user_id, agent_id, message, reply)

        return reply

    def _build_messages(
        self,
        message: str,
        memories: list,
        history: Optional[list[dict]],
        system: Optional[str],
    ) -> list[dict]:
        messages: list[dict] = []

        system_parts: list[str] = []
        if system:
            system_parts.append(system)

        if memories:
            lines = [self._system_prefix] if self._system_prefix else []
            for m in memories:
                lines.append(f"- [{m.category}] {m.content}")
            system_parts.append("\n".join(lines))

        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": message})
        return messages

    async def _save_turn(self, user_id: str, agent_id: str, user_msg: str, assistant_reply: str) -> None:
        try:
            await self._g.memory.add_turn(
                user_id,
                agent_id,
                messages=[
                    {"role": "user",      "content": user_msg},
                    {"role": "assistant", "content": assistant_reply},
                ],
                scope=self._scope,
            )
        except Exception:
            pass
