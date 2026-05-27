import os
from typing import Optional

from dotenv import load_dotenv

from .utils import setup_logging

logger = setup_logging("llm_client")

load_dotenv()


class LLMClient:
    """统一的 LLM 调用接口，支持 OpenAI 兼容 API（含 DeepSeek）和 Anthropic"""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "") or None
        self.max_tokens = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "32768"))

        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY 未设置。请在 .env 文件中配置或设置环境变量。"
            )

    def call(self, prompt: str, system: str = "", response_format: Optional[str] = None) -> str:
        if self.provider == "openai":
            return self._call_openai(prompt, system, response_format)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, system)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    def _call_openai(self, prompt: str, system: str, response_format: Optional[str]) -> str:
        from openai import OpenAI

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = OpenAI(**client_kwargs)
        kwargs = {
            "model": self.model,
            "messages": [],
            "temperature": 0.7,
            "max_tokens": self.max_tokens,
        }
        if system:
            kwargs["messages"].append({"role": "system", "content": system})
        kwargs["messages"].append({"role": "user", "content": prompt})

        if response_format == "json":
            from openai import NOT_GIVEN

            kwargs["response_format"] = {"type": "json_object"}

        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str, system: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        resp = client.messages.create(**kwargs)
        return resp.content[0].text if resp.content else ""


def get_llm_client() -> LLMClient:
    """工厂函数，从环境变量创建 LLM 客户端"""
    return LLMClient()
