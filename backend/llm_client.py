"""
Thin async wrapper around the Grok (xAI) chat completions API.
xAI's API is OpenAI-compatible, so plain httpx is used instead of a heavy SDK.
"""
import json
import logging
from typing import Any, Optional

import httpx

from config import settings

logger = logging.getLogger("acadease.llm")


class LLMError(Exception):
    pass


class GrokClient:
    def __init__(self):
        self.api_key = settings.grok_api_key
        self.base_url = settings.grok_api_base.rstrip("/")
        self.model = settings.grok_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> str:
        if not self.api_key:
            raise LLMError("GROK_API_KEY is not set. Add it to backend/.env before starting the server.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error("Grok API error: %s - %s", e.response.status_code, e.response.text)
            raise LLMError(f"Grok API returned {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("Grok API request failed: %s", e)
            raise LLMError("Could not reach Grok API") from e

    async def chat_json(
        self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 512
    ) -> Optional[dict]:
        raw = await self.chat(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            cleaned = raw.strip().strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
            try:
                return json.loads(cleaned)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse JSON from LLM response: %s", raw[:300])
                return None


grok_client = GrokClient()
