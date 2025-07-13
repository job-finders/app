from typing import List, Dict, Type, Optional, Any
from pydantic import BaseModel
import httpx
import json
from src.config import config_instance
from src.utils.route_helpers import get_service


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None, default_timeout: float = 30.0):
        self.api_key = api_key or config_instance().OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.logger = None
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(default_timeout, read=default_timeout)
        )

    def init_app(self):
        if self.logger is None:
            self.logger = get_service("logger")()("openrouter_client")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
            max_tokens: int = 2024,
            stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Raw chat completion without parsing"""
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        self.logger.info(f"DEBUG: OpenRouter request data: {json.dumps(data, indent=2)}")

        response = await self._http_client.post(
            f"{self.base_url}/chat/completions",
            json=data,
            headers=self.headers
        )

        self.logger.info(f"DEBUG: OpenRouter response status: {response.status_code}")
        response.raise_for_status()
        return response.json()
    
    async def structured_completion(
        self,
        messages: List[Dict[str, str]],
        output_model: Type[BaseModel],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
            max_tokens: int = 2048,
        **kwargs
    ) -> BaseModel:
        """Structured completion with Pydantic parsing"""
        # Add schema to system message for better structured output
        schema_prompt = f"\nRespond with valid JSON matching this schema:\n{output_model.model_json_schema()}"
        
        enhanced_messages = messages.copy()
        self.logger.info(f"DEBUG: OpenRouter messages before schema: {json.dumps(enhanced_messages, indent=2)}")
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            enhanced_messages[0]["content"] += schema_prompt
        else:
            enhanced_messages.insert(0, {"role": "system", "content": schema_prompt})
        
        response = await self.chat_completion(
            enhanced_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs
        )

        self.logger.info(f"DEBUG: OpenRouter response: {response}")

        content = response["choices"][0]["message"]["content"]
        
        # Try to parse JSON if it's wrapped in code blocks
        try:
            if content.startswith("```json") and content.endswith("```"):
                content = content[7:-3].strip()
            elif content.startswith("```") and content.endswith("```"):
                content = content[3:-3].strip()
            
            return output_model.model_validate_json(content)
        except Exception:
            # Fallback to original parsing method
            return output_model.model_validate_json(content)
    
    async def agent_call(
        self,
        system_prompt: str,
        user_message: str,
        output_model: Optional[Type[BaseModel]] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
            max_tokens: int = 2048,
        **kwargs
    ) -> BaseModel | str:
        """Agent-friendly call with system/user separation"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if output_model:
            return await self.structured_completion(
                messages, output_model, model, temperature, max_tokens, **kwargs
            )
        else:
            response = await self.chat_completion(
                messages, model, temperature, max_tokens, **kwargs
            )
            return response["choices"][0]["message"]["content"]


# Backward compatibility function
async def call_openrouter(
    messages: List[Dict[str, str]],
    output_model: Type[BaseModel],
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> BaseModel:
    openrouter_client = OpenRouterClient()
    openrouter_client.init_app()

    return await openrouter_client.structured_completion(
        messages, output_model, model, temperature, max_tokens
    )