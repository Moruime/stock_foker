# SectorAgent 全面升级

## 现状分析

当前 SectorAgent 有 4 个数据源：
1. `fetch_industry_board` — 行业板块基本信息、涨跌幅、板块内前 5 个股
2. `fetch_concept_boards` — 今日热门概念板块 top10
3. `fetch_hithink_industry_data` — 行业 PE/PB/ROE（已通过 DataSourceCache 缓存）
4. `fetch_hithink_market_data` — 主力资金净流入/大单/换手率（已通过 DataSourceCache 缓存）

前端 SectorPage 有 6 个独立视觉区块，布局松散。

## Task 1: 后端 — 新增行业财务汇总数据源

在 `data_fetcher.py` 新增 `fetch_hithink_industry_finance` 函数，查询行业整体财务概况（营收增速、净利润增速、毛利率、行业排名等），丰富板块分析的基本面维度。

在 `data_source_service.py` 的 `_SOURCE_REGISTRY` 中注册新数据源类型 `industry_finance`。

**文件**: `backend/app/services/data_fetcher.py`, `backend/app/services/data_source_service.py`

## Task 2: 后端 — SectorAgent 接入新数据源

修改 `sector_agent.py` 的 `fetch_data`，新增获取 `industry_finance` 数据源（通过 `get_data_source` 走缓存）。

将新数据传递给 `build_prompt`。

**文件**: `backend/app/agents/sector_agent.py`

## Task 3: 后端 — Prompt 优化

修改 `prompts.py` 的 `sector_prompt` 函数：
1. 给每个数据段落加编号（一、二、三...），与 sentiment_prompt 风格统一
2. 新增「行业财务概况」数据段落
3. 扩展 System prompt，明确要求 AI 综合行业估值、资金流向和行业财务做判断
4. 将 analysis 从 2-3 句扩展为 3-5 句
5. 输出 JSON 中新增 `industry_rank` 字段（行业在全市场的排名位置）

**文件**: `backend/app/llm/prompts.py`

## Task 4: 后端验证

执行 `python -c "from app.main import app"` 确认后端无导入错误。

## Task 5: 前端 — SectorPage 页面重构

参照 SentimentPage 的三区块设计，重构 SectorPage 为 3 个清晰的功能卡片：

**区域 1: AI 板块总览**（紧凑单卡片）
- 左侧：板块名称 + 趋势标签 + 轮动信号
- 右侧：统计指标（相对强度、PE、PB、ROE、主力净流入），用 `space-around` 填满
- 下方 Divider + 分析摘要（Paragraph ellipsis 3 行可展开）
- 合并了原来的「所属板块」「相对强度」「分析摘要」3 个独立 Card

**区域 2: 数据详情**（Card + 3 Tabs）
- Tab 1「行业估值」：PE/PB/ROE/行业中值/所属行业（原 industryValuation 面板）
- Tab 2「资金流向」：主力净流入/大单/换手率/量比/成交额（原 marketData 面板）
- Tab 3「行业财务」：营收增速/净利润增速/毛利率等（新增数据源）
- 每个 Tab 标签带条数和独立刷新按钮（复用 `tabLabel` 模式）

**区域 3: 关联板块与成分股**（Card + 2 Tabs）
- Tab 1「相关概念」：概念板块 Tag 列表
- Tab 2「板块成分股」：同行个股 Table

从 6 个松散 Card 精简为 3 个逻辑清晰的区块。

**文件**: `frontend/src/pages/SectorPage.tsx`

## Task 6: 前端验证

执行 `npx tsc --noEmit` 确认 TypeScript 编译通过。
