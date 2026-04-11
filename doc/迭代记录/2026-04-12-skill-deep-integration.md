# 2026-04-12 同花顺 Skill 深度集成（9 Skills 全量接入）

## 1 开发概述

将剩余 9 个未使用的同花顺 Skills 全量接入 4 大 Agent，同时实现 API 并行化优化。
本次覆盖行业估值、新闻搜索、公告搜索、指数行情、资金流向、研报搜索、公司经营、基本资料、股东股本等数据维度。

## 2 新增功能

### 2.1 综合搜索客户端

| 功能 | 说明 |
| --- | --- |
| `_call_hithink_search_api()` | 封装 `/v1/comprehensive/search` 接口，支持 news/announcement/report 三种 channel |

### 2.2 SectorAgent 数据增强

| Skill | 函数 | 说明 |
| --- | --- | --- |
| hithink-industry-query | `fetch_hithink_industry_data()` | 行业 PE/PB/ROE/排名 |
| hithink-market-query | `fetch_hithink_market_data()` | 主力资金净流入/大单净量/换手率/量比 |

### 2.3 SentimentAgent 数据增强

| Skill | 函数 | 说明 |
| --- | --- | --- |
| news-search | `fetch_hithink_news()` | 财经资讯搜索（comprehensive/search） |
| announcement-search | `fetch_hithink_announcements()` | 公告搜索（comprehensive/search） |

### 2.4 MacroAgent 数据增强

| Skill | 函数 | 说明 |
| --- | --- | --- |
| hithink-zhishu-query | `fetch_hithink_index_data()` | 上证/沪深300/创业板指最新行情 |

### 2.5 EnhancedAdviceAgent 数据增强

| Skill | 函数 | 说明 |
| --- | --- | --- |
| report-search | `fetch_hithink_reports()` | 研报搜索（comprehensive/search） |
| hithink-business-query | `fetch_hithink_business_data()` | 主营构成/客户/供应商 |
| hithink-basicinfo-query | `fetch_hithink_basicinfo()` | 行业分类/上市日期/股本/市值 |
| hithink-management-query | `fetch_hithink_shareholders()` | 股东户数/前十大股东/实控人 |

### 2.6 API 并行化优化

| 功能 | 说明 |
| --- | --- |
| `parallel_fetch()` | 通用并行调度工具，基于 `ThreadPoolExecutor`，最多 8 线程 |
| SentimentAgent | 4 个 fetch 并行（原串行 ~48s → ~12s） |
| SectorAgent | 4 个 fetch 并行 |
| MacroAgent | 5 个 fetch 并行 |
| EnhancedAdviceAgent | 6 个 fetch 并行 |

### 2.7 Prompt 模板升级

| Agent | 新增段落 |
| --- | --- |
| sector_prompt | 行业估值数据 + 主力资金流向数据 |
| sentiment_prompt | 财经资讯搜索结果 + 最新公告信息（各截取前 10 条） |
| macro_prompt | 主要指数实时行情 |
| enhanced_advice_prompt | 九～十二：研报 + 经营数据 + 基本资料 + 股东股本（研报截取前 5 条） |

## 3 关键文件变更

| 文件 | 变更 |
| --- | --- |
| `backend/app/services/data_fetcher.py` | 新增 `_call_hithink_search_api` + `parallel_fetch` + 10 个 fetch 函数 |
| `backend/app/agents/sentiment_agent.py` | 接入 news/announcements + parallel_fetch |
| `backend/app/agents/sector_agent.py` | 接入 industry_valuation/market_data + parallel_fetch |
| `backend/app/agents/macro_agent.py` | 接入 hithink_index + parallel_fetch |
| `backend/app/agents/enhanced_advice_agent.py` | 接入 reports/business/basicinfo/shareholders + parallel_fetch |
| `backend/app/llm/prompts.py` | 更新 4 个 Agent 的 Prompt 模板，新增数据段落 |

## 4 Skill 使用状态

| 状态 | Skill |
| --- | --- |
| ✅ 已接入 | hithink-macro-query, hithink-finance-query, hithink-insresearch-query, hithink-event-query |
| ✅ 本次接入 | hithink-industry-query, news-search, announcement-search, hithink-zhishu-query, hithink-market-query, report-search, hithink-business-query, hithink-basicinfo-query, hithink-management-query |
| 🎯 全量 | 13/13 Skills 已接入 |
