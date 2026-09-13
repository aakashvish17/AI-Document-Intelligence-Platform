import os
import json
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings

class LLMService:
    """
    Model-Agnostic LLM Service supporting:
    1. Cloud Groq API (openai/gpt-oss-20b, openai/gpt-oss-120b, qwen/qwen3.6-27b)
    2. Local Ollama (qwen2.5:3b on GTX 1650)
    Automatic fallback across providers.
    """
    def __init__(self):
        pass

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_format: bool = False,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        target_provider = (provider or settings.LLM_PROVIDER or "groq").lower()

        if target_provider == "groq":
            # 1. Try Groq Cloud first
            res = await self._call_groq(system_prompt, user_prompt, temperature, json_format, model=model)
            if res.get("status") == "success":
                return res
            # Fallback to local Ollama
            print("[!] Groq unavailable or errored. Falling back to local Ollama...")
            return await self._call_ollama(system_prompt, user_prompt, temperature, json_format)
        else:
            # 1. Try Local Ollama first
            res = await self._call_ollama(system_prompt, user_prompt, temperature, json_format, model=model)
            if res.get("status") == "success":
                return res
            # Fallback to Groq if key configured
            if settings.GROQ_API_KEY:
                print("[!] Local Ollama unavailable. Falling back to Groq Cloud...")
                return await self._call_groq(system_prompt, user_prompt, temperature, json_format)
            return res

    async def _call_groq(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_format: bool = False,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query Groq Cloud API via ultra-fast OpenAI-compatible endpoint"""
        api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return {
                "status": "error",
                "text": "GROQ_API_KEY is not configured in .env",
                "model": "Groq"
            }

        target_model = model or settings.GROQ_MODEL or "openai/gpt-oss-20b"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 4096
        }
        if json_format:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    return {
                        "status": "success",
                        "text": content,
                        "model": f"Groq ({target_model})"
                    }
                else:
                    return {
                        "status": "error",
                        "text": f"Groq HTTP {res.status_code}: {res.text}",
                        "model": f"Groq ({target_model})"
                    }
        except Exception as e:
            return {
                "status": "error",
                "text": f"Groq API connection error: {str(e)}",
                "model": f"Groq ({target_model})"
            }

    async def _call_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_format: bool = False,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query local Ollama instance with pure text context"""
        target_model = model or settings.OLLAMA_MODEL or "qwen2.5:3b"
        try:
            payload: Dict[str, Any] = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": 8192
                }
            }
            if json_format:
                payload["format"] = "json"

            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json=payload
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("message", {}).get("content", "")
                    return {
                        "status": "success",
                        "text": content,
                        "model": f"Local Ollama ({target_model})"
                    }
                else:
                    return {
                        "status": "error",
                        "text": f"Ollama HTTP error {res.status_code}: {res.text}",
                        "model": f"Local Ollama ({target_model})"
                    }
        except Exception as e:
            return {
                "status": "error",
                "text": f"Local Ollama connection error: {str(e)}",
                "model": f"Local Ollama ({target_model})"
            }

llm_service = LLMService()
