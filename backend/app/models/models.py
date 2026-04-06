from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum as SAEnum, UniqueConstraint
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class TimeFrame(str, enum.Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class TradeType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class MarketSentiment(str, enum.Enum):
    OPTIMISTIC = "optimistic"
    NEUTRAL = "neutral"
    PESSIMISTIC = "pessimistic"


class RecordMode(str, enum.Enum):
    BACKFILL = "backfill"
    REALTIME = "realtime"


class FocusStock(Base):
    """当前关注的股票"""
    __tablename__ = "focus_stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), nullable=False)
    time_frame = Column(SAEnum(TimeFrame), default=TimeFrame.SHORT)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TradeRecord(Base):
    """交易操作记录"""
    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), nullable=False)
    trade_type = Column(SAEnum(TradeType), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text)
    market_sentiment = Column(SAEnum(MarketSentiment))
    target_price = Column(Float)
    expected_hold_days = Column(Integer)
    actual_result = Column(Float)
    result_note = Column(Text)
    traded_at = Column(DateTime, nullable=False)
    record_mode = Column(SAEnum(RecordMode), nullable=False, default=RecordMode.REALTIME)
    created_at = Column(DateTime, server_default=func.now())


class KlineCache(Base):
    """K线数据本地缓存"""
    __tablename__ = "kline_cache"
    __table_args__ = (
        UniqueConstraint("stock_code", "period", "date", name="uq_kline"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    period = Column(String(10), nullable=False)  # daily / weekly / monthly
    date = Column(String(10), nullable=False)     # YYYY-MM-DD
    open = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    turnover = Column(Float, default=0)


class AgentResultCache(Base):
    """Agent 结果缓存"""
    __tablename__ = "agent_result_cache"
    __table_args__ = (
        UniqueConstraint("agent_name", "stock_code", "cache_key", name="uq_agent_cache"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(50), nullable=False, index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    cache_key = Column(String(100), nullable=False)  # 如日期 "2026-04-06"
    status = Column(String(20), nullable=False)  # success / degraded / error
    llm_used = Column(Integer, default=0)
    data = Column(Text, nullable=False)  # JSON 序列化
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class StockPosition(Base):
    """股票持仓信息"""
    __tablename__ = "stock_positions"
    __table_args__ = (
        UniqueConstraint("stock_code", name="uq_position_stock"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)
    cost_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    take_profit_price = Column(Float)
    stop_loss_price = Column(Float)
    first_buy_date = Column(DateTime, nullable=False)
    note = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
