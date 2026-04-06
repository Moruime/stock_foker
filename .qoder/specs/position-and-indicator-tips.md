# 持仓管理 + 指标含义提示 实现方案

## 背景

1. 当前应用只有交易记录（TradeRecord），无法记录某支股票的当前持仓信息（成本价、数量、止盈止损等）
2. 指标概览（indicators_summary）直接显示英文 key（如 macd_dif），用户不知道含义

## 功能1：持仓管理

### 后端 — 数据模型 `StockPosition`

新增表 `stock_positions`，字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| stock_code | String(10) UNIQUE | 股票代码（每票仅一条） |
| stock_name | String(50) | 股票名称 |
| cost_price | Float | 持仓成本价 |
| quantity | Integer | 持仓数量 |
| take_profit_price | Float nullable | 止盈价 |
| stop_loss_price | Float nullable | 止损价 |
| first_buy_date | DateTime | 首次买入日期 |
| note | Text nullable | 备注 |
| created_at / updated_at | DateTime | 时间戳 |

不存储市值、盈亏、天数 — 前端结合实时价格计算。

### 后端 — Schema

- `PositionCreate`：stock_code, stock_name, cost_price, quantity, first_buy_date 必填，其余可选
- `PositionUpdate`：所有字段可选，部分更新
- `PositionResponse`：全字段 + id + 时间戳

### 后端 — API

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/positions/{stock_code}` | 获取持仓 |
| POST | `/api/positions` | 创建持仓 |
| PUT | `/api/positions/{stock_code}` | 更新持仓 |
| DELETE | `/api/positions/{stock_code}` | 删除持仓 |

### 前端 — PositionCard 组件

新建 `frontend/src/components/PositionCard.tsx`，在两个页面复用。

Props: `stockCode`, `stockName`, `currentPrice?`

有持仓时显示卡片：成本价、数量、市值、浮动盈亏（金额+百分比）、首次买入日期、持仓天数、止盈止损价（含预警 Tag）。带编辑和删除按钮。

无持仓时显示"添加持仓"按钮。

颜色：盈利 = `COLORS.stockUp`（红），亏损 = `COLORS.stockDown`（绿），符合 A 股惯例。

### 前端 — 页面嵌入

- **AnalysisPage.tsx**: 在周期选择器与 K 线图之间插入，传入 `currentPrice = advice.indicators_summary.current_price`
- **TradesPage.tsx**: 在标题行与表格之间插入，不传 currentPrice（盈亏显示"—"）

## 功能2：指标含义提示

### 纯前端实现

新建 `frontend/src/constants/indicators.ts`，定义指标中英文映射 + 含义 + 动态解读：

| Key | 中文名 | 含义摘要 |
|-----|--------|---------|
| current_price | 当前价 | 最新收盘价 |
| macd_dif | MACD DIF | 快慢均线差值，DIF > DEA 为多头 |
| macd_dea | MACD DEA | DIF 的信号线 |
| kdj_k | KDJ K值 | <20 超卖，>80 超买 |
| kdj_d | KDJ D值 | K 的均线，K 上穿 D 为金叉 |
| kdj_j | KDJ J值 | <0 极度超卖，>100 极度超买 |
| rsi | RSI | <30 超卖，>70 超买 |
| ma5/ma10/ma20 | 均线 | 股价在上方偏多，下方偏空 |
| boll_upper/lower | 布林带 | 触及上轨注意压力，触及下轨可能支撑 |

每个指标还有 `interpret(value, allIndicators)` 函数，根据当前值生成动态解读文字。

### AnalysisPage.tsx 指标概览改造

- label 从英文 key 改为中文名
- label 后加 `Tooltip` 包裹的 `QuestionCircleOutlined` 图标
- Tooltip 内容：指标含义 + 当前值动态解读

## 涉及文件

| 文件 | 操作 |
|------|------|
| `backend/app/models/models.py` | 修改 — 新增 StockPosition 模型 |
| `backend/app/models/schemas.py` | 修改 — 新增 3 个 Position Schema |
| `backend/app/routers/stock_router.py` | 修改 — 新增 4 个持仓端点 |
| `frontend/src/types/index.ts` | 修改 — 新增 Position 类型 |
| `frontend/src/services/api.ts` | 修改 — 新增 4 个持仓 API 函数 |
| `frontend/src/constants/indicators.ts` | 新建 — 指标映射+含义+解读 |
| `frontend/src/components/PositionCard.tsx` | 新建 — 持仓卡片组件 |
| `frontend/src/pages/AnalysisPage.tsx` | 修改 — 嵌入 PositionCard + 指标 Tooltip |
| `frontend/src/pages/TradesPage.tsx` | 修改 — 嵌入 PositionCard |

## 实施顺序

1. 后端：models.py -> schemas.py -> stock_router.py
2. 前端指标提示：constants/indicators.ts -> AnalysisPage.tsx 指标改造（可与1并行）
3. 前端持仓：types -> api.ts -> PositionCard.tsx -> 嵌入两个页面

## 验证

1. `npx tsc --noEmit` + `npx vite build` 通过
2. 后端启动后自动建表，curl 测试持仓 CRUD
3. 页面验证：分析页持仓卡片展示、指标 Tooltip、交易记录页持仓卡片
