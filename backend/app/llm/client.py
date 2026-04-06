"""LLM 统一客户端 — 走 OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.llm.config import LLMConfig, get_llm_config

logger = logging.getLogger(__name__)


class LLMClient:
    """对接任意 OpenAI 兼容模型的轻量客户端。"""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._cfg = config or get_llm_config()

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        return (
            self._cfg.enabled
            and bool(self._cfg.api_key)
            and self._cfg.api_key != "your-api-key-here"
        )

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """发送 chat completion 请求，返回纯文本回复。"""
        if not self.is_available():
            raise RuntimeError("LLM 未启用或 API Key 未配置")

        body: dict[str, Any] = {
            "model": kwargs.get("model", self._cfg.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self._cfg.temperature),
            "max_tokens": kwargs.get("max_tokens", self._cfg.max_tokens),
        }

        # Qwen3 等支持 thinking 模式的模型，可通过此参数关闭深度推理以降低延迟
        if not self._cfg.enable_thinking:
            body["enable_thinking"] = False

        url = f"{self._cfg.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._cfg.api_key}",
            "Content-Type": "application/json",
        }

        last_err: Exception | None = None
        for attempt in range(1):
            try:
                resp = httpx.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=self._cfg.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
            except Exception as e:
                last_err = e
                logger.warning("LLM 调用失败 (attempt %d): %s", attempt + 1, e)

        raise RuntimeError(f"LLM 调用失败: {last_err}")

    def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict:
        """发送 chat completion 请求，解析 JSON 格式回复。"""
        raw = self.chat(messages, **kwargs)

        # 提取 JSON（兼容 markdown code block 包裹的情况）
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LLM 输出非法 JSON，尝试容错提取: %s", text[:200])
            # 尝试找到第一个 { 和最后一个 }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise RuntimeError(f"LLM 输出无法解析为 JSON: {text[:200]}")

    def get_status(self) -> dict:
        """返回当前 LLM 配置状态（脱敏）。"""
        cfg = self._cfg
        key_display = ""
        if cfg.api_key:
            if cfg.api_key == "your-api-key-here":
                key_display = "(未配置)"
            elif len(cfg.api_key) > 8:
                key_display = cfg.api_key[:4] + "****" + cfg.api_key[-4:]
            else:
                key_display = "****"
        return {
            "enabled": cfg.enabled,
            "available": self.is_available(),
            "provider": cfg.provider,
            "api_key": key_display,
            "base_url": cfg.base_url,
            "model": cfg.model,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "timeout": cfg.timeout,
            "enable_thinking": cfg.enable_thinking,
        }


# 模块级单例
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reload_llm_client() -> LLMClient:
    """重新加载配置并刷新单例（用于 .env 变更后）。"""
    global _client
    from app.llm.config import get_llm_config
    _client = LLMClient(config=get_llm_config())
    return _client
