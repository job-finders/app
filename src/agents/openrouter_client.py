from __future__ import annotations
import json
from typing import Any, Dict, List, Type, Optional

import httpx
from pydantic import BaseModel, ValidationError

from src.config import config_instance
from src.utils.route_helpers import get_service


class OpenRouterClient:
    """
    Thin async wrapper around OpenRouter’s chat-completions endpoint.
    Handles:
      • unified HTTP client
      • structured (Pydantic) or plain completions
      • JSON-in-code-block sanitation
      • configurable logging & timeout
    """
    _ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or config_instance().OPENROUTER_API_KEY
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, read=timeout),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        self._log = get_service("logger")()("openrouter_client")

    # ------------------------------------------------------------------
    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **extras: Any,
    ) -> Dict[str, Any]:
        """Raw OpenRouter call returning the full JSON payload."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **extras,
        }
        self._log.debug("Request payload: %s", json.dumps(payload, indent=2))

        resp = await self._client.post(self._ENDPOINT, json=payload)
        self._log.debug("HTTP %s", resp.status_code)
        resp.raise_for_status()
        
        return resp.json()

    # ------------------------------------------------------------------
    async def structured_completion(
        self,
        messages: List[Dict[str, str]],
        output_model: Type[BaseModel],
        *,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **extras: Any,
    ) -> BaseModel:
        """
        Returns a Pydantic model validated from the assistant’s JSON reply.
        Injects the schema into the system message to improve reliability.
        """
        schema_prompt = (
            f"\nRespond with valid JSON matching this schema:\n{output_model.model_json_schema()}"
        )
        msgs = messages.copy()
        if msgs and msgs[0]["role"] == "system":
            msgs[0]["content"] += schema_prompt
        else:
            msgs.insert(0, {"role": "system", "content": schema_prompt})

        raw = await self.chat_completion(
            msgs, model=model, temperature=temperature, max_tokens=max_tokens, **extras
        )
        try:
            self._log.debug("Raw response: %s", json.dumps(raw, indent=2))
            content = raw["choices"][0]["message"]["content"]
        except KeyError as e:
            self._log.error("Malformed response: %s", raw)
            raise ValueError(f"Missing expected key in response: {e}")
            
        # remove ```json … ``` wrappers if present
        if content.startswith("```json") and content.endswith("```"):
            content = content[7:-3].strip()
        elif content.startswith("```") and content.endswith("```"):
            content = content[3:-3].strip()

        try:
            return output_model.model_validate_json(content)
        except ValidationError as e:
            self._log.warning("Validation failed: %s", e)
            raise

    # ------------------------------------------------------------------
    async def agent_call(
        self,
        system: str,
        user: str,
        *,
        output_model: Type[BaseModel] | None = None,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **extras: Any,
    ) -> BaseModel | str:
        """Convenience helper for agent-style (system + user) calls."""
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if output_model:
            return await self.structured_completion(
                messages, output_model, model=model, temperature=temperature, max_tokens=max_tokens, **extras
            )
        resp = await self.chat_completion(
            messages, model=model, temperature=temperature, max_tokens=max_tokens, **extras
        )
        return resp["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------
# Backward-compatibility alias
async def call_openrouter(
    messages: List[Dict[str, str]],
    output_model: Type[BaseModel],
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> BaseModel:
    async with OpenRouterClient() as cli:
        return await cli.structured_completion(
            messages, output_model, model=model, temperature=temperature, max_tokens=max_tokens
        )