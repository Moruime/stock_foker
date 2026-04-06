# Stock Foker 第二阶段 — Agent 链路设计与实现方案

## Context

当前 MVP 的买卖建议基于纯规则引擎（技术指标评分），缺少消息面、板块联动、宏观环境等维度。第二阶段引入 LLM Agent 链路，将多维度数据通过 AI 融合分析，生成更具可解释性的综合建议。同时需要更新产品设计文档以反映这些新设计。

用户要求：LLM 提供商暂不确定，需设计抽象层；API Key 预留占位符由用户后续补充；设计+代码实现一并完成。

## 架构总览

```
前端 (3个新页面 + 增强AnalysisPage + 设置页)
          │ HTTP
后端 agent_router.py
          │
    ┌─────┴─────┐
    │  4 Agents  │
    │ sentiment  │──┐
    │ sector     │──┤ 并行执行
    │ macro      │──┘
    │            │
    │ enhanced   │← 汇总上述3个结果 + 技术指标 + 用户画像
    └─────┬─────┘
          │
    llm/client.py (OpenAI兼容API, httpx)
          │
    .env (LLM_API_KEY / LLM_BASE_URL / LLM_MODEL)
```

## 实施计划

### Step 1: 产品设计文档更新

**文件**: `doc/产品设计文档.md`

在第 5 章版本规划的 5.2 第二阶段后新增 `第7章 Agent 链路设计` 章节，包含:
- Agent 架构总览图
- LLM 抽象层设计说明
- 4 个 Agent 的输入输出定义
- Agent 协作数据流
- 降级策略说明

### Step 2: LLM 抽象层

**新建文件**:
- `backend/.env.example` — LLM 配置模板（LLM_ENABLED, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL 等），预留 key 占位符
- `backend/app/llm/__init__.py`
- `backend/app/llm/config.py` — 用 python-dotenv 从 `.env` 读取配置，封装为 LLMConfig dataclass
- `backend/app/llm/client.py` — LLMClient 类：用 httpx 调用 OpenAI-compatible Chat Completions API；提供 `chat(messages)` 和 `chat_json(messages)` 方法；内置超时/重试/降级
- `backend/app/llm/prompts.py` — 4 个 Agent 的 Prompt 模板函数，每个返回 messages 列表，要求 LLM 输出结构化 JSON

**无新依赖**: httpx 和 python-dotenv 均已在 requirements.txt 中。

### Step 3: Agent 基类与 4 个 Agent

**新建文件**:
- `backend/app/agents/__init__.py`
- `backend/app/agents/base_agent.py` — 抽象基类，Template Method 模式:
  ```
  execute() → fetch_data() → build_prompt() → call_llm() → parse_response()
                                                         ↘ fallback() (LLM不可用时)
  ```
  统一返回 AgentResult(agent_name, status, data, llm_used, timestamp)

- `backend/app/agents/sentiment_agent.py` — 消息面情绪分析
  - fetch: AKShare `stock_news_em(symbol)` 获取个股新闻
  - LLM输出: overall_sentiment(-1~1), sentiment_label, key_news[], analysis
  - fallback: 返回原始新闻列表，情绪=0

- `backend/app/agents/sector_agent.py` — 板块联动分析
  - fetch: AKShare 行业板块(`stock_board_industry_name_em`)、板块成分股、概念板块
  - LLM输出: sector_name, sector_trend, relative_strength, rotation_signal, analysis
  - fallback: 返回板块原始数据

- `backend/app/agents/macro_agent.py` — 宏观环境感知
  - fetch: 上证指数走势、北向资金(`stock_hsgt_north_net_flow_in_em`)、市场涨跌概况
  - LLM输出: market_phase(牛/熊/震荡), market_sentiment, risk_level, analysis
  - fallback: 返回原始指标数据

- `backend/app/agents/enhanced_advice_agent.py` — 增强版买卖建议（链路终结点）
  - fetch: 调用现有 advice_service + profile_service + 持仓数据 + 上游3个Agent结果
  - LLM输出: signal, confidence, reasoning[], dimension_scores{technical,sentiment,sector,macro}, risk_warnings[], position_advice, summary
  - fallback: 返回现有 advice_service 的纯规则结果

### Step 4: 数据获取服务

