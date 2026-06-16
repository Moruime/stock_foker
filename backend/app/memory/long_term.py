"""长期记忆管理 — 持久化 + 关键词检索（向量检索预留）。

当前实现使用 SQLite LIKE 关键词匹配。
sqlite-vec 向量检索作为增强路径，通过环境变量 MEMORY_USE_VECTOR=true 启用。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.memory.models import LongTermMemory, UserPreference

logger = logging.getLogger(__name__)


class LongTermMemoryManager:
    """管理长期记忆的 CRUD + 检索。"""

    def __init__(self, db: Session, user_id: str = "default") -> None:
        self._db = db
        self._user_id = user_id

    # ------------------------------------------------------------------
    # 存储
    # ------------------------------------------------------------------

    def store(
        self,
        title: str,
        content: str | dict,
        memory_type: str = "insight",
        importance: float = 0.5,
    ) -> int:
        """存储一条长期记忆。

        Args:
            title: 记忆标题（用于关键词检索）
            content: 记忆内容（字符串或 JSON dict）
            memory_type: preference / insight / trade_pattern / query_history
            importance: 重要度 0-1

        Returns:
            记忆 ID
        """
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)

        memory = LongTermMemory(
            user_id=self._user_id,
            memory_type=memory_type,
            title=title,
            content=content,
            importance=importance,
        )
        self._db.add(memory)
        self._db.commit()
        self._db.refresh(memory)
        logger.info("存储长期记忆: [%s] %s (id=%d)", memory_type, title, memory.id)
        return memory.id

    def store_trade_insight(self, stock_name: str, insight: str, trade_result: float) -> int:
        """从交易结果中提取投资教训并存储。"""
        content = {
            "stock_name": stock_name,
            "insight": insight,
            "trade_result": trade_result,
            "extracted_at": datetime.now().isoformat(),
        }
        importance = min(abs(trade_result) / 10, 1.0)  # 盈亏越大越重要
        return self.store(
            title=f"{stock_name}交易教训: {insight[:50]}",
            content=content,
            memory_type="trade_pattern",
            importance=importance,
        )

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------

    def recall(self, query: str, top_k: int = 5, memory_type: str | None = None) -> list[dict]:
        """检索相关记忆。

        当前实现: 关键词 LIKE 匹配 + 重要度排序。
        TODO: sqlite-vec 向量相似度检索。

        Args:
            query: 检索查询
            top_k: 返回最多 K 条
            memory_type: 限定记忆类型（可选）

        Returns:
            记忆列表 [{"id", "title", "content", "memory_type", "importance"}]
        """
        # 提取关键词
        keywords = self._extract_keywords(query)

        base_query = self._db.query(LongTermMemory).filter(
            LongTermMemory.user_id == self._user_id,
        )

        if memory_type:
            base_query = base_query.filter(LongTermMemory.memory_type == memory_type)

        # 关键词匹配
        if keywords:
            conditions = []
            for kw in keywords:
                conditions.append(LongTermMemory.title.contains(kw))
                conditions.append(LongTermMemory.content.contains(kw))
            base_query = base_query.filter(or_(*conditions))

        results = base_query.order_by(
            LongTermMemory.importance.desc(),
            LongTermMemory.access_count.desc(),
        ).limit(top_k).all()

        # 更新访问记录
        for r in results:
            r.access_count = (r.access_count or 0) + 1
            r.last_accessed = datetime.now()
        if results:
            self._db.commit()

        return [
            {
                "id": r.id,
                "title": r.title,
                "content": r.content,
                "memory_type": r.memory_type,
                "importance": r.importance,
            }
            for r in results
        ]

    def _extract_keywords(self, query: str) -> list[str]:
        """从查询中提取关键词（简单分词）。"""
        # 去除常见停用词，按空格分割
        stop_words = {"的", "了", "是", "在", "和", "与", "对", "从", "到", "也", "就", "都"}
        words = []
        # 简单分词：按空格和标点分割
        import re
        tokens = re.split(r'[\s,，。、；;：:！!？?]+', query)
        for t in tokens:
            t = t.strip()
            if len(t) >= 2 and t not in stop_words:
                words.append(t)
        return words[:5]  # 最多 5 个关键词

    # ------------------------------------------------------------------
    # 用户偏好
    # ------------------------------------------------------------------

    def get_user_preference(self) -> dict:
        """获取用户投资偏好。"""
        pref = self._db.query(UserPreference).filter(
            UserPreference.user_id == self._user_id,
        ).first()

        if not pref:
            return {
                "risk_appetite": "moderate",
                "preferred_sectors": [],
                "hold_period": "short",
                "position_size_pref": "medium",
                "notes": "",
            }

        return {
            "risk_appetite": pref.risk_appetite,
            "preferred_sectors": json.loads(pref.preferred_sectors) if pref.preferred_sectors else [],
            "hold_period": pref.hold_period,
            "position_size_pref": pref.position_size_pref,
            "notes": pref.notes or "",
        }

    def update_user_preference(self, **kwargs) -> None:
        """更新用户偏好。"""
        pref = self._db.query(UserPreference).filter(
            UserPreference.user_id == self._user_id,
        ).first()

        if not pref:
            pref = UserPreference(user_id=self._user_id)
            self._db.add(pref)

        for key, value in kwargs.items():
            if key == "preferred_sectors" and isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False)
            if hasattr(pref, key):
                setattr(pref, key, value)

        self._db.commit()

    # ------------------------------------------------------------------
    # 管理
    # ------------------------------------------------------------------

    def list_memories(self, memory_type: str | None = None, limit: int = 20) -> list[dict]:
        """列出记忆。"""
        q = self._db.query(LongTermMemory).filter(
            LongTermMemory.user_id == self._user_id,
        )
        if memory_type:
            q = q.filter(LongTermMemory.memory_type == memory_type)
        results = q.order_by(LongTermMemory.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "memory_type": r.memory_type,
                "importance": r.importance,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in results
        ]

    def delete_memory(self, memory_id: int) -> bool:
        """删除指定记忆。"""
        row = self._db.query(LongTermMemory).filter(
            LongTermMemory.id == memory_id,
            LongTermMemory.user_id == self._user_id,
        ).first()
        if row:
            self._db.delete(row)
            self._db.commit()
            return True
        return False
