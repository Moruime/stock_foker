# 2026-04-06 Phase 2 Agent 链路实现

## 1 开发概述

完成产品设计文档第二阶段核心功能：LLM Agent 链路全栈实现，包括消息面情绪分析、板块联动分析、宏观环境感知、增强版综合建议四个 Agent，以及对应的前端页面和 AI 设置页。

## 2 新增功能

### 2.1 后端 Agent 链路

| 模块 | 说明 |
| ------ | ------ |
| LLM 抽象层 | OpenAI 兼容 Chat Completions API 客户端（httpx），支持 DeepSeek/通义千问/Moonshot/GLM 等 |
| LLM 配置 | .env 文件管理，支持运行时热重载，无需重启后端 |
| Agent 基类 | 模板方法模式：fetch_data → build_prompt → call_llm → parse_response + fallback 降级 |
| SentimentAgent | AKShare `stock_news_em` 抓取新闻 → LLM 情绪分析 → 情绪评分/关键新闻/噪音比 |
| SectorAgent | AKShare 行业板块/概念板块/成分股 → LLM 板块联动分析 → 板块趋势/相对强度/同行排名 |
| MacroAgent | 上证指数/北向资金/市场涨跌 → LLM 宏观分析 → 市场阶段/风险等级/关键指标 |
| EnhancedAdviceAgent | 上游 3 Agent 结果 + 技术指标 + 画像 + 持仓 → 四维度综合建议 |
| 数据抓取层 | `data_fetcher.py` 封装 AKShare 接口调用 |
| API 路由 | 7 个端点：sentiment/sector/macro/enhanced-analysis/llm-status/reload-config/cache |
| 结果缓存 | `agent_result_cache` 表，当日有效，LLM 可用时自动跳过降级缓存 |

### 2.2 前端页面

| 页面 | 说明 |
| ------ | ------ |
| SentimentPage | 消息面情绪分析：情绪评分、关键新闻列表、噪音比 |
| SectorPage | 板块联动：行业/概念板块数据、成分股排名表格（含股票代码） |
| MacroPage | 宏观环境：市场阶段、情绪指数、风险等级、关键指标 |
| SettingsPage | AI 设置：LLM 配置状态展示、重新加载配置按钮、Thinking 模式状态 |
| AnalysisPage 增强 | 新增 AI 综合分析区域：四维度雷达图、信号/置信度/推理过程/风险/仓位建议 |

### 2.3 前端基础设施

- TypeScript 类型：AgentResult、EnhancedAnalysis、LLMStatus
- API 封装：7 个函数（runSentimentAgent、runSectorAgent、runMacroAgent、runEnhancedAnalysis、getLLMStatus、reloadLLMConfig、clearAgentCache）
- 路由：新增 /sentiment、/sector、/macro、/settings 四条路由
- 侧边栏：新增消息面、板块联动、宏观环境、AI 设置四个菜单项

## 3 问题修复

| 问题 | 原因 | 解决方案 |
| ------ | ------ | ------ |
| 配置 .env 后 AI 仍显示不可用 | LLMClient 模块级单例在启动时创建，后续 .env 变更无效 | 新增 `reload_llm_client()` + POST /reload-config 热重载端点 |
| LLM 可用后仍返回降级结果 | Agent 缓存命中旧的 degraded 结果 | `_get_cached()` 检测 LLM 可用时跳过降级缓存 |
| Qwen3 thinking 模式超时 | qwen3.6-plus 默认开启思考链，生成长推理导致 60s 超时 | 新增 `LLM_ENABLE_THINKING` 配置，关闭后响应 ~8s |
| 板块成分股缺少股票代码 | Prompt 模板未要求 code 字段 | 修复 prompt + parse_response 从 AKShare 数据回填 |
| AI 设置页未显示 thinking 状态 | enable_thinking 字段未加入后端响应和前端类型 | 补充后端 status/schema + 前端 type/display |
| 北向资金接口报错 | AKShare 函数更名 | `stock_hsgt_north_net_flow_in_em` → `stock_hsgt_hist_em` |

## 4 工程改进

- 更新 3 个文档：技术架构文档（项目结构/数据库/API/数据流/LLM 配置）、MVP 实现说明（功能状态/未实现列表）、产品设计文档（配置表/API 端点）
- 日志输出从 `.pids/` 迁移到 `logs/` 目录
- `.gitignore` 新增 `logs/` 规则

## 5 关键文件变更

### 5.1 新增文件

| 文件 | 说明 |
| ------ | ------ |
| `backend/app/llm/config.py` | LLM 配置加载 |
| `backend/app/llm/client.py` | LLM 客户端 |
| `backend/app/llm/prompts.py` | Agent Prompt 模板 |
| `backend/app/agents/base_agent.py` | Agent 基类 |
| `backend/app/agents/sentiment_agent.py` | 消息面 Agent |
| `backend/app/agents/sector_agent.py` | 板块联动 Agent |
| `backend/app/agents/macro_agent.py` | 宏观环境 Agent |
| `backend/app/agents/enhanced_advice_agent.py` | 增强建议 Agent |
| `backend/app/services/data_fetcher.py` | 数据抓取服务 |
| `backend/app/routers/agent_router.py` | Agent API 路由 |
| `backend/.env.example` | LLM 配置模板 |
| `frontend/src/pages/SentimentPage.tsx` | 消息面页面 |
| `frontend/src/pages/SectorPage.tsx` | 板块联动页面 |
| `frontend/src/pages/MacroPage.tsx` | 宏观环境页面 |
| `frontend/src/pages/SettingsPage.tsx` | AI 设置页面 |

### 5.2 修改文件

| 文件 | 变更 |
| ------ | ------ |
| `backend/app/models/models.py` | 新增 AgentResultCache 模型 |
| `backend/app/models/schemas.py` | 新增 Agent 相关 Schema |
| `backend/app/main.py` | 注册 agent_router |
| `frontend/src/types/index.ts` | 新增 Agent 相关类型 |
| `frontend/src/services/api.ts` | 新增 7 个 API 函数 |
| `frontend/src/App.tsx` | 新增 4 条路由 |
| `frontend/src/components/MainLayout.tsx` | 新增 4 个菜单项 |
| `frontend/src/pages/AnalysisPage.tsx` | 新增 AI 综合分析区域 |
| `start.sh` | 日志路径迁移到 logs/ |
| `doc/*.md` | 3 个文档全面更新 |
