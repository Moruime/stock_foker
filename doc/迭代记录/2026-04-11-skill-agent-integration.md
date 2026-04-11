# 2026-04-11 同花顺 Skill 接入三大 Agent

## 1 开发概述

将已安装的同花顺 SkillHub 技能数据能力正式接入 MacroAgent、
SentimentAgent 和 EnhancedAdviceAgent，实现 AI 分析从「纯大盘行情」
升级至「宏观经济指标 + 基本面 + 结构化事件」五维分析体系。

## 2 新增功能

### 2.1 同花顺 API 通用客户端

| 功能 | 说明 |
| --- | --- |
| `_call_hithink_api()` | 封装问财 OpenAPI 调用，统一 SSL 修复、超时、错误处理 |
| `fetch_hithink_macro_indicators()` | 查询 CPI/PPI/PMI/LPR/M2 两组宏观指标 |
| `fetch_hithink_finance_data()` | 查询个股 ROE/净利润增速/毛利率/负债率/PE |
| `fetch_hithink_insresearch_data()` | 查询个股机构评级与目标价 |
| `fetch_hithink_events()` | 查询个股近期业绩预告/解禁/减持/增持事件 |

### 2.2 MacroAgent 数据增强

| 功能 | 说明 |
| --- | --- |
| 接入真实宏观数据 | 原只有 AKShare 大盘行情，现新增 CPI/PPI/PMI/LPR/M2 |
| Prompt 分层展示 | 市场行情数据与宏观经济指标数据分两段输入给 LLM |
| System 提示升级 | 明确要求 LLM 基于宏观经济指标（而非仅大盘数据）判断市场阶段 |

### 2.3 SentimentAgent 数据增强

| 功能 | 说明 |
| --- | --- |
| 接入结构化事件 | 业绩预告/解禁/减持/增持事件补充新闻面 |
| Prompt 有事件段落 | 当事件数据非空时动态注入「近期重要事件」段落 |

### 2.4 EnhancedAdviceAgent 第五维度

| 功能 | 说明 |
| --- | --- |
| 基本面财务数据输入 | ROE/净利润增速/毛利率/负债率/PE 作为第五维度 |
| 机构评级输入 | 机构一致评级与目标价作为第六输入段 |
| `dimension_scores` 扩展 | 新增 `fundamental` 维度，始终保证字段存在（含 fallback） |
| 推理步骤升级 | reasoning 从 6 步增加到 7 步，新增「基本面/机构评级维度判断」 |

### 2.5 前端五维雷达图

| 功能 | 说明 |
| --- | --- |
| AnalysisPage 雷达图 | indicator 从 4 个增加到 5 个，新增「基本面」轴 |
| 名称更新 | 「四维评分」改为「五维评分」 |
| SnapshotPanel 维度标签 | `dimLabels` 新增 `fundamental: '基本面'` |

## 3 关键文件变更

### 3.1 修改文件

| 文件 | 变更 |
| --- | --- |
| `backend/app/services/data_fetcher.py` | 新增同花顺 API 客户端及 4 个 fetch 函数 |
| `backend/app/agents/macro_agent.py` | 调用 `fetch_hithink_macro_indicators` |
| `backend/app/agents/sentiment_agent.py` | 调用 `fetch_hithink_events` |
| `backend/app/agents/enhanced_advice_agent.py` | 调用财务/机构评级接口，扩展 fundamental 维度 |
| `backend/app/llm/prompts.py` | 更新三个 Agent 的 Prompt 模板 |
| `frontend/src/pages/AnalysisPage.tsx` | 雷达图 4 维升级为 5 维 |
| `frontend/src/components/SnapshotPanel.tsx` | 新增 fundamental 维度标签 |
