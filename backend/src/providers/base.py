from abc import ABC, abstractmethod
from typing import Callable, Optional


class LLMProvider(ABC):
    """Abstract interface every provider must implement."""

    @abstractmethod
    async def generate_json(self, prompt: str, temperature: float = 0.2) -> str:
        """Return a JSON string."""

    @abstractmethod
    async def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        """Return plain text."""

    @abstractmethod
    async def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """Return a 768-dimensional embedding vector."""

    async def generate_turn_json(
        self,
        prompt: str,
        search_fn: Optional[Callable] = None,
        max_tool_calls: int = 3,
    ) -> str:
        """
        Agentic extraction with optional tool calling.
        Providers that support tool calling override this.
        Default falls back to plain generate_json.
        """
        return await self.generate_json(prompt)
