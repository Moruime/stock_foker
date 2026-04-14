# 2026-04-14 数据展示补全与修复 - 迭代记录

## 开发概述

宏观环境页（MacroPage）补全 3 个数据源展示，
消息面页（SentimentPage）补全业绩预告 Tab，
并修复多个字段适配与交互问题。

## 新增功能

| 功能 | 说明 |
| --- | --- |
| 宏观经济指标卡片 | CPI/PPI/PMI 月度数据展示，自适应列宽，附数据期标注 |
| 涨跌概况统计 | A 股上涨/下跌/涨停/跌停家数，红绿配色 |
| 主力资金流向 Top10 | 问财 API 返回的主力资金流向排名表格，含代码/名称/资金流/涨跌幅 |
| 业绩预告 Tab | SentimentPage 新增 Tab，展示变动类型/预告净利润/增长率/报告期/公告日期 |

## 问题修复

| 问题 | 原因 | 解决方案 |
| --- | --- | --- |
| 业绩预告字段全空 | API 返回字段名为`变动类型`而非`预告类型`，`净利润增长率`而非`变动幅度` | 修正所有字段关键词匹配 |
| 北向资金净买入额为空 | API 返回`主力资金流向[日期]`而非`净买入` | 改匹配`主力资金流向`，标题改为主力资金流向 Top10 |
| 宏观经济指标不显示 | `findNum(row, 'CPI同比')`无法匹配`指标值`字段 | 改为直接读取`row['指标值']` |
| CPI 显示 0.0%（年度数据） | 查询词`最近一期CPI同比增速`返回年度周期 | 改为`中国CPI当月同比最新值`获取月度数据 |
| 变动原因弹窗无响应 | Ant Design 5 `Modal.info()`静态方法需 App 组件支持 | 改用`App.useApp()` hook 的`modal.info()` |
| 宏观指标卡片大段留白 | `Col span=4`仅占 1/6 宽度，3 个指标只填一半 | 根据指标数量自适应 span（3 个用 8） |

## 工程改进

- App.tsx 增加 `<AntApp>` 组件包裹，
  为全局 Modal/Message 静态方法提供上下文
- 后端新注册 4 个数据源：`north_flow`、
  `market_overview`、`hithink_macro`、
  `hithink_events`
- 清理 hithink_macro 旧缓存，确保查询词更新后生效

## 关键文件变更

### 修改文件

| 文件 | 变更说明 |
| --- | --- |
| `frontend/src/App.tsx` | 增加 AntApp 组件包裹 |
| `frontend/src/pages/MacroPage.tsx` | 重写布局，新增 3 个数据源卡片，修复字段匹配与自适应列宽 |
| `frontend/src/pages/SentimentPage.tsx` | 新增业绩预告 Tab，修复 Modal 为 hook 方式，新增公告日期列 |
| `backend/app/services/data_source_service.py` | 注册 4 个新数据源到 `_SOURCE_REGISTRY` |
| `backend/app/services/data_fetcher.py` | CPI/PPI 查询词改为月度当月同比，更新 north_flow 文档注释 |
