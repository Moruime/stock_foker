/**
 * useDataSource — 独立数据源获取 hook
 *
 * 每个数据面板通过此 hook 独立管理自身的加载/缓存/刷新状态。
 * 内部维护模块级 Map 作为轻量内存缓存（跨组件共享、不触发 re-render）。
 * 缓存新鲜度边界与 Agent 一致：每天 09:00。
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getDataSource, refreshDataSource } from '../services/api';

// ------------------------------------------------------------------ types

export interface DataSourceResult {
  data: Record<string, unknown> | null;
  loading: boolean;
  error: string;
  timestamp: string;
  fromCache: boolean;
  refresh: () => void;
}

// ------------------------------------------------------------------ 模块级内存缓存

interface CacheEntry {
  data: Record<string, unknown>;
  timestamp: string;
  cachedAt: number; // Date.now()
}

const _memCache = new Map<string, CacheEntry>();

function _cacheKey(stockCode: string, sourceType: string): string {
  return `${stockCode}:ds:${sourceType}`;
}

function _last9amMs(): number {
  const now = new Date();
  const boundary = new Date(now);
  boundary.setHours(9, 0, 0, 0);
  if (now < boundary) boundary.setDate(boundary.getDate() - 1);
  return boundary.getTime();
}

function _getMemCache(stockCode: string, sourceType: string): CacheEntry | null {
  const entry = _memCache.get(_cacheKey(stockCode, sourceType));
  if (!entry) return null;
  if (entry.cachedAt < _last9amMs()) return null; // 过期
  return entry;
}

function _setMemCache(stockCode: string, sourceType: string, data: Record<string, unknown>, timestamp: string): void {
  _memCache.set(_cacheKey(stockCode, sourceType), {
    data,
    timestamp,
    cachedAt: Date.now(),
  });
}

/** 清除指定股票的所有数据源内存缓存 */
export function invalidateDataSourceCache(stockCode: string): void {
  for (const key of Array.from(_memCache.keys())) {
    if (key.startsWith(`${stockCode}:ds:`)) {
      _memCache.delete(key);
    }
  }
}

// ------------------------------------------------------------------ hook

export function useDataSource(
  stockCode: string | undefined,
  stockName: string | undefined,
  sourceType: string,
): DataSourceResult {
  const [data, setData] = useState<Record<string, unknown> | null>(() => {
    if (!stockCode) return null;
    return _getMemCache(stockCode, sourceType)?.data ?? null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [timestamp, setTimestamp] = useState(() => {
    if (!stockCode) return '';
    return _getMemCache(stockCode, sourceType)?.timestamp ?? '';
  });
  const [fromCache, setFromCache] = useState(() => {
    if (!stockCode) return false;
    return _getMemCache(stockCode, sourceType) !== null;
  });

  // 避免 stale closure
  const stockCodeRef = useRef(stockCode);
  const stockNameRef = useRef(stockName);
  stockCodeRef.current = stockCode;
  stockNameRef.current = stockName;

  const fetchData = useCallback(async (forceRefresh = false) => {
    const code = stockCodeRef.current;
    const name = stockNameRef.current;
    if (!code) return;

    // 内存缓存命中
    if (!forceRefresh) {
      const cached = _getMemCache(code, sourceType);
      if (cached) {
        setData(cached.data);
        setTimestamp(cached.timestamp);
        setFromCache(true);
        return;
      }
    }

    setLoading(true);
    setError('');
    try {
      const resp = forceRefresh
        ? await refreshDataSource(code, sourceType, name || '')
        : await getDataSource(code, sourceType, name || '');
      setData(resp.data);
      setTimestamp(resp.timestamp);
      setFromCache(resp.from_cache);
      _setMemCache(code, sourceType, resp.data, resp.timestamp);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '获取数据失败');
    } finally {
      setLoading(false);
    }
  }, [sourceType]);

  const refresh = useCallback(() => {
    fetchData(true);
  }, [fetchData]);

  useEffect(() => {
    if (!stockCode) {
      setData(null);
      setTimestamp('');
      setFromCache(false);
      return;
    }
    // 同步检查内存缓存（避免闪烁）
    const cached = _getMemCache(stockCode, sourceType);
    if (cached) {
      setData(cached.data);
      setTimestamp(cached.timestamp);
      setFromCache(true);
    } else {
      // 重置状态后异步获取
      setData(null);
      setTimestamp('');
      setFromCache(false);
      fetchData();
    }
  }, [stockCode, sourceType, fetchData]);

  return { data, loading, error, timestamp, fromCache, refresh };
}
