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
