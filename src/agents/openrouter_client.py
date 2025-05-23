# openrouter_client.py
import os
import httpx
from pydantic import BaseModel
from typing import Type

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

async def call_openrouter(prompt: str, output_model: Type[BaseModel]) -> BaseModel:
    """
    Calls DeepSeek via OpenRouter and parses response into structured Pydantic output.
    """
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(OPENROUTER_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return output_model.parse_raw(content)
