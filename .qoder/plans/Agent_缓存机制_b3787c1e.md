# Agent 缓存机制

## 现状分析

| 层 | 现状 | 问题 |
|---|---|---|
| 后端 | `sentiment`/`sector`/`macro` 有按天缓存 (`AgentResultCache`) | `enhanced-analysis` 未检查自身 `enhanced_advice` 缓存，每次都重新调用 LLM |
| 前端 | 页面组件在 `useEffect` 里直接调接口 | 每次导航都触发 API 请求 + loading，结果不跨页保留 |

---

## Task 1: 后端 - 修复 `enhanced-analysis` 缓存检查

**文件**: `backend/app/routers/agent_router.py`

在 `run_enhanced_analysis` 函数开头添加对 `enhanced_advice` 自身的缓存检查：

```python
# 先检查 enhanced_advice 整体缓存
cached_enhanced = _get_cached(db, "enhanced_advice", stock_code)
if cached_enhanced:
    # 同时尝试读取三个上游缓存拼装完整响应
    s = _get_cached(db, "sentiment", stock_code) or {...}
    ...
    return { "sentiment": s, "sector": ..., "macro": ..., "enhanced_advice": cached_enhanced }
```

---

## Task 2: 前端 - 创建 `AgentCacheContext`

**新建文件**: `frontend/src/contexts/AgentCacheContext.tsx`

设计要点：
- 使用 `useRef` 存储 `Map<string, { data, cachedAt: string }>`，避免无谓 re-render
- Cache key 格式：`${stockCode}:${agentType}`（例如 `600036:sentiment`）
- 有效期判断：`cachedAt` 日期部分与当前日期相同（与后端逻辑对齐）
- 暴露 `getAgentCache(stockCode, agentType)` / `setAgentCache(...)` / `invalidateStock(stockCode)` 三个方法

---

## Task 3: 更新 `App.tsx`

用 `AgentCacheProvider` 包裹整个 Router，使缓存跨页面存活。

---

## Task 4-6: 更新三个单独 Agent 页面

涉及文件：`SentimentPage.tsx` / `SectorPage.tsx` / `MacroPage.tsx`

统一改造模式：
1. 从 Context 中取 `getAgentCache` / `setAgentCache`
2. `useEffect` 中先查缓存 → 有则直接 `setResult(cached)` 无则调 API
3. 手动"刷新"按钮：先调后端 `DELETE /api/agent/cache/{stockCode}` 清除 DB 缓存，同时清除前端 Context 缓存，再重新 fetch
4. 在页面头部显示缓存时间戳（格式：`缓存于 HH:mm`），让用户感知数据新鲜度

---

## Task 7: 更新 `AnalysisPage` 的 AI 综合分析

- 组件 mount 时检查缓存：若有今日有效的 `enhanced_advice` 缓存，自动展示（无需点按钮）
- 成功获取后写入缓存
- 按钮逻辑：无缓存时显示"开始分析"（primary），有缓存时显示"刷新"（default）
- 刷新时先清除前端 + 后端缓存，再重新分析

---

## 缓存失效策略

| 场景 | 处理方式 |
|---|---|
| 自然过期 | 按天：当日 0 点后缓存失效，下次访问重新 fetch |
| 切换股票 | key 含 `stockCode`，自动命中/不命中各自缓存 |
| 手动刷新 | 调用 `DELETE /api/agent/cache/{stockCode}` + 清除前端 Context |
| 应用刷新 | 前端内存缓存清空（但后端 DB 缓存仍有效，首次 fetch 也很快） |

