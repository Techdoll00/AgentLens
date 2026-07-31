"""OpenAI-compatible async LLM client.

Works with any API that implements the OpenAI chat completions interface
(OpenAI, DeepSeek, vLLM, LiteLLM proxy, etc.).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})


class OpenAIClient:
    """LLM client for OpenAI-compatible APIs.

    Parameters
    ----------
    model : str
        Model identifier (e.g. "deepseek-chat", "gpt-4o").
    api_key : str
        API key.
    base_url : str | None
        Override API base URL for compatible providers.
    max_retries : int
        Max retry attempts for transient failures.
    """

    def __init__(
        self,
        model: str = "deepseek-chat",
        *,
        api_key: str = "",
        base_url: str | None = None,
        max_retries: int = 3,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError("openai package required: pip install openai") from e

        self.model = model
        self._max_retries = max(1, max_retries)
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        delay = 2.0
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                if content is None:
                    raise RuntimeError("LLM returned empty content")
                return content
            except Exception as exc:
                last_exc = exc
                status = getattr(exc, "status_code", None)
                if status is not None and status not in _RETRYABLE_STATUS:
                    raise
                if attempt + 1 >= self._max_retries:
                    raise
                logger.warning("LLM transient error, retry %d/%d in %.1fs", attempt + 1, self._max_retries, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60.0)

        assert last_exc is not None
        raise last_exc

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> T:
        import json

        schema = response_model.model_json_schema()
        instruction = f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        augmented = list(messages)
        if augmented and augmented[-1]["role"] == "user":
            augmented[-1] = {**augmented[-1], "content": augmented[-1]["content"] + instruction}
        else:
            augmented.append({"role": "user", "content": instruction})

        raw = await self.generate_text(augmented, temperature=temperature, max_tokens=max_tokens)

        from src.llm.json_extract import extract_json
        extracted = extract_json(raw)
        return response_model.model_validate_json(extracted)

    async def close(self) -> None:
        await self._client.close()