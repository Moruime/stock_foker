import axios from 'axios';
import type {
  FocusStock,
  StockSearchResult,
  StockAnalysis,
  TradeRecord,
  TradeRecordCreate,
  TradingProfile,
  Position,
  PositionCreate,
  PositionUpdate,
  AgentResult,
  EnhancedAnalysis,
  LLMStatus,
  AgentSnapshot,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
});

// --- 股票关注 ---
export const getFocusStock = () =>
  api.get<FocusStock | null>('/focus').then((r) => r.data);

export const setFocusStock = (data: {
  stock_code: string;
  stock_name: string;
  time_frame: string;
}) => api.post<FocusStock>('/focus', data).then((r) => r.data);

export const updateTimeFrame = (time_frame: string) =>
  api.put<FocusStock>('/focus/timeframe', { time_frame }).then((r) => r.data);

export const getFocusHistory = () =>
  api.get<FocusStock[]>('/focus/history').then((r) => r.data);

// --- 搜索 ---
export const searchStocks = (keyword: string) =>
  api.get<StockSearchResult[]>('/stocks/search', { params: { keyword } }).then((r) => r.data);

// --- K线与分析 ---
export const getStockAnalysis = (
  stockCode: string,
  period = 'daily',
  startDate?: string,
  endDate?: string,
  refresh?: boolean,
) =>
  api
    .get<StockAnalysis>(`/stocks/${stockCode}/analysis`, {
      params: { period, start_date: startDate, end_date: endDate, refresh: refresh || undefined },
    })
    .then((r) => r.data);

// --- 交易记录 ---
export const getTradeRecords = (stockCode?: string) =>
  api
    .get<TradeRecord[]>('/trades', { params: { stock_code: stockCode } })
    .then((r) => r.data);

export const createTradeRecord = (data: TradeRecordCreate) =>
  api.post<TradeRecord>('/trades', data).then((r) => r.data);

export const updateTradeRecord = (
  id: number,
  data: Record<string, unknown>,
) => api.put<TradeRecord>(`/trades/${id}`, data).then((r) => r.data);

export const deleteTradeRecord = (id: number) =>
  api.delete(`/trades/${id}`).then((r) => r.data);

export interface BatchDeleteResult {
  deleted: number;
  realtime_adjusted: number;
  total: number;
}

export const batchDeleteTradeRecords = (ids: number[]) =>
  api.post<BatchDeleteResult>('/trades/batch-delete', ids).then((r) => r.data);

export interface ImportResult {
  success: number;
  skipped: number;
  duplicated: number;
  errors: string[];
  total: number;
}

