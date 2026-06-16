"""LLM 统一客户端 — 走 OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

import httpx

from app.llm.config import LLMConfig, get_llm_config

logger = logging.getLogger(__name__)

# 模型定价（元/千token）
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    # (input_price, output_price) per 1000 tokens
    "qwen3-plus": (0.0008, 0.002),
    "qwen-plus": (0.0008, 0.002),
    "qwen-turbo": (0.0003, 0.0006),
    "qwen-max": (0.002, 0.006),
}


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """根据模型定价计算本次调用成本（元）。"""
    pricing = _MODEL_PRICING.get(model, (0.0008, 0.002))  # 默认 qwen3-plus
    return input_tokens * pricing[0] / 1000 + output_tokens * pricing[1] / 1000


class LLMClient:
    """对接任意 OpenAI 兼容模型的轻量客户端。"""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._cfg = config or get_llm_config()
        # trust_env=False：不读取 macOS 系统代理，直连 dashscope/OpenAI 等 LLM 接口
        # 避免系统代理故障导致 LLM 调用超时
        self._http = httpx.Client(trust_env=False, timeout=self._cfg.timeout)

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

        model = kwargs.get("model", self._cfg.model)
        body: dict[str, Any] = {
            "model": model,
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

        caller = kwargs.get("caller", "unknown")
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                t0 = time.time()
                resp = self._http.post(
                    url,
                    json=body,
                    headers=headers,
                )
                resp.raise_for_status()
                latency_ms = int((time.time() - t0) * 1000)
                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # 记录 token usage
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                self._record_usage(
                    model=model,
                    caller=caller,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                )

                return content.strip()
            except Exception as e:
                last_err = e
                logger.warning("LLM 调用失败 (attempt %d): %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)  # 指数退避: 1s, 2s

        raise RuntimeError(f"LLM 调用失败: {last_err}")

    def _record_usage(
        self,
        model: str,
        caller: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
    ) -> None:
        """异步记录 LLM 调用的 token 消耗到数据库（失败不阻断主流程）。"""
        try:
            from app.db.database import SessionLocal
            from app.models.models import LLMUsageLog

            total_tokens = input_tokens + output_tokens
            cost = _calc_cost(model, input_tokens, output_tokens)

            db = SessionLocal()
            try:
                log = LLMUsageLog(
                    model=model,
                    caller=caller,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost_yuan=round(cost, 6),
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.debug("Token usage 记录失败 (不影响主流程): %s", e)

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
