# 2026-04-09 Agent 缓存机制与每日记录实现

## 1 开发概述

本次分两轮实现：第一轮建立 Agent 双层缓存机制与每日快照记录；第二轮完善缓存体系
（当日过滤修复、AI 综合分析缓存恢复、9 点整刷新边界）并安装同花顺问财财务数据查询
Skill。

## 2 新增功能

### 2.1 Agent 缓存机制

| 功能 | 说明 |
| --- | --- |
| 前端 AgentCacheContext | 内存缓存层，按 9am 边界失效，useRef 存储避免无谓 re-render |
| 页面缓存命中即显示 | 三个 Agent 页面 mount 时优先读取前端缓存，命中直接展示无 loading |
| AnalysisPage 自动展示缓存 | 切换股票时有缓存则自动展示 AI 综合分析，无需点击"开始分析" |
| 缓存时间戳展示 | 命中缓存时页面头部显示"缓存于 HH:mm" |
| 手动刷新清双层缓存 | 刷新按钮同时清后端 DB 缓存和前端 Context 缓存 |

### 2.2 Agent 每日记录

| 功能 | 说明 |
| --- | --- |
| daily_agent_snapshot 表 | 每种 Agent 每支股票每天保留最新一条关键指标快照 |
| 自动保存 | Agent 运行成功后自动抽取关键字段写入快照表 |
| 日期回溯 API | `GET /api/snapshots/{agent_type}/dates` 和 `/{date}` 两个端点 |
| SnapshotPanel 组件 | 左栏日期列表 + 右栏详情，三种 Agent 各自定制展示 |
| 三页面内嵌面板 | 消息面/板块联动/宏观环境页底部各自嵌入历史记录面板 |

### 2.3 enhanced_advice 快照支持

| 功能 | 说明 |
| --- | --- |
| 后端快照字段扩展 | `_SNAPSHOT_FIELDS` 新增 `enhanced_advice`（7 个字段） |
| snapshot_router 白名单扩展 | `enhanced_advice` 加入合法 `agent_type` 列表 |
| 前端 EnhancedAdviceDetail 组件 | 展示信号标签、置信度进度条、维度分数、分析依据、风险提示 |
| AnalysisPage 嵌入历史面板 | AI 综合分析卡片下方嵌入 SnapshotPanel |

### 2.4 AI 综合分析页面缓存恢复

| 功能 | 说明 |
| --- | --- |
| 新增只读缓存端点 | `GET /api/agent/enhanced-analysis/cached/{stock_code}`，仅查 DB 缓存 |
| 页面 mount 自动恢复 | `useEffect` 内存缓存 miss 后自动查后端 DB，有则展示，无则空态 |
| 三层缓存加载顺序 | 前端内存缓存 → 后端 DB 缓存（只读端点）→ 空态等待手动触发 |

### 2.5 9:00 AM 缓存新鲜度边界

| 功能 | 说明 |
| --- | --- |
| 后端 `_last_9am()` 边界函数 | 以每天 09:00 为界，此后生成的缓存才算新鲜 |
| `_get_stale_cached()` 函数 | 返回最近一条缓存（含过期），供页面 mount 恢复旧数据 |
| 前端 Context 有效性对齐 | `AgentCacheContext.isValidEntry` 改为 9am 边界判断 |
| 过期数据前端提示 | AnalysisPage 展示橙色 Alert 提示数据为 09:00 前的旧数据 |

### 2.6 同花顺问财财务数据查询 Skill 安装

| 功能 | 说明 |
| --- | --- |
| aime-skillhub-cli 安装 | 安装同花顺官方 Skill 管理 CLI |
| 财务数据查询 Skill | 支持营业收入、净利润、ROE、负债率、现金流等全市场查询 |
| Qoder 技能集成 | SKILL.md 放入 `.qoder/skills/hithink-finance-query/` |
| 环境变量配置 | `IWENCAI_BASE_URL` 和 `IWENCAI_API_KEY` 写入 `backend/.env` |

## 3 问题修复

| 问题 | 原因 | 解决方案 |
| --- | --- | --- |
| enhanced-analysis 每次都调 LLM | 端点只检查上游三 Agent 缓存，未检查 enhanced_advice 自身 | 端点开头补充对 enhanced_advice 的缓存查询 |
| 历史记录仍显示当天数据 | `todayStr()` 使用 `toISOString()` 返回 UTC，与后端本地时间不匹配 | 改为本地时间 `getFullYear/getMonth/getDate` 拼接 |
| AI 综合分析页面刷新后需重新分析 | `useEffect` 只查前端内存缓存，刷新后内存清空即无数据 | 新增后端只读缓存端点，mount 时自动查询并恢复 |
| 同花顺 CLI SSL 证书错误 | macOS Python 标准库不自带根证书 | `cli.py` 添加 `ssl.CERT_NONE` 上下文绕过校验 |

## 4 工程改进

- 新增 `frontend/src/contexts/` 目录，建立前端 Context 规范位置
- 安装 `aime-skillhub-cli`，项目具备从问财 SkillHub 安装金融技能的能力
- `backend/.env.example` 新增同花顺 API 配置占位符，规范化配置文档

## 5 关键文件变更

### 5.1 新增文件

| 文件 | 说明 |
| --- | --- |
| `frontend/src/contexts/AgentCacheContext.tsx` | Agent 前端内存缓存 Context |
| `backend/app/routers/snapshot_router.py` | 快照查询路由 |
| `frontend/src/components/SnapshotPanel.tsx` | 历史记录面板组件 |
| `.qoder/skills/hithink-finance-query/SKILL.md` | 同花顺财务数据查询 Skill 定义 |
| `.qoder/skills/hithink-finance-query/scripts/cli.py` | 财务数据查询 CLI 脚本（已修复 SSL） |

### 5.2 修改文件

| 文件 | 变更 |
| --- | --- |
| `backend/app/models/models.py` | 新增 DailyAgentSnapshot 模型 |
| `backend/app/models/schemas.py` | 新增 SnapshotResponse Schema |
| `backend/app/routers/agent_router.py` | 缓存修复 + 快照钩子 + `_last_9am()`/`_get_stale_cached()` + 只读缓存端点 |
| `backend/app/main.py` | 注册 snapshot_router |
| `backend/app/routers/snapshot_router.py` | `enhanced_advice` 加入合法类型白名单 |
| `frontend/src/App.tsx` | 用 AgentCacheProvider 包裹 Router |
| `frontend/src/types/index.ts` | 新增 AgentSnapshot 类型 |
| `frontend/src/services/api.ts` | 新增 getSnapshotDates / getSnapshotDetail / getCachedEnhancedAnalysis |
| `frontend/src/contexts/AgentCacheContext.tsx` | `isValidEntry` 改为 9am 边界，修复 UTC 时区问题 |
| `frontend/src/components/SnapshotPanel.tsx` | 新增 EnhancedAdviceDetail 组件，修复 `todayStr()` 时区问题，清理今日角标 |
| `frontend/src/pages/SentimentPage.tsx` | 接入缓存 + 嵌入 SnapshotPanel |
| `frontend/src/pages/SectorPage.tsx` | 接入缓存 + 嵌入 SnapshotPanel |
| `frontend/src/pages/MacroPage.tsx` | 接入缓存 + 嵌入 SnapshotPanel |
| `frontend/src/pages/AnalysisPage.tsx` | 缓存自动展示 + mount 恢复 + isStale() + 过期 Alert + 嵌入 SnapshotPanel |
| `backend/.env.example` | 新增同花顺 API 配置段 |
