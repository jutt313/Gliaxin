import os
from typing import Optional

import anthropic
import openai

from providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """
    Anthropic Claude provider for generation.
    Embeddings use OpenAI (Claude has no embedding API).
    Requires OPENAI_API_KEY to be set for embeddings.
    """

    def __init__(
        self,
        anthropic_api_key: str,
        gen_model: str,
        openai_api_key: Optional[str] = None,
        embed_model: str = "text-embedding-3-small",
    ):
        self._gen_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        self._gen_model = gen_model
        self._embed_model = embed_model
        self._embed_client: Optional[openai.AsyncOpenAI] = None
        if openai_api_key:
            self._embed_client = openai.AsyncOpenAI(api_key=openai_api_key)

    async def generate_json(self, prompt: str, temperature: float = 0.2) -> str:
        resp = await self._gen_client.messages.create(
            model=self._gen_model,
            max_tokens=4096,
            temperature=temperature,
            messages=[{
                "role": "user",
                "content": prompt + "\n\nRespond with valid JSON only. No markdown fences.",
            }],
        )
        return resp.content[0].text if resp.content else ""

    async def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        resp = await self._gen_client.messages.create(
            model=self._gen_model,
            max_tokens=1024,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.content[0].text if resp.content else "").strip()

    async def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        if not self._embed_client:
            raise RuntimeError(
                "Claude provider requires OPENAI_API_KEY for embeddings. "
                "Set OPENAI_API_KEY in your .env to use Claude as the generation provider."
            )
        resp = await self._embed_client.embeddings.create(
            model=self._embed_model,
            input=text,
            dimensions=768,
        )
        return resp.data[0].embedding
