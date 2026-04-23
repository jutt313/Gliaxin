from typing import Callable, Awaitable, Optional
from ._http import HttpClient
from .memory import MemoryNamespace
from .agent import AgentNamespace

DEFAULT_BASE_URL = "https://api.gliaxin.com"


class Gliaxin:
    """
    Gliaxin API client.

    Args:
        api_key:  Your Gliaxin API key (starts with glx_).
        base_url: Override the API base URL (useful for self-hosting or testing).
        timeout:  Request timeout in seconds (default 30).

    Example:
        from gliaxin import Gliaxin

        g = Gliaxin("glx_YOUR_KEY")

        # Memory operations
        await g.memory.add("user_123", "User prefers dark mode")
        await g.memory.get("user_123")
        await g.memory.search("user_123", "UI preferences")
        await g.memory.forget("user_123")

        # Agent operations
        await g.agent.register("support-bot")
        await g.agent.list()
        await g.agent.shared("user_123")
        await g.agent.delete("agent-uuid")

        # One-line memory wrapper — works with any LLM
        async def my_llm(messages):
            ...  # OpenAI, Anthropic, Gemini, Ollama, anything

        client = g.wrap(my_llm)
        reply = await client.chat(user_id="user_123", message="What do I like?")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ):
        if not api_key or not api_key.startswith("glx_"):
            raise ValueError("api_key must start with 'glx_'")

        http = HttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self.memory = MemoryNamespace(http)
        self.agent  = AgentNamespace(http)

    def wrap(
        self,
        llm_fn: Callable[[list[dict]], Awaitable[str]],
        *,
        context_limit: int = 10,
        auto_save: bool = True,
        agent_id: Optional[str] = None,
        system_prefix: str = "You have access to the following memories about this user:",
    ) -> "GliaxinWrapper":
        """
        Wrap any async LLM callable with automatic memory search + save.

        Args:
            llm_fn:        Any async fn: (messages: list[dict]) -> str
                           Works with OpenAI, Anthropic, Gemini, Ollama, LiteLLM, etc.
            context_limit: Max memories injected per call (default 10).
            auto_save:     Auto-save user + assistant turn after each call (default True).
            agent_id:      Optional agent UUID to attribute saved memories to.
            system_prefix: Header line prepended before the memory block in the system prompt.

        Returns:
            GliaxinWrapper with a .chat(user_id, message) method.

        Example:
            async def my_llm(messages):
                resp = await openai.chat.completions.create(model="gpt-4o", messages=messages)
                return resp.choices[0].message.content

            client = g.wrap(my_llm)
            reply = await client.chat(user_id="user_123", message="hello")
        """
        from .wrap import GliaxinWrapper
        return GliaxinWrapper(
            self,
            llm_fn,
            context_limit=context_limit,
            auto_save=auto_save,
            agent_id=agent_id,
            system_prefix=system_prefix,
        )


# re-export so `from gliaxin import GliaxinWrapper` works
from .wrap import GliaxinWrapper  # noqa: E402
