export interface FocusStock {
  id: number;
  stock_code: string;
  stock_name: string;
  time_frame: 'short' | 'medium' | 'long';
  is_active: number;
  created_at: string;
}

export interface StockSearchResult {
  stock_code: string;
  stock_name: string;
  type?: 'stock' | 'index' | 'etf';
}

export interface KlineData {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  turnover?: number;
}

export interface TechnicalIndicators {
  ma5: (number | null)[];
  ma10: (number | null)[];
  ma20: (number | null)[];
  ma60: (number | null)[];
  macd: { dif: number[]; dea: number[]; histogram: number[] };
  kdj: { k: number[]; d: number[]; j: number[] };
  rsi: (number | null)[];
  boll: { upper: number[]; middle: number[]; lower: number[] };
  volumes: number[];
}

export interface TradingAdvice {
  signal: 'buy' | 'sell' | 'hold';
  confidence: number;
  reasoning: string[];
  indicators_summary: Record<string, number>;
}

export interface StockAnalysis {
  kline_data: KlineData[];
  indicators: TechnicalIndicators;
  advice: TradingAdvice;
  time_frame: string;
}

export type RecordMode = 'backfill' | 'realtime';

export interface TradeRecord {
  id: number;
  stock_code: string;
  stock_name: string;
  trade_type: 'buy' | 'sell';
  price: number;
  quantity: number;
  reason?: string;
  market_sentiment?: 'optimistic' | 'neutral' | 'pessimistic';
  target_price?: number;
  expected_hold_days?: number;
  actual_result?: number;
  result_note?: string;
  traded_at: string;
  record_mode: RecordMode;
  created_at: string;
}

export interface TradeRecordCreate {
  stock_code: string;
  stock_name: string;
  trade_type: 'buy' | 'sell';
  price: number;
  quantity: number;
  reason?: string;
  market_sentiment?: 'optimistic' | 'neutral' | 'pessimistic';
  target_price?: number;
  expected_hold_days?: number;
  traded_at: string;
  record_mode?: RecordMode;
}

export interface TradingProfile {
  total_trades: number;
  win_rate: number;
  avg_profit: number;
  avg_loss: number;
  profit_loss_ratio: number;
  avg_hold_days: number;
  trade_frequency: string;
  preferred_time_frame: string;
  sentiment_accuracy: number;
  common_buy_reasons: { reason: string; count: number }[];
  common_sell_reasons: { reason: string; count: number }[];
}

export interface Position {
  id: number;
  stock_code: string;
  stock_name: string;
  cost_price: number;
  quantity: number;
  take_profit_price?: number;
  stop_loss_price?: number;
  first_buy_date: string;
  note?: string;
  created_at: string;
  updated_at: string;
}

export interface PositionCreate {
  stock_code: string;
  stock_name: string;
  cost_price: number;
  quantity: number;
  take_profit_price?: number;
  stop_loss_price?: number;
  first_buy_date: string;
  note?: string;
}

export interface PositionUpdate {
  cost_price?: number;
  quantity?: number;
  take_profit_price?: number;
  stop_loss_price?: number;
  note?: string;
}

// --- Agent Types ---
export interface AgentResult {
  agent_name: string;
  status: 'success' | 'degraded' | 'error';
  data: Record<string, unknown>;
  llm_used: boolean;
  timestamp: string;
  error_message?: string;
}

export interface EnhancedAnalysis {
  sentiment: AgentResult;
  sector: AgentResult;
  macro: AgentResult;
  enhanced_advice: AgentResult;
}

export interface LLMStatus {
  enabled: boolean;
  available: boolean;
  provider: string;
  api_key: string;
  base_url: string;
  model: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  enable_thinking: boolean;
}

// --- Snapshot Types ---
export interface AgentSnapshot {
  id: number;
  agent_type: string;
  stock_code: string;
  date: string;
  snapshot_data: Record<string, unknown>;
  llm_used: boolean;
  created_at: string;
  updated_at: string;
}
