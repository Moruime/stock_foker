"""Agent 抽象基类 — Template Method 模式。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.llm.client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)


class AgentResult:
    """Agent 统一返回结构。"""

    __slots__ = ("agent_name", "status", "data", "llm_used", "timestamp", "error_message")

    def __init__(
        self,
        agent_name: str,
        status: str = "success",
        data: dict | None = None,
        llm_used: bool = False,
        error_message: str | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.status = status  # "success" | "degraded" | "error"
        self.data = data or {}
        self.llm_used = llm_used
        self.timestamp = datetime.now().isoformat()
        self.error_message = error_message

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "data": self.data,
            "llm_used": self.llm_used,
            "timestamp": self.timestamp,
            "error_message": self.error_message,
        }


class BaseAgent(ABC):
    """所有 Agent 的抽象基类。

    子类需实现:
      - agent_name: 类属性
      - fetch_data(): 获取所需数据
      - build_prompt(): 构建 LLM Prompt
      - parse_response(): 解析 LLM 输出
      - fallback(): LLM 不可用时的降级逻辑
    """

    agent_name: str = "base"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or get_llm_client()

    def execute(self, **kwargs: Any) -> AgentResult:
        """执行 Agent 完整流程。"""
        try:
            # 1. 获取数据
            raw_data = self.fetch_data(**kwargs)

            # 2. 尝试 LLM 分析
            if self.llm.is_available():
                try:
                    messages = self.build_prompt(raw_data=raw_data, **kwargs)
                    llm_output = self.llm.chat_json(messages)
                    parsed = self.parse_response(llm_output, raw_data=raw_data, **kwargs)
                    return AgentResult(
                        agent_name=self.agent_name,
                        status="success",
                        data=parsed,
                        llm_used=True,
                    )
                except Exception as e:
                    logger.warning(
                        "%s Agent LLM 调用失败，降级处理: %s", self.agent_name, e
                    )

            # 3. 降级
            fallback_data = self.fallback(raw_data=raw_data, **kwargs)
            return AgentResult(
                agent_name=self.agent_name,
                status="degraded",
                data=fallback_data,
                llm_used=False,
            )

        except Exception as e:
            logger.error("%s Agent 执行失败: %s", self.agent_name, e)
            return AgentResult(
                agent_name=self.agent_name,
                status="error",
                data={},
                llm_used=False,
                error_message=str(e),
            )

    @abstractmethod
    def fetch_data(self, **kwargs: Any) -> dict:
        """获取 Agent 所需的原始数据。"""

    @abstractmethod
    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        """构建 LLM Prompt messages。"""

    @abstractmethod
    def parse_response(self, llm_output: dict, *, raw_data: dict, **kwargs: Any) -> dict:
        """解析 LLM 输出并合并原始数据。"""

    @abstractmethod
    def fallback(self, *, raw_data: dict, **kwargs: Any) -> dict:
        """LLM 不可用时的降级逻辑。"""
