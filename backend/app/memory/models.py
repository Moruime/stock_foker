"""Memory 系统数据模型。"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func

from app.db.database import Base


class ShortTermMemory(Base):
    """会话短期记忆 — 滑动窗口内的对话历史。"""
    __tablename__ = "short_term_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, index=True)
    role = Column(String(10), nullable=False)       # user / assistant / system / summary
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class LongTermMemory(Base):
    """长期记忆 — 持久化的投资洞察和用户偏好。"""
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, default="default", index=True)
    memory_type = Column(String(20), nullable=False, index=True)  # preference / insight / trade_pattern / query_history
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)           # JSON 结构化内容
    importance = Column(Float, default=0.5)          # 0-1 重要度
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserPreference(Base):
    """用户投资偏好（显式设置）。"""
    __tablename__ = "user_preference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, default="default", index=True)
    risk_appetite = Column(String(20), default="moderate")    # conservative / moderate / aggressive
    preferred_sectors = Column(Text, default="[]")            # JSON list
    hold_period = Column(String(20), default="short")         # short / medium / long
    position_size_pref = Column(String(20), default="medium") # small / medium / large
    notes = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
