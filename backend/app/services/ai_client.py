"""Provider-agnostic LLM client (OpenAI-compatible chat completions).

The concrete base_url / api_key / model come from `.env` (LearnBuddy credits
are programmatically callable via an OpenAI-compatible endpoint). The client
records token usage and wall-clock latency so the evaluation harness can report
cost and latency per approach.
"""
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("autograder.ai")


@dataclass
class LLMResult:
    content: str
    usage: dict
    elapsed_seconds: float
    model: str


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.0,
        response_format: dict | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        url = f"{self.base_url}/chat/completions"
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {"Authorization": f"Bearer {self.api_key}"}
        start = time.monotonic()
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        elapsed = time.monotonic() - start

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        logger.info(
            "LLM 调用 model=%s 耗时=%.2fs tokens=%s",
            self.model,
            elapsed,
            usage.get("total_tokens", "?"),
        )
        return LLMResult(
            content=content,
            usage=usage,
            elapsed_seconds=elapsed,
            model=self.model,
        )


def get_llm() -> LLMClient | None:
    """Return a configured client, or None when LLM is not configured."""
    if not settings.llm_configured:
        return None
    return LLMClient(settings.llm_base_url, settings.llm_api_key, settings.llm_model)
