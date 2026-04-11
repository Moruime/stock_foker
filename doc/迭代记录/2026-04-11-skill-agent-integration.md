# 2026-04-11 Skill 全量接入与架构审查修复

## 1 开发概述

将 13 个同花顺 SkillHub 技能全量接入 4 大 Agent，
实现 AI 分析从「纯大盘行情」升级至
「宏观指标 + 基本面 + 结构化事件 + 行业估值」
多维分析体系；同时完成第一期架构审查，
修复 P0/P1/P2 共 15 项隐患。

## 2 新增功能

### 2.1 同花顺 API 通用客户端

| 功能 | 说明 |
| --- | --- |
| `_call_hithink_api()` | 问财 OpenAPI 统一封装 |
| `_call_hithink_search_api()` | 综合搜索接口封装 |
| `parallel_fetch()` | 通用并行调度，最多 8 线程 |

### 2.2 MacroAgent 数据增强

| 数据源 | 说明 |
| --- | --- |
| hithink-macro-query | CPI/PPI/PMI/LPR/M2 |
| hithink-zhishu-query | 上证/沪深300/创业板指行情 |

### 2.3 SentimentAgent 数据增强

| 数据源 | 说明 |
| --- | --- |
| hithink-event-query | 业绩预告/解禁/减持/增持事件 |
| news-search | 财经资讯搜索 |
| announcement-search | 公告搜索 |

### 2.4 SectorAgent 数据增强

| 数据源 | 说明 |
| --- | --- |
| hithink-industry-query | 行业 PE/PB/ROE/排名 |
| hithink-market-query | 主力资金净流入/大单/换手率 |

### 2.5 EnhancedAdviceAgent 数据增强

| 数据源 | 说明 |
| --- | --- |
| hithink-finance-query | ROE/净利润增速/毛利率/PE |
| hithink-insresearch-query | 机构评级与目标价 |
| report-search | 研报搜索 |
| hithink-business-query | 主营构成/客户/供应商 |
| hithink-basicinfo-query | 行业分类/上市日期/市值 |
| hithink-management-query | 股东户数/前十大/实控人 |

### 2.6 前端五维雷达图

| 功能 | 说明 |
| --- | --- |
| AnalysisPage 雷达图 | 4 维升级为 5 维，新增「基本面」 |
| SnapshotPanel | 新增 fundamental 维度标签 |

### 2.7 API 并行化优化

| Agent | 说明 |
| --- | --- |
| SentimentAgent | 4 fetch 并行（~48s → ~12s） |
| SectorAgent | 4 fetch 并行 |
| MacroAgent | 5 fetch 并行 |
| EnhancedAdviceAgent | 6 fetch 并行 |

## 3 架构审查与修复

详见 `doc/代码审查/` 目录下审查报告与修复报告。

### 3.1 P0 修复（2 项）

| 问题 | 修复 |
| --- | --- |
| SQLite Session 跨线程共享 | 子线程创建独立 SessionLocal |
| SectorAgent 降级签名缺参 | 补传 stock_name |

### 3.2 P1 修复（7 项）

| 问题 | 修复 |
| --- | --- |
| LLM 重试无退避 | 指数退避 2^attempt |
| 数据源缓存双重查询 | 返回 (data, ts) 元组 |
| 快照校验消息写死 | 动态拼接 VALID_AGENT_TYPES |
| 删除交易未回滚持仓 | realtime 记录反向调整 |
| K 线更新遗漏 turnover | 补充 turnover 字段 |
| 前端缓存无上限 | 数量淘汰机制 |
| FocusStock 竞态 | flush 后再 insert |

### 3.3 P2 修复（6 项）

| 问题 | 修复 |
| --- | --- |
| 缺少数据库索引 | 3 列添加 index=True |
| on_event 已弃用 | 迁移到 lifespan |
| 列表缓存无过期 | 4 小时 TTL |
| WAL 模式未启用 | PRAGMA journal_mode=WAL |
| CORS 硬编码 | 环境变量 CORS_ORIGINS |
| K 线缓存无清理 | 删除 400 天前旧数据 |

## 4 关键文件变更

### 4.1 新增文件

| 文件 | 说明 |
| --- | --- |
| `doc/代码审查/2026-04-11-phase1-architecture-review.md` | 审查报告 |
| `doc/代码审查/2026-04-11-phase1-fix-report.md` | 修复报告 |

### 4.2 修改文件

| 文件 | 变更 |
| --- | --- |
| `backend/app/services/data_fetcher.py` | 同花顺客户端 + parallel_fetch + 14 fetch |
| `backend/app/agents/macro_agent.py` | 接入宏观指标 + 指数行情 |
| `backend/app/agents/sentiment_agent.py` | 接入事件 + 资讯 + 公告 |
| `backend/app/agents/sector_agent.py` | 接入行业估值 + 资金流向 + 签名修复 |
| `backend/app/agents/enhanced_advice_agent.py` | 接入财务/评级/研报/经营/基本资料/股东 |
| `backend/app/llm/prompts.py` | 4 个 Agent Prompt 模板升级 |
| `backend/app/routers/agent_router.py` | Session 跨线程修复 |
| `backend/app/routers/stock_router.py` | 交易回滚 + FocusStock 竞态 |
| `backend/app/routers/snapshot_router.py` | 校验消息动态化 |
| `backend/app/services/data_source_service.py` | 缓存双查询优化 |
| `backend/app/services/stock_service.py` | turnover + TTL + K 线清理 |
| `backend/app/llm/client.py` | 重试退避 |
| `backend/app/models/models.py` | 数据库索引 |
| `backend/app/db/database.py` | WAL 模式 |
| `backend/app/main.py` | lifespan + CORS 环境变量 |
| `frontend/src/pages/AnalysisPage.tsx` | 五维雷达图 |
| `frontend/src/components/SnapshotPanel.tsx` | fundamental 标签 |
| `frontend/src/contexts/AgentCacheContext.tsx` | 缓存淘汰 |
| `frontend/src/hooks/useDataSource.ts` | 缓存淘汰 |
