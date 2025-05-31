# src/agents/openrouter_client.py

from typing import Type
from pydantic import BaseModel
import httpx
from src.config import config_instance

# src/agents/openrouter_client.py

async def call_openrouter(prompt: str, output_model: Type[BaseModel], system_prompt: str) -> BaseModel:
    OPENROUTER_API_KEY = config_instance().OPENROUTER_API_KEY
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",  # or your preferred default
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]["content"]

    return output_model.parse_raw(message)

