import os
from typing import Callable, Optional

from google import genai
from google.genai import types as genai_types

from providers.base import LLMProvider

_SEARCH_MEMORIES_TOOL = genai_types.Tool(
    function_declarations=[
        genai_types.FunctionDeclaration(
            name="search_memories",
            description=(
                "Search the user's existing memory vault for more context. "
                "Pass a query phrase and optionally a list of tags."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "query": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        description="Natural language phrase to search for",
                    ),
                    "tags": genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING),
                        description="Optional tag list to filter by",
                    ),
                },
                required=["query"],
            ),
        )
    ]
)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, gen_model: str, embed_model: str):
        self._api_key = api_key
        self._gen_model = gen_model
        self._embed_model = embed_model
        self._gen_client: Optional[genai.Client] = None
        self._embed_client: Optional[genai.Client] = None

    def _gen(self) -> genai.Client:
        if self._gen_client is None:
            self._gen_client = genai.Client(api_key=self._api_key)
        return self._gen_client

    def _emb(self) -> genai.Client:
        if self._embed_client is None:
            self._embed_client = genai.Client(api_key=self._api_key)
        return self._embed_client

    async def generate_json(self, prompt: str, temperature: float = 0.2) -> str:
        resp = await self._gen().aio.models.generate_content(
            model=self._gen_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=temperature,
            ),
        )
        return resp.text or ""

    async def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        resp = await self._gen().aio.models.generate_content(
            model=self._gen_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(temperature=temperature),
        )
        return (resp.text or "").strip()

    async def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        result = await self._emb().aio.models.embed_content(
            model=self._embed_model,
            contents=text,
            config=genai_types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=768,
            ),
        )
        return list(result.embeddings[0].values)

    async def generate_turn_json(
        self,
        prompt: str,
        search_fn: Optional[Callable] = None,
        max_tool_calls: int = 3,
    ) -> str:
        client = self._gen()
        contents = [genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])]
        tool_calls_made = 0

        while True:
            snapshot = contents
            resp = await client.aio.models.generate_content(
                model=self._gen_model,
                contents=snapshot,
                config=genai_types.GenerateContentConfig(
                    tools=[_SEARCH_MEMORIES_TOOL],
                    temperature=0.2,
                ),
            )

            tool_parts = [
                p for p in (resp.candidates[0].content.parts if resp.candidates else [])
                if hasattr(p, "function_call") and p.function_call
            ]

            if tool_parts and tool_calls_made < max_tool_calls and search_fn:
                contents.append(resp.candidates[0].content)
                tool_results = []
                for part in tool_parts:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    query = args.get("query", "")
                    tags = list(args.get("tags") or [])
                    tool_calls_made += 1
                    result_text = await search_fn(query, tags)
                    tool_results.append(
                        genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name=fc.name,
                                response={"result": result_text},
                            )
                        )
                    )
                contents.append(genai_types.Content(role="user", parts=tool_results))
                contents.append(genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=(
                        "Now using all the context above, return the final JSON array of memories. "
                        "No markdown, no prose — JSON array only."
                    ))],
                ))
            else:
                break

        return resp.text or ""
