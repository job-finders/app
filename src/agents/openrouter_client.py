# src/agents/openrouter_client.py

from typing import List, Dict, Type
from pydantic import BaseModel
import httpx
from src.config import config_instance

async def call_openrouter(
    messages: List[Dict[str, str]],
    output_model: Type[BaseModel],
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> BaseModel:
    OPENROUTER_API_KEY = config_instance().OPENROUTER_API_KEY
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]["content"]

    return output_model.parse_raw(message)
