"""Memory Manager — 统一管理短期和长期记忆，为 Agent 提供记忆注入接口。"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.memory.short_term import ShortTermMemoryManager
from app.memory.long_term import LongTermMemoryManager

logger = logging.getLogger(__name__)


class MemoryManager:
    """Memory 系统统一入口。

    提供:
    - 短期记忆管理（会话上下文）
    - 长期记忆检索（用户偏好 + 投资洞察）
    - Agent Prompt 注入（format_memory_context）
    """

    def __init__(self, db: Session, session_id: str = "default", user_id: str = "default") -> None:
        self.short_term = ShortTermMemoryManager(db, session_id)
        self.long_term = LongTermMemoryManager(db, user_id)
        self._db = db

    def format_memory_context(self, stock_name: str = "", time_frame: str = "") -> str:
        """为 Agent Prompt 生成 Memory 上下文字符串。

        包含:
        1. 用户偏好摘要
        2. 相关历史记忆（基于 stock_name 检索）
        3. 短期对话摘要（如有）

        Args:
            stock_name: 当前分析的股票名称
            time_frame: 投资时间框架

        Returns:
            可直接注入 Prompt 的文本
        """
        sections = []

        # 1. 用户偏好
        pref = self.long_term.get_user_preference()
        if pref.get("risk_appetite") != "moderate" or pref.get("preferred_sectors"):
            pref_text = self._format_preference(pref)
            sections.append(f"【用户偏好】\n{pref_text}")

        # 2. 相关长期记忆
        if stock_name:
            query = f"{stock_name} {time_frame}".strip()
            memories = self.long_term.recall(query, top_k=3)
            if memories:
                mem_text = "\n".join(
                    f"- {m['title']}: {m['content'][:100]}"
                    for m in memories
                )
                sections.append(f"【相关历史记忆】\n{mem_text}")

        # 3. 短期对话摘要
        context = self.short_term.get_context_window()
        summaries = [m for m in context if m["role"] == "summary"]
        if summaries:
            sections.append(f"【对话历史摘要】\n{summaries[-1]['content']}")

        if not sections:
            return ""

        return "\n\n".join(sections)

    def _format_preference(self, pref: dict) -> str:
        """格式化用户偏好为自然语言。"""
        parts = []
        risk_map = {
            "conservative": "保守型（偏好低波动、蓝筹股）",
            "moderate": "稳健型",
            "aggressive": "激进型（接受高波动，偏好成长股）",
        }
        parts.append(f"风险偏好: {risk_map.get(pref.get('risk_appetite', ''), '稳健型')}")

        if pref.get("preferred_sectors"):
            parts.append(f"偏好行业: {', '.join(pref['preferred_sectors'])}")

        hold_map = {"short": "短线(1-5天)", "medium": "中线(1-4周)", "long": "长线(1月+)"}
        parts.append(f"持有周期: {hold_map.get(pref.get('hold_period', ''), '短线')}")

        if pref.get("notes"):
            parts.append(f"备注: {pref['notes']}")

        return "; ".join(parts)

    def after_analysis(self, stock_name: str, signal: str, confidence: float, summary: str) -> None:
        """分析完成后的回调 — 自动存储查询记录到长期记忆。"""
        try:
            self.long_term.store(
                title=f"分析记录: {stock_name} → {signal}({confidence:.0%})",
                content={
                    "stock_name": stock_name,
                    "signal": signal,
                    "confidence": confidence,
                    "summary": summary[:200],
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                },
                memory_type="query_history",
                importance=confidence * 0.5,
            )
        except Exception as e:
            logger.debug("记录分析历史失败: %s", e)
