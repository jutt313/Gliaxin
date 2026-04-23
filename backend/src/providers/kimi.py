import os
from typing import Optional

from providers.openai_provider import OpenAIProvider

# Kimi (Moonshot AI) is OpenAI-compatible.
# It does not have a native embedding API, so embeddings fall back to OpenAI.
# Set KIMI_API_KEY and optionally OPENAI_API_KEY for embeddings.

KIMI_BASE_URL = "https://api.moonshot.cn/v1"


class KimiProvider(OpenAIProvider):
    """
    Kimi (Moonshot AI) provider — uses the OpenAI-compatible API for generation.
    Embeddings fall back to OpenAI text-embedding-3-small.
    Set OPENAI_API_KEY in .env to enable embeddings when using Kimi.
    """

    def __init__(
        self,
        kimi_api_key: str,
        gen_model: str = "moonshot-v1-8k",
        openai_api_key: Optional[str] = None,
        embed_model: str = "text-embedding-3-small",
    ):
        super().__init__(
            api_key=kimi_api_key,
            gen_model=gen_model,
            embed_model=embed_model,
            base_url=KIMI_BASE_URL,
        )
        self._openai_api_key = openai_api_key
        self._openai_embed_client = None
        if openai_api_key:
            import openai
            self._openai_embed_client = openai.AsyncOpenAI(api_key=openai_api_key)

    async def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        if self._openai_embed_client:
            import openai
            resp = await self._openai_embed_client.embeddings.create(
                model=self._embed_model,
                input=text,
                dimensions=768,
            )
            return resp.data[0].embedding
        raise RuntimeError(
            "Kimi provider requires OPENAI_API_KEY for embeddings. "
            "Set OPENAI_API_KEY in your .env."
        )