**新建文件**:
- `backend/app/services/data_fetcher.py` — 封装所有新数据源:
  - `fetch_stock_news(stock_code)` — 个股新闻
  - `fetch_industry_board(stock_code)` — 所属行业板块
  - `fetch_concept_boards(stock_code)` — 概念板块
  - `fetch_index_data()` — 大盘指数
  - `fetch_north_flow()` — 北向资金
  - `fetch_market_overview()` — 市场涨跌概况
  - 每个函数独立 try-except，失败返回 None 不阻断流程

### Step 5: 数据模型与 API Schema

**修改文件**:
- `backend/app/models/models.py` — 新增 AgentResultCache 模型（agent_name, stock_code, result_json, status, llm_used, created_at）
- `backend/app/models/schemas.py` — 新增 AgentResultResponse, SentimentAnalysis, SectorAnalysis, MacroAnalysis, EnhancedAdvice 等 Pydantic Schema

### Step 6: API 路由

**新建文件**:
- `backend/app/routers/agent_router.py`:
  - `GET /api/agents/sentiment/{stock_code}` — 消息面分析
  - `GET /api/agents/sector/{stock_code}` — 板块联动分析
  - `GET /api/agents/macro` — 宏观环境分析（可选 stock_code 参数）
  - `GET /api/agents/enhanced-advice/{stock_code}` — 增强版综合建议（触发全链路，前3个Agent并行，enhanced串行汇总）
  - `GET /api/agents/status` — Agent系统状态（LLM是否可用）

**修改文件**:
- `backend/app/main.py` — 注册 agent_router，启动时加载 .env

### Step 7: 前端类型和 API

**修改文件**:
- `frontend/src/types/index.ts` — 新增 AgentResult, SentimentAnalysis, SectorAnalysis, MacroAnalysis, EnhancedAdvice 等 TypeScript 接口
- `frontend/src/services/api.ts` — 新增 6 个 API 函数

### Step 8: 前端新页面

**新建文件**:
- `frontend/src/pages/SentimentPage.tsx` — 消息面分析页（情绪仪表盘 + 新闻时间线 + AI分析总结）
- `frontend/src/pages/SectorPage.tsx` — 板块联动页（板块排名 + 个股相对强弱 + 概念板块 + AI分析）
- `frontend/src/pages/MacroPage.tsx` — 宏观环境页（大盘走势 + 宏观指标卡片 + 市场阶段标签 + AI分析）
- `frontend/src/pages/SettingsPage.tsx` — 设置页（LLM配置表单 + 连接测试）

**修改文件**:
- `frontend/src/components/MainLayout.tsx` — 侧边栏新增菜单分组（分析/记录/系统）
- `frontend/src/App.tsx` — 新增4个路由
- `frontend/src/pages/AnalysisPage.tsx` — 增强：增加四维雷达图(ECharts radar) + AI综合建议展示区

### Step 9: 更新产品设计文档详细内容

回到 `doc/产品设计文档.md`，将上述所有设计结果整理为正式文档内容。

## 关键设计决策

1. **LLM调用统一走 OpenAI-compatible API** — 用 httpx POST `{base_url}/chat/completions`，支持 DeepSeek/Moonshot/GLM/Qwen/OpenAI 等所有主流模型
2. **Agent并行执行** — 消息面/板块/宏观 3 个 Agent 用 `concurrent.futures.ThreadPoolExecutor` 并行，enhanced 串行汇总
3. **优雅降级** — LLM_ENABLED=false 或 API Key 未配置时，所有 Agent 走 fallback 逻辑，系统仍可正常使用
4. **零新依赖** — 完全复用现有 httpx + python-dotenv + akshare
5. **Agent 结果缓存** — AgentResultCache 表存储当日结果，避免重复 LLM 调用

## 验证方案

1. **后端验证**:
   - 不配置 LLM Key 时，所有 Agent 端点应返回 `status: "degraded"` + 原始数据
   - 配置 Key 后，Agent 端点应返回 `status: "success"` + AI 分析结果
   - `/api/agents/enhanced-advice/{code}` 应聚合全部4个维度
   - `curl` 逐一测试各端点

2. **前端验证**:
   - TypeScript 类型检查 + 构建通过
   - 4个新页面可正常访问和渲染
   - AnalysisPage 雷达图正确展示
   - 降级状态下页面不报错，显示"AI不可用"提示

3. **集成验证**:
   - 前后端联调，新页面数据正确展示
   - Settings 页可查看 LLM 状态
