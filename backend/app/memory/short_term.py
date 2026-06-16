"""短期记忆管理 — 滑动窗口 + LLM 摘要压缩。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.memory.models import ShortTermMemory

logger = logging.getLogger(__name__)

# 配置
MAX_ROUNDS = 10           # 窗口最大轮数
SUMMARIZE_THRESHOLD = 8   # 超过此轮数时触发压缩
COMPRESS_COUNT = 5        # 压缩前 N 轮为摘要


class ShortTermMemoryManager:
    """管理会话级短期记忆。

    策略:
    - 维持最近 MAX_ROUNDS 轮对话
    - 超过 SUMMARIZE_THRESHOLD 时，将前 COMPRESS_COUNT 轮压缩为 summary
    - Summary 作为 system 消息注入 prompt
    """

    def __init__(self, db: Session, session_id: str) -> None:
        self._db = db
        self._session_id = session_id

    def add_message(self, role: str, content: str) -> None:
        """添加一条消息到短期记忆。"""
        # 粗略估算 token (中文约 1.5 token/字，英文约 1 token/4字符)
        token_count = max(len(content) // 2, len(content.encode("utf-8")) // 4)
        msg = ShortTermMemory(
            session_id=self._session_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self._db.add(msg)
        self._db.commit()

    def get_context_window(self) -> list[dict[str, str]]:
        """获取当前上下文窗口（含历史摘要 + 最近消息）。

        返回格式: [{"role": "system/user/assistant", "content": "..."}]
        """
        messages = self._db.query(ShortTermMemory).filter(
            ShortTermMemory.session_id == self._session_id,
        ).order_by(ShortTermMemory.created_at.asc()).all()

        result = []
        for msg in messages:
            result.append({"role": msg.role, "content": msg.content})

        return result

    def get_message_count(self) -> int:
        """获取当前会话的消息条数（不含 summary）。"""
        return self._db.query(ShortTermMemory).filter(
            ShortTermMemory.session_id == self._session_id,
            ShortTermMemory.role != "summary",
        ).count()

    def should_compress(self) -> bool:
        """是否需要压缩。"""
        return self.get_message_count() > SUMMARIZE_THRESHOLD

    def compress(self, llm_client=None) -> str | None:
        """压缩前 N 轮消息为摘要。

        Args:
            llm_client: LLMClient 实例，用于生成摘要。不传则使用简单截断。

        Returns:
            生成的摘要文本，或 None（如果不需要压缩）
        """
        if not self.should_compress():
            return None

        # 取所有非 summary 消息
        messages = self._db.query(ShortTermMemory).filter(
            ShortTermMemory.session_id == self._session_id,
            ShortTermMemory.role != "summary",
        ).order_by(ShortTermMemory.created_at.asc()).all()

        if len(messages) <= COMPRESS_COUNT:
            return None

        # 前 COMPRESS_COUNT 条需要压缩
        to_compress = messages[:COMPRESS_COUNT]
        compress_text = "\n".join(
            f"[{m.role}]: {m.content[:200]}" for m in to_compress
        )

        # 生成摘要
        if llm_client and llm_client.is_available():
            try:
                summary = llm_client.chat(
                    [
                        {"role": "system", "content": "你是一个对话摘要助手。请将以下对话历史压缩为一段简洁的摘要，保留关键信息（股票名称、分析结论、用户偏好等）。输出纯文本，不超过200字。"},
                        {"role": "user", "content": compress_text},
                    ],
                    max_tokens=300,
                    caller="memory_compress",
                )
            except Exception as e:
                logger.warning("LLM 摘要生成失败，使用简单截断: %s", e)
                summary = f"[历史摘要] {compress_text[:300]}..."
        else:
            summary = f"[历史摘要] {compress_text[:300]}..."

        # 删除被压缩的消息
        for msg in to_compress:
            self._db.delete(msg)

        # 插入摘要消息（作为最早的消息）
        summary_msg = ShortTermMemory(
            session_id=self._session_id,
            role="summary",
            content=summary,
            token_count=len(summary) // 2,
        )
        self._db.add(summary_msg)
        self._db.commit()

        logger.info("短期记忆压缩完成: 压缩 %d 条消息为摘要", len(to_compress))
        return summary

    def clear(self) -> None:
        """清空当前会话的短期记忆。"""
        self._db.query(ShortTermMemory).filter(
            ShortTermMemory.session_id == self._session_id,
        ).delete()
        self._db.commit()
