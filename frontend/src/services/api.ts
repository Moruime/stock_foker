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
} from '../types';

const api = axios.create({ baseURL: '/api' });

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
) =>
  api
    .get<StockAnalysis>(`/stocks/${stockCode}/analysis`, {
      params: { period, start_date: startDate, end_date: endDate },
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
