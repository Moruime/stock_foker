/**
 * AgentCacheContext
 *
 * 前端内存缓存层，避免页面切换时重复调用 Agent 接口。
 * - Cache key: `${stockCode}:${agentType}`
 * - 有效期：当天最近一次 09:00 之后（与后端缓存新鲜度边界对齐）
 * - 使用 useRef 存储，不触发组件 re-render
 */

import { createContext, useContext, useRef, useCallback, type ReactNode } from 'react';
import type { AgentResult, EnhancedAnalysis } from '../types';

// ------------------------------------------------------------------ types

export type AgentType = 'sentiment' | 'sector' | 'macro' | 'enhanced_advice';

type CacheValue =
  | { type: 'agent'; data: AgentResult }
  | { type: 'enhanced'; data: EnhancedAnalysis };

interface CacheEntry {
  value: CacheValue;
  /** ISO 字符串，取自 Agent 返回的 timestamp，或写入时的当前时间 */
  cachedAt: string;
}

interface AgentCacheContextValue {
  /** 读取缓存，若不存在或已过期返回 null */
  getAgentCache(stockCode: string, agentType: 'sentiment' | 'sector' | 'macro'): AgentResult | null;
  getEnhancedCache(stockCode: string): EnhancedAnalysis | null;
  /** 写入缓存 */
  setAgentCache(stockCode: string, agentType: 'sentiment' | 'sector' | 'macro', data: AgentResult): void;
  setEnhancedCache(stockCode: string, data: EnhancedAnalysis): void;
  /** 清除指定股票的所有缓存（手动刷新时调用） */
  invalidateStock(stockCode: string): void;
}

// ------------------------------------------------------------------ helpers

/** 返回最近一次 09:00 的本地 Date（缓存新鲜度边界） */
function last9am(): Date {
  const now = new Date();
  const boundary = new Date(now);
  boundary.setHours(9, 0, 0, 0);
  if (now < boundary) boundary.setDate(boundary.getDate() - 1);
  return boundary;
}

function isValidEntry(entry: CacheEntry): boolean {
  // 缓存时间在上一个 09:00 之后才算有效
  return new Date(entry.cachedAt) >= last9am();
}

function cacheKey(stockCode: string, agentType: AgentType): string {
  return `${stockCode}:${agentType}`;
}

/** 最多缓存的股票数量（每只 4 类 Agent） */
const MAX_STOCKS = 20;

/** 当缓存超过上限时，淘汰最早的条目 */
function _evictIfNeeded(store: Map<string, CacheEntry>): void {
  // 每只股票最多 4 个 key，上限 = MAX_STOCKS * 4
  if (store.size <= MAX_STOCKS * 4) return;
  // 按 cachedAt 升序排序，删除最旧的 4 个（即最旧一只股票）
  const entries = [...store.entries()].sort(
    (a, b) => new Date(a[1].cachedAt).getTime() - new Date(b[1].cachedAt).getTime(),
  );
  for (let i = 0; i < 4 && i < entries.length; i++) {
    store.delete(entries[i][0]);
  }
}

// ------------------------------------------------------------------ context

const AgentCacheContext = createContext<AgentCacheContextValue | null>(null);

export function AgentCacheProvider({ children }: { children: ReactNode }) {
  // Map 存在 ref 中，写入不触发 re-render
  const storeRef = useRef<Map<string, CacheEntry>>(new Map());

  const getAgentCache = useCallback(
    (stockCode: string, agentType: 'sentiment' | 'sector' | 'macro'): AgentResult | null => {
      const entry = storeRef.current.get(cacheKey(stockCode, agentType));
      if (!entry || !isValidEntry(entry)) return null;
      if (entry.value.type !== 'agent') return null;
      return entry.value.data;
    },
    [],
  );

  const getEnhancedCache = useCallback((stockCode: string): EnhancedAnalysis | null => {
    const entry = storeRef.current.get(cacheKey(stockCode, 'enhanced_advice'));
    if (!entry || !isValidEntry(entry)) return null;
    if (entry.value.type !== 'enhanced') return null;
    return entry.value.data;
  }, []);

  const setAgentCache = useCallback(
    (stockCode: string, agentType: 'sentiment' | 'sector' | 'macro', data: AgentResult): void => {
      storeRef.current.set(cacheKey(stockCode, agentType), {
        value: { type: 'agent', data },
        cachedAt: data.timestamp || new Date().toISOString(),
      });
      _evictIfNeeded(storeRef.current);
    },
    [],
  );

  const setEnhancedCache = useCallback((stockCode: string, data: EnhancedAnalysis): void => {
    storeRef.current.set(cacheKey(stockCode, 'enhanced_advice'), {
      value: { type: 'enhanced', data },
      cachedAt: data.enhanced_advice?.timestamp || new Date().toISOString(),
    });
    _evictIfNeeded(storeRef.current);
  }, []);

  const invalidateStock = useCallback((stockCode: string): void => {
    const types: AgentType[] = ['sentiment', 'sector', 'macro', 'enhanced_advice'];
    for (const t of types) {
      storeRef.current.delete(cacheKey(stockCode, t));
    }
  }, []);

  return (
    <AgentCacheContext.Provider
      value={{ getAgentCache, getEnhancedCache, setAgentCache, setEnhancedCache, invalidateStock }}
    >
      {children}
    </AgentCacheContext.Provider>
  );
}

export function useAgentCache(): AgentCacheContextValue {
  const ctx = useContext(AgentCacheContext);
  if (!ctx) throw new Error('useAgentCache must be used within AgentCacheProvider');
  return ctx;
}
