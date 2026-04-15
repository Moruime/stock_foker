# 2026-04-15 Agent 性能优化与降级保障 - 迭代记录

## 开发概述

Sentiment/Sector Agent 数据源并行化改造，
实现问财 API 熔断机制与三级缓存降级策略。

## 新增功能

| 功能 | 说明 |
| --- | --- |
| 数据源并行获取 | `parallel_get_data_sources()` 多线程并行获取，每线程独立 DB Session |
| 问财 API 熔断 | 首次 403 后触发全局熔断，后续调用瞬间返回空数据（0s），避免无谓等待 |
| 历史缓存回退 | API 返回空数据时自动回退到最近一次有效缓存，跳过空数据行（最多扫描 5 条） |
| `stock_news` 缓存注册 | 原非缓存的 `fetch_stock_news` 纳入缓存体系，减少重复调用 |
| `events_data` 去重 | Sentiment Agent 中 `events_data` 不再重复调用，复用缓存 `hithink_events` |

## 问题修复

| 问题 | 原因 | 解决方案 |
| --- | --- | --- |
| Sentiment Agent 耗时 44s | 8 个数据源串行调用（2 个 parallel_fetch + 6 个串行 get_data_source） | 统一为 8 个数据源全部走 `parallel_get_data_sources` 并行获取 |
| Sector Agent 缓存源串行 | 4 个 `get_data_source` 串行调用 | 改为 `parallel_get_data_sources` 并行 |
| 问财 403 导致全部超时 | API 额度耗尽返回 403，8 个并行线程各等 12s 超时 | 首次 403 触发熔断，后续调用直接跳过 |
| 空缓存被当作有效命中 | `_get_cached_source` 不检查数据是否为空 | 新鲜缓存命中时增加 `_is_empty_data()` 检查 |

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
| Macro | 8.9s | 未改动 | - |

## 关键文件变更

### 新增文件

| 文件 | 说明 |
| --- | --- |
| 无 | - |

### 修改文件

| 文件 | 变更说明 |
| --- | --- |
| `backend/app/services/data_source_service.py` | 注册 `stock_news`；新增 `parallel_get_data_sources`、`_get_latest_history_cache`、`_is_empty_data`；三级降级策略 |
| `backend/app/services/data_fetcher.py` | 熔断机制（`_check_iwencai_403` / `get_iwencai_status` / `reset_iwencai_circuit`）；两个 API 函数增加熔断检查 |
| `backend/app/agents/sentiment_agent.py` | 8 个数据源统一并行获取，去除 `parallel_fetch` + 串行双路调用 |
| `backend/app/agents/sector_agent.py` | 4 个缓存数据源改为 `parallel_get_data_sources` 并行 |
