# 同花顺问财 API 实测报告

> 测试日期：2026-04-14 22:30 CST

## 1 测试环境

- API 端点：`openapi.iwencai.com`
- 接口：`/v1/query2data` + `/v1/comprehensive/search`
- 认证：Bearer Token（IWENCAI_API_KEY）

## 2 query2data 接口测试结果

### 2.1 个股数据查询

| 函数 | 查询词 | 状态 | 结果数 |
| --- | --- | --- | --- |
| `fetch_hithink_finance_data` | 贵州茅台最新ROE净利润... | PASS | 1 |
| `fetch_hithink_basicinfo` | 宁德时代所属行业上市日期... | PASS | 1 |
| `fetch_hithink_shareholders` | 贵州茅台股东户数前十大... | PASS | 10 |
| `fetch_hithink_market_data` | 宁德时代主力资金净流入... | PASS | 1 |
| `fetch_hithink_business_data` | 宁德时代主营业务构成... | PASS | 9 |
| `fetch_hithink_insresearch_data` | 贵州茅台机构评级... | PASS | 5 |

### 2.2 板块联动查询

| 函数 | 查询词 | 状态 | 结果数 |
| --- | --- | --- | --- |
| `fetch_concept_boards` | 宁德时代所属概念板块 | PASS | 1 |
| `fetch_industry_board` | 宁德时代所属同花顺行业 | PASS | 1 |
| `fetch_hithink_industry_data` | 宁德时代所属行业PE PB... | PASS | 1 |
| `fetch_hithink_industry_finance` | 宁德时代所属行业营收... | PASS | 10 |
| `fetch_hithink_industry_peers` | 宁德时代同行业个股... | PASS | 10 |

### 2.3 宏观与市场概览

| 函数 | 查询词 | 状态 | 结果数 |
| --- | --- | --- | --- |
| `fetch_hithink_macro_indicators` | CPI/PPI/PMI/LPR 分查 | PASS | 4key |
| `fetch_hithink_index_data` | 上证/沪深300/创业板指... | PASS | 3 |
| `fetch_index_data` | 上证指数最近5交易日... | PASS | 1 |
| `fetch_north_flow` | 今日北向资金净买入额前10 | PASS | 10 |
| `fetch_market_overview` | 今日A股上涨下跌涨停跌停 | PASS | 1 |

### 2.4 事件与新闻

| 函数 | 查询词 | 状态 | 结果数 |
| --- | --- | --- | --- |
| `fetch_hithink_events` | 宁德时代最新业绩预告... | PASS | 1 |
| `fetch_stock_news` | 宁德时代近期重大新闻... | PASS | 7 |

## 3 comprehensive/search 接口测试结果

| 函数 | channel | 状态 | 结果数 |
| --- | --- | --- | --- |
| `fetch_hithink_news` | news | PASS | 10 |
| `fetch_hithink_reports` | report | PASS | 10 |
| `fetch_hithink_announcements` | announcement | PASS | 10 |

## 4 总结

- **21/21 函数全部返回有效数据**
- `query2data` 接口：18 个查询均成功
- `comprehensive/search` 接口：3 个 channel 均成功
- 无超时、无认证失败、无网络异常

## 5 已知 API 限制

| 限制 | 说明 | 应对策略 |
| --- | --- | --- |
| 复合概念查询 -2058 | 概念+涨跌幅+成份股数量 | 仅查所属概念名称 |
| 行业复合查询 0 条 | 行业+换手率+前5个股 | 拆分为独立查询 |
| 宏观指标合并丢数据 | CPI+PPI+PMI 合查缺 PPI | 拆分为单指标查询 |
| 北向资金无汇总接口 | 返回个股维度非汇总额 | 改为净买入额 Top10 |
| 事件类查询精度有限 | 解禁/增减持返回不含详情 | 聚焦业绩预告获取详情 |
