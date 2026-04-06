import os
from dataclasses import dataclass

from dotenv import load_dotenv

# 加载 backend/.env（如果存在）
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(os.path.abspath(_env_path))


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool
    provider: str
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    enable_thinking: bool


def get_llm_config() -> LLMConfig:
    return LLMConfig(
        enabled=os.getenv("LLM_ENABLED", "false").lower() == "true",
        provider=os.getenv("LLM_PROVIDER", ""),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        enable_thinking=os.getenv("LLM_ENABLE_THINKING", "true").lower() == "true",
    )
