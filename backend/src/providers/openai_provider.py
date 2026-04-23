import os
from typing import Optional

import openai

from providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider — uses chat completions for generation and
    text-embedding-3-small with dimensions=768 to match the DB schema.
    """

    def __init__(self, api_key: str, gen_model: str, embed_model: str, base_url: Optional[str] = None):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**kwargs)
        self._gen_model = gen_model
        self._embed_model = embed_model

    async def generate_json(self, prompt: str, temperature: float = 0.2) -> str:
        resp = await self._client.chat.completions.create(
            model=self._gen_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    async def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        resp = await self._client.chat.completions.create(
            model=self._gen_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()

    async def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        resp = await self._client.embeddings.create(
            model=self._embed_model,
            input=text,
            dimensions=768,
        )
        return resp.data[0].embedding
