# 2026-04-14 数据展示补全与修复 - 迭代记录

## 开发概述

宏观环境页（MacroPage）补全 3 个数据源展示，
消息面页（SentimentPage）补全业绩预告 Tab，
并修复多个字段适配与交互问题。
下半场实现副图指标面板（MACD/KDJ/RSI），
修复 AKShare 成交量单位错误，添加 API 响应 no-cache 机制。

## 新增功能

| 功能 | 说明 |
| --- | --- |
| 宏观经济指标卡片 | CPI/PPI/PMI 月度数据展示，flex 一行居中布局 |
| 涨跌概况统计 | A 股上涨/下跌/涨停/跌停家数，红绿配色 |
| 主力资金流向 Top10 | 问财 API 返回的主力资金流向排名表格，含代码/名称/资金流/涨跌幅 |
| 业绩预告 Tab | SentimentPage 新增 Tab，展示变动类型/预告净利润/增长率/报告期/公告日期 |
| 副图指标面板 | K 线图下方新增 MACD/KDJ/RSI 可切换副图，3 层 grid + dataZoom 联动 |
| API no-cache 机制 | 前端 axios + 后端 NoCacheMiddleware 双重禁止浏览器缓存 API 响应 |

## 问题修复

| 问题 | 原因 | 解决方案 |
| --- | --- | --- |
| 业绩预告字段全空 | API 返回字段名为`变动类型`而非`预告类型`，`净利润增长率`而非`变动幅度` | 修正所有字段关键词匹配 |
| 北向资金净买入额为空 | API 返回`主力资金流向[日期]`而非`净买入` | 改匹配`主力资金流向`，标题改为主力资金流向 Top10 |
| 宏观经济指标不显示 | `findNum(row, 'CPI同比')`无法匹配`指标值`字段 | 改为直接读取`row['指标值']` |
| CPI 显示 0.0%（年度数据） | 查询词`最近一期CPI同比增速`返回年度周期 | 改为`中国CPI当月同比最新值`获取月度数据 |
| 变动原因弹窗无响应 | Ant Design 5 `Modal.info()`静态方法需 App 组件支持 | 改用`App.useApp()` hook 的`modal.info()` |
| 宏观指标卡片大段留白 | `Col span=4`仅占 1/6 宽度，3 个指标只填一半 | 改为 flex 一行布局，flex:1 均分居中 |
| 成交量柱近期不可见 | AKShare 成交量单位为手（Sina 为股），混用导致新数据小 100 倍 | `_get_kline_akshare` 中 volume×100 转换单位 |
| 浏览器缓存旧 API 响应 | FastAPI 未设置 Cache-Control 头，浏览器缓存 GET 请求 | 前后端添加 no-cache/no-store 头 |

## 工程改进

- App.tsx 增加 `<AntApp>` 组件包裹，
  为全局 Modal/Message 静态方法提供上下文
- 后端新注册 4 个数据源：`north_flow`、
  `market_overview`、`hithink_macro`、
  `hithink_events`
- 清理 hithink_macro 旧缓存，确保查询词更新后生效
- 后端 main.py 添加 NoCacheMiddleware，
  对 `/api/` 路径响应设置 no-store/no-cache
- 前端 axios 实例添加 Cache-Control/Pragma 请求头
- 清空全部 kline_cache 缓存修正 AKShare 单位污染数据

## 关键文件变更

### 新增文件

| 文件 | 说明 |
| --- | --- |
| 无 | - |

### 修改文件

| 文件 | 变更说明 |
| --- | --- |
| `frontend/src/App.tsx` | 增加 AntApp 组件包裹 |
| `frontend/src/pages/MacroPage.tsx` | 重写布局为 flex 一行居中，新增 3 个数据源卡片 |
| `frontend/src/pages/SentimentPage.tsx` | 新增业绩预告 Tab，修复 Modal 为 hook 方式 |
| `frontend/src/pages/AnalysisPage.tsx` | 副图指标面板（3 层 grid、MACD/KDJ/RSI 切换、tooltip 增强）；ReactECharts 添加 key 强制重建 |
| `frontend/src/services/api.ts` | axios 实例添加 no-cache 请求头 |
| `backend/app/main.py` | 添加 NoCacheMiddleware 禁止浏览器缓存 API 响应 |
| `backend/app/services/stock_service.py` | `_get_kline_akshare` 成交量×100 转换（手→股） |
| `backend/app/services/data_source_service.py` | 注册 4 个新数据源 |
| `backend/app/services/data_fetcher.py` | CPI/PPI 查询词改为月度当月同比 |
