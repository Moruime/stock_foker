# 2026-04-15 Agent 性能优化与体验升级 - 迭代记录

## 开发概述

Sentiment/Sector Agent 数据源并行化改造与熔断降级；
新增对比基准分析、SSE 流式推送；
北向资金数据源替换为 AKShare + Macro Agent 缓存体系改造。

## 新增功能

| 功能 | 说明 |
| --- | --- |
| 数据源并行获取 | `parallel_get_data_sources()` 多线程并行获取，每线程独立 DB Session |
| 问财 API 熔断 | 首次 403 后触发全局熔断，后续调用瞬间返回空数据（0s），避免无谓等待 |
| 历史缓存回退 | API 返回空数据时自动回退到最近一次有效缓存，跳过空数据行（最多扫描 5 条） |
| `stock_news` 缓存注册 | 原非缓存的 `fetch_stock_news` 纳入缓存体系，减少重复调用 |
| `events_data` 去重 | Sentiment Agent 中 `events_data` 不再重复调用，复用缓存 `hithink_events` |
| 对比基准分析 | 个股 vs 沪深300/上证指数归一化涨跌幅走势对比，含超额收益统计 |
| 基准时间维度切换 | 近一月/近三月/近半年/近一年四档切换 |
| SSE 流式分析 | AI 综合分析改为 SSE 逐步推送，实时显示 Agent 执行进度 |
| 北向资金 AKShare 替代 | `fetch_north_flow()` 改用 AKShare 东方财富汇总接口，修复数据语义偏差 |
| Macro Agent 缓存体系 | 4 个全局数据源统一走 `parallel_get_data_sources` 缓存 |

## 问题修复

| 问题 | 原因 | 解决方案 |
| --- | --- | --- |
| Sentiment Agent 耗时 44s | 8 个数据源串行调用（2 个 parallel_fetch + 6 个串行 get_data_source） | 统一为 8 个数据源全部走 `parallel_get_data_sources` 并行获取 |
| Sector Agent 缓存源串行 | 4 个 `get_data_source` 串行调用 | 改为 `parallel_get_data_sources` 并行 |
| 问财 403 导致全部超时 | API 额度耗尽返回 403，8 个并行线程各等 12s 超时 | 首次 403 触发熔断，后续调用直接跳过 |
| 北向资金数据语义错误 | 问财 API 查询"北向资金"返回的实际是主力资金流向数据 | 替换为 AKShare `stock_hsgt_fund_flow_summary_em` 东方财富汇总接口 |
| Macro Agent 未走缓存 | 4 个全局数据源直接调用 `parallel_fetch`，每次请求都消耗问财额度 | 改为 `parallel_get_data_sources` 统一走缓存体系 |
| Macro prompt 北向资金标注错误 | 提示词写"北向资金净买入Top10"但实际是主力资金 | 修正为"沪深港通资金流向汇总" |

## 工程改进

- `data_source_service.py` 新增三级降级策略：
  当日缓存 → API 调用 → 历史缓存回退
- `data_fetcher.py` 新增熔断机制：
  `_check_iwencai_403()` / `get_iwencai_status()` /
  `reset_iwencai_circuit()`
- `_is_empty_data()` 统一判断空数据：
  覆盖 `{}`、`{"datas": []}`、`{"data": []}` 三种格式
- Sentiment Agent 原 `news_data` + `events_data`
  非缓存双路调用合并为缓存体系内统一管理

## 性能对比

| Agent | 优化前（无缓存） | 优化后（无缓存） | 提升 |
| --- | --- | --- | --- |
| Sentiment | 44.0s | 20.9s | -53% |
| Sector | 9.8s | 11.7s | 持平（403 干扰） |
| Macro | 8.9s | 缓存命中时 <1s | 已纳入缓存体系 |

## 关键文件变更

### 新增文件

| 文件 | 说明 |
| --- | --- |
| 无 | - |

### 修改文件

| 文件 | 变更说明 |
| --- | --- |
| `backend/app/services/data_source_service.py` | 注册 `stock_news`；新增 `parallel_get_data_sources`、`_get_latest_history_cache`、`_is_empty_data`；三级降级策略 |
| `backend/app/services/data_fetcher.py` | 熔断机制；`fetch_north_flow` 改用 AKShare 东方财富汇总接口 |
| `backend/app/agents/macro_agent.py` | 4 个数据源统一走 `parallel_get_data_sources` 缓存体系 |
| `backend/app/llm/prompts.py` | 宏观 prompt 北向资金标注修正为沪深港通资金流向汇总 |
| `backend/app/agents/sentiment_agent.py` | 8 个数据源统一并行获取，去除 `parallel_fetch` + 串行双路调用 |
| `backend/app/agents/sector_agent.py` | 4 个缓存数据源改为 `parallel_get_data_sources` 并行 |
| `backend/app/services/stock_service.py` | 新增 `_BENCHMARKS` 常量和 `get_benchmark_comparison()` 函数 |
| `backend/app/routers/stock_router.py` | 新增 `GET /api/stocks/{stock_code}/benchmark` 端点 |
| `backend/app/routers/agent_router.py` | 新增 SSE 端点 `POST /enhanced-analysis-stream`，含 `_sse_event`、`_enhanced_analysis_generator` |
| `frontend/src/services/api.ts` | 新增 `BenchmarkData` 类型、`getBenchmark()`；新增 `SSEEvent` 类型、`streamEnhancedAnalysis()` |
| `frontend/src/pages/AnalysisPage.tsx` | 新增对比基准卡片（ECharts 折线图 + 统计指标 + 时间切换）；AI 分析改为 SSE 流式 UI |
