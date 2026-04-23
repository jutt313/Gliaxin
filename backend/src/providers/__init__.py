"""
Provider factory. Reads ACTIVE_LLM_PROVIDER from env and returns the right LLMProvider.

Supported values for ACTIVE_LLM_PROVIDER:
  gemini   — Google Gemini (default; needs GEMINI_API_KEY)
  openai   — OpenAI       (needs OPENAI_API_KEY)
  claude   — Anthropic    (needs ANTHROPIC_API_KEY + OPENAI_API_KEY for embeddings)
  kimi     — Moonshot AI  (needs KIMI_API_KEY + OPENAI_API_KEY for embeddings)
"""

import os
from providers.base import LLMProvider

_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is not None:
        return _provider

    active = os.getenv("ACTIVE_LLM_PROVIDER", "gemini").strip().lower()

    if active == "gemini":
        from providers.gemini import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for ACTIVE_LLM_PROVIDER=gemini")
        _provider = GeminiProvider(
            api_key=api_key,
            gen_model=os.getenv("GEMINI_GEN_MODEL", "gemini-2.5-flash"),
            embed_model=os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001"),
        )

    elif active == "openai":
        from providers.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for ACTIVE_LLM_PROVIDER=openai")
        _provider = OpenAIProvider(
            api_key=api_key,
            gen_model=os.getenv("OPENAI_GEN_MODEL", "gpt-4o-mini"),
            embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        )

    elif active == "claude":
        from providers.claude import ClaudeProvider
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for ACTIVE_LLM_PROVIDER=claude")
        _provider = ClaudeProvider(
            anthropic_api_key=api_key,
            gen_model=os.getenv("CLAUDE_GEN_MODEL", "claude-sonnet-4-6"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        )

    elif active == "kimi":
        from providers.kimi import KimiProvider
        api_key = os.getenv("KIMI_API_KEY")
        if not api_key:
            raise RuntimeError("KIMI_API_KEY is required for ACTIVE_LLM_PROVIDER=kimi")
        _provider = KimiProvider(
            kimi_api_key=api_key,
            gen_model=os.getenv("KIMI_GEN_MODEL", "moonshot-v1-8k"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        )

    else:
        raise RuntimeError(
            f"Unknown ACTIVE_LLM_PROVIDER={active!r}. "
            "Choose: gemini, openai, claude, kimi"
        )

    return _provider


def reset_provider() -> None:
    """Force re-init on next get_provider() call. Useful in tests."""
    global _provider
    _provider = None
