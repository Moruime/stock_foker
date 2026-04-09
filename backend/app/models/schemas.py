from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional
from app.models.models import TimeFrame, TradeType, MarketSentiment, RecordMode


# --- Focus Stock Schemas ---
class FocusStockCreate(BaseModel):
    stock_code: str
    stock_name: str
    time_frame: TimeFrame = TimeFrame.SHORT


class FocusStockResponse(BaseModel):
    id: int
    stock_code: str
    stock_name: str
    time_frame: TimeFrame
    is_active: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TimeFrameUpdate(BaseModel):
    time_frame: TimeFrame


# --- Trade Record Schemas ---
class TradeRecordCreate(BaseModel):
    stock_code: str
    stock_name: str
    trade_type: TradeType
    price: float
    quantity: int
    reason: Optional[str] = None
    market_sentiment: Optional[MarketSentiment] = None
    target_price: Optional[float] = None
    expected_hold_days: Optional[int] = None
    traded_at: datetime
    record_mode: RecordMode = RecordMode.REALTIME


class TradeRecordUpdate(BaseModel):
    trade_type: Optional[TradeType] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    reason: Optional[str] = None
    market_sentiment: Optional[MarketSentiment] = None
    target_price: Optional[float] = None
    expected_hold_days: Optional[int] = None
    traded_at: Optional[datetime] = None
    actual_result: Optional[float] = None
    result_note: Optional[str] = None


class TradeRecordResponse(BaseModel):
    id: int
    stock_code: str
    stock_name: str
    trade_type: TradeType
    price: float
    quantity: int
    reason: Optional[str] = None
    market_sentiment: Optional[MarketSentiment] = None
    target_price: Optional[float] = None
    expected_hold_days: Optional[int] = None
    actual_result: Optional[float] = None
    result_note: Optional[str] = None
    traded_at: datetime
    record_mode: RecordMode = RecordMode.REALTIME
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Stock Data Schemas ---
class KlineData(BaseModel):
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    turnover: Optional[float] = None


class TechnicalIndicators(BaseModel):
    ma5: Optional[list[Optional[float]]] = None
    ma10: Optional[list[Optional[float]]] = None
    ma20: Optional[list[Optional[float]]] = None
    ma60: Optional[list[Optional[float]]] = None
    macd: Optional[dict] = None
    kdj: Optional[dict] = None
    rsi: Optional[list[Optional[float]]] = None
    boll: Optional[dict] = None
    volumes: Optional[list[Optional[float]]] = None


class StockKlineResponse(BaseModel):
    stock_code: str
    stock_name: str
    kline_data: list[KlineData]
    indicators: TechnicalIndicators


# --- Trading Profile Schemas ---
class TradingProfile(BaseModel):
    total_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_loss_ratio: float
    avg_hold_days: float
    trade_frequency: str
    preferred_time_frame: str
    sentiment_accuracy: float
    common_buy_reasons: list[dict]
    common_sell_reasons: list[dict]


# --- Trading Advice Schemas ---
class TradingAdvice(BaseModel):
    signal: str  # "buy" / "sell" / "hold"
    confidence: float
    reasoning: list[str]
    indicators_summary: dict


# --- Position Schemas ---
class PositionCreate(BaseModel):
    stock_code: str
    stock_name: str
    cost_price: float
    quantity: int
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    first_buy_date: datetime
    note: Optional[str] = None


class PositionUpdate(BaseModel):
    cost_price: Optional[float] = None
    quantity: Optional[int] = None
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    note: Optional[str] = None


class PositionResponse(BaseModel):
    id: int
    stock_code: str
    stock_name: str
    cost_price: float
    quantity: int
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    first_buy_date: datetime
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Agent Schemas ---
class AgentResultResponse(BaseModel):
    agent_name: str
    status: str  # success / degraded / error
    data: dict[str, Any]
    llm_used: bool
    timestamp: str
    error_message: Optional[str] = None


class AgentRunRequest(BaseModel):
    stock_code: str
    stock_name: str


class EnhancedAnalysisResponse(BaseModel):
    sentiment: AgentResultResponse
    sector: AgentResultResponse
    macro: AgentResultResponse
    enhanced_advice: AgentResultResponse


class LLMStatusResponse(BaseModel):
    enabled: bool
    available: bool
    provider: str
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    enable_thinking: bool


# --- Snapshot Schemas ---
class SnapshotResponse(BaseModel):
    id: int
    agent_type: str
    stock_code: str
    date: str
    snapshot_data: dict[str, Any]
    llm_used: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
