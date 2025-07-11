from typing import List, Dict, Type, Optional, Any
from pydantic import BaseModel
import httpx
import json
from src.config import config_instance

class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config_instance().OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1024,
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
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def structured_completion(
        self,
        messages: List[Dict[str, str]],
        output_model: Type[BaseModel],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> BaseModel:
        """Structured completion with Pydantic parsing"""
        # Add schema to system message for better structured output
        schema_prompt = f"\nRespond with valid JSON matching this schema:\n{output_model.model_json_schema()}"
        
        enhanced_messages = messages.copy()
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            enhanced_messages[0]["content"] += schema_prompt
        else:
            enhanced_messages.insert(0, {"role": "system", "content": schema_prompt})
        
        response = await self.chat_completion(
            enhanced_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
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
        max_tokens: int = 1024,
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

# Singleton instance
openrouter_client = OpenRouterClient()

# Backward compatibility function
async def call_openrouter(
    messages: List[Dict[str, str]],
    output_model: Type[BaseModel],
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> BaseModel:
    return await openrouter_client.structured_completion(
        messages, output_model, model, temperature, max_tokens
    )