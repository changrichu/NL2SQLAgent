"""Unified LLM interface — supports OpenAI / DeepSeek / Qwen / Doubao / Zhipu.

All providers expose an OpenAI-compatible Chat Completions endpoint, so we
funnel every call through the official `openai` SDK.
"""
from typing import List, Dict, Optional

from openai import OpenAI

from .config import settings


class LLMClient:
    PROVIDERS: Dict[str, Dict[str, str]] = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "default_model": "gpt-4o-mini",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "api_key_env": "DEEPSEEK_API_KEY",
            "default_model": "deepseek-chat",
        },
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key_env": "DASHSCOPE_API_KEY",
            "default_model": "qwen-plus",
        },
        "doubao": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "api_key_env": "DOUBAO_API_KEY",
            "default_model": "doubao-pro-32k",
        },
        "zhipu": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4/",
            "api_key_env": "ZHIPU_API_KEY",
            "default_model": "glm-4-plus",
        },
    }

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        provider = provider or settings.llm_provider
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        cfg = self.PROVIDERS[provider]
        api_key = settings.get(cfg["api_key_env"])
        if not api_key:
            raise ValueError(
                f"Missing API key for provider '{provider}'. "
                f"Set {cfg['api_key_env']} in your .env file."
            )

        self.provider = provider
        self.model = model or settings.llm_model or cfg["default_model"]
        self.client = OpenAI(api_key=api_key, base_url=cfg["base_url"])

    def chat(self, prompt: str, system: Optional[str] = None, temperature: float = 0.1) -> str:
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
