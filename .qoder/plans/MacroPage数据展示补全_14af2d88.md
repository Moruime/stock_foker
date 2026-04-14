# 宏观页 + 消息面页数据展示补全

## 现状分析

### MacroPage 缺失数据

当前展示：AI概览 + 指数行情 + AI关键指标 + 分析摘要

缺失 3 个数据源（仅作 LLM 输入）：
- `north_flow` — 北向资金净买入 Top10
- `market_overview` — A股涨跌停统计
- `hithink_macro` — 宏观指标 CPI/PPI/PMI/LPR/M2/社融

### SentimentPage 缺失数据

当前信息流 4 个 Tab：AI重点 / 财经资讯 / 公司公告 / 研报观点

缺失：
- `hithink_events` — 业绩预告（含预告类型、预计净利润、变动原因），当前仅作 LLM 输入，未注册到 `_SOURCE_REGISTRY`，前端无展示

## 目标布局（自上而下）

```
+--[ 宏观环境分析 ]---------------------------[ 缓存时间 | 刷新 ]--+
|                                                                  |
|  [ 市场阶段 ]    [ 市场情绪 ]    [ 风险等级 ]     <-- AI 概览    |
|                                                                  |
|  +--- 主要指数行情 (span=16) ---+  +--- 涨跌概况 (span=8) ---+  |
|  | 上证指数  沪深300  创业板指   |  |  上涨 XXXX  下跌 XXXX   |  |
|  | 3300.00   3900.00  2100.00   |  |  涨停 XX    跌停 XX     |  |
|  | +0.52%    -0.13%   +1.02%   |  |                          |  |
|  +------------------------------+  +--------------------------+  |
|                                                                  |
|  +--- 宏观经济指标 (full width) ----------------------------+    |
|  | CPI同比 | PPI同比 | 制造业PMI | LPR | M2同比 | 社融      |    |
|  | +0.1%   | -2.8%   | 50.2     | 3.1%| 7.0%   | 3.2万亿   |    |
|  +----------------------------------------------------------+    |
|                                                                  |
|  +--- 北向资金净买入 Top10 (full width) --------------------+    |
|  | # | 股票名称 | 净买入额(亿) | 涨跌幅                     |    |
|  | 1 | 贵州茅台 | 8.32         | +1.23%                     |    |
|  | ...                                                       |    |
|  +----------------------------------------------------------+    |
|                                                                  |
|  +--- AI 关键指标 ---+  +--- 对 XX 的影响 + 分析摘要 ------+    |
|  | (保持原样)         |  | (合并为一个卡片，减少碎片感)      |    |
|  +-------------------+  +-----------------------------------+    |
+------------------------------------------------------------------+
```

设计要点：
- 指数行情与涨跌概况并排（2:1），信息密度高且对比直观
- 宏观指标用 Statistic 组件横排，数值配色（正红负绿）
- 北向资金用紧凑 Table，净买入额单位换算为亿，涨跌幅配色
- AI 分析区将"关键指标" + "对个股影响" + "分析摘要"合并为一个卡片（减少碎片）

## Task 1: 后端 — 注册 4 个新数据源

文件: `backend/app/services/data_source_service.py`

在 `_SOURCE_REGISTRY` 中新增 4 个条目：

```python
"north_flow":       (fetch_north_flow, False),       # 全局数据，不需要 stock_name
"market_overview":  (fetch_market_overview, False),   # 全局数据
"hithink_macro":    (fetch_hithink_macro_indicators, False),  # 全局数据
"hithink_events":   (fetch_hithink_events, True),     # 个股数据，需要 stock_name
```

同时在文件顶部补充对应的 import。

## Task 2: 前端 — MacroPage 完整改版

文件: `frontend/src/pages/MacroPage.tsx`

### 2a. 新增 3 个 useDataSource hook

```tsx
const northFlow = useDataSource(focus?.stock_code, focus?.stock_name, 'north_flow');
const marketOverview = useDataSource(focus?.stock_code, focus?.stock_name, 'market_overview');
const hithinkMacro = useDataSource(focus?.stock_code, focus?.stock_name, 'hithink_macro');
```

### 2b. handleRefresh 中增加新数据源刷新

### 2c. 数据解析

- `market_overview`: 从 `datas[0]` 提取上涨家数/下跌家数/涨停家数/跌停家数
- `north_flow`: `datas` 数组，每行含股票简称、净买入额、涨跌幅
- `hithink_macro`: 字典结构 `{cpi: {datas: [...]}, ppi: {...}, pmi: {...}, monetary: {...}}`

### 2d. 布局重构

1. AI 概览行（保持 3 stat cards）
2. Row: 指数行情(Col span=16) + 涨跌概况(Col span=8)
   - 涨跌概况用 Ant Design `Statistic` 组件，4 个数字 2x2 网格
   - 上涨/涨停用红色，下跌/跌停用绿色
3. 宏观经济指标卡片（full width）
   - 横排 6 个 Statistic，用 Row/Col 均匀分布
   - 正值红色，负值绿色（A股配色）
4. 北向资金 Top10 表格（full width）
   - 列: 排名 / 股票简称 / 净买入额(亿) / 涨跌幅
   - 紧凑 size="small"，无分页
   - 净买入额和涨跌幅配色
5. AI 综合分析卡片（合并原来 3 个小卡片）
   - 用 Divider 分隔：关键指标 → 对个股影响 → 分析摘要

### 2e. 新增 import

- `Statistic, Table, Divider` from antd

## Task 3: 前端 — SentimentPage 补充业绩预告

文件: `frontend/src/pages/SentimentPage.tsx`

### 3a. 新增 useDataSource hook

```tsx
const eventsDS = useDataSource(focus?.stock_code, focus?.stock_name, 'hithink_events');
```

### 3b. handleRefresh 中补充 eventsDS.refresh()

### 3c. 信息流新增"业绩预告"Tab

在信息流 Tabs 中插入（位于 AI重点 之后、财经资讯 之前）：

- Tab 标签: "业绩预告"，带数量 + loading 指示
- 展示方式: Table（非 List），更适合结构化数据
- 列: 预告类型 / 预计净利润 / 变动幅度 / 变动原因
- 问财返回字段名含中文关键词，用 findVal 模糊匹配
- 预告类型用 Tag 配色：预增/略增(红) 预减/略减/首亏/续亏(绿)
- AI概览统计区新增"业绩预告"计数

### 3d. 数据解析

`hithink_events` 返回 `{datas: [...]}` 格式，每条记录含：
- 股票简称、预告类型、预告净利润下限/上限、变动原因等字段
- 需用 Object.keys + includes 模糊匹配字段名

## Task 4: 验证

- 后端 import 验证
- 前端 TypeScript 类型检查
- 重启后端服务