export const importTradeRecords = (file: File): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  return api
    .post<ImportResult>('/trades/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};

// --- 画像 ---
export const getTradingProfile = (stockCode?: string) =>
  api
    .get<TradingProfile>('/profile', { params: { stock_code: stockCode } })
    .then((r) => r.data);

// --- 持仓管理 ---
export const getPosition = (stockCode: string) =>
  api.get<Position | null>(`/positions/${stockCode}`).then((r) => r.data);

export const createPosition = (data: PositionCreate) =>
  api.post<Position>('/positions', data).then((r) => r.data);

export const updatePosition = (stockCode: string, data: PositionUpdate) =>
  api.put<Position>(`/positions/${stockCode}`, data).then((r) => r.data);

export const deletePosition = (stockCode: string) =>
  api.delete(`/positions/${stockCode}`).then((r) => r.data);

// --- Agent ---
export const runSentimentAgent = (stockCode: string, stockName: string) =>
  api
    .post<AgentResult>('/agent/sentiment', { stock_code: stockCode, stock_name: stockName })
    .then((r) => r.data);

export const runSectorAgent = (stockCode: string, stockName: string) =>
  api
    .post<AgentResult>('/agent/sector', { stock_code: stockCode, stock_name: stockName })
    .then((r) => r.data);

export const runMacroAgent = (stockCode: string, stockName: string) =>
  api
    .post<AgentResult>('/agent/macro', { stock_code: stockCode, stock_name: stockName })
    .then((r) => r.data);

export const runEnhancedAnalysis = (stockCode: string, stockName: string) =>
  api
    .post<EnhancedAnalysis>('/agent/enhanced-analysis', {
      stock_code: stockCode,
      stock_name: stockName,
    })
    .then((r) => r.data);

// 仅查询 DB 缓存，不运行 Agent，缓存不存在则 reject
export const getCachedEnhancedAnalysis = (stockCode: string) =>
  api
    .get<EnhancedAnalysis>(`/agent/enhanced-analysis/cached/${stockCode}`)
    .then((r) => r.data);

// SSE 流式综合分析
export type SSEStage =
  | 'cache_hit'
  | 'upstream_start'
  | 'sentiment_done'
  | 'sector_done'
  | 'macro_done'
  | 'enhanced_start'
  | 'complete';

export interface SSEEvent {
  stage: SSEStage;
  data?: Record<string, unknown>;
}

export function streamEnhancedAnalysis(
  stockCode: string,
  stockName: string,
  onEvent: (evt: SSEEvent) => void,
  onError?: (err: Error) => void,
): AbortController {
  const ctrl = new AbortController();

  fetch('/api/agent/enhanced-analysis-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stock_code: stockCode, stock_name: stockName }),
    signal: ctrl.signal,
  })
    .then(async (resp) => {
      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // SSE 事件以双换行分隔
        const parts = buf.split('\n\n');
        buf = parts.pop() || '';
        for (const part of parts) {
          if (!part.trim()) continue;
          // 提取 data: 行
          const dataLine = part
            .split('\n')
            .find((l) => l.startsWith('data: '));
          if (!dataLine) continue;
          try {
            const parsed = JSON.parse(dataLine.slice(6)) as SSEEvent;
            onEvent(parsed);
          } catch {
            // 解析失败忽略
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError?.(err instanceof Error ? err : new Error(String(err)));
      }
    });

  return ctrl;
}

export const getLLMStatus = () =>
  api.get<LLMStatus>('/agent/llm-status').then((r) => r.data);

export const reloadLLMConfig = () =>
  api.post<LLMStatus>('/agent/reload-config').then((r) => r.data);

export const clearAgentCache = (stockCode: string) =>
  api.delete(`/agent/cache/${stockCode}`).then((r) => r.data);

// --- 问财 API 状态 ---
export interface IwencaiStatus {
  available: boolean;
  reason: string;
}

export const getIwencaiStatus = () =>
  api.get<IwencaiStatus>('/agent/iwencai-status').then((r) => r.data);

export const resetIwencaiCircuit = () =>
  api.post<IwencaiStatus>('/agent/iwencai-reset').then((r) => r.data);

// --- 对比基准 ---
export interface BenchmarkSeries {
  code: string;
  name: string;
  close: number[];
  pct_change: number[];
}

export interface BenchmarkData {
  dates: string[];
  stock: { name: string; close: number[]; pct_change: number[] };
  benchmarks: BenchmarkSeries[];
  stats: {
    stock_return: number;
    hs300_return: number;
    sh_return: number;
    excess_hs300: number;
    excess_sh: number;
  };
}

export const getBenchmark = (stockCode: string, period = 'daily', days = 120) =>
  api
    .get<BenchmarkData>(`/stocks/${stockCode}/benchmark`, {
      params: { period, days },
    })
    .then((r) => r.data);

// --- Data Source ---
export interface DataSourceResponse {
  source_type: string;
  stock_code: string;
  data: Record<string, unknown>;
  timestamp: string;
  from_cache: boolean;
}

export const getDataSource = (stockCode: string, sourceType: string, stockName: string) =>
  api
    .get<DataSourceResponse>(`/data-source/${stockCode}/${sourceType}`, {
      params: { stock_name: stockName },
    })
    .then((r) => r.data);

export const refreshDataSource = (stockCode: string, sourceType: string, stockName: string) =>
  api
    .post<DataSourceResponse>(`/data-source/${stockCode}/${sourceType}/refresh`, null, {
      params: { stock_name: stockName },
    })
    .then((r) => r.data);

// --- Snapshots ---
export const getSnapshotDates = (agentType: string, stockCode: string) =>
  api
    .get<string[]>(`/snapshots/${agentType}/dates`, { params: { stock_code: stockCode } })
    .then((r) => r.data);

export const getSnapshotDetail = (agentType: string, date: string, stockCode: string) =>
  api
    .get<AgentSnapshot>(`/snapshots/${agentType}/${date}`, { params: { stock_code: stockCode } })
    .then((r) => r.data);
