# 2026-04-12 Skill 深度集成 - 待办列表

## 1 已完成事项（本次迭代）

| 事项 | 说明 |
| --- | --- |
| ~~SectorAgent 接入 hithink-industry-query~~ | ✅ 行业 PE/PB/ROE 估值数据 |
| ~~SentimentAgent 接入 news-search + announcement-search~~ | ✅ 财经资讯 + 公告搜索 |
| ~~MacroAgent 接入 hithink-zhishu-query~~ | ✅ 指数实时行情 |
| ~~SectorAgent 接入 hithink-market-query~~ | ✅ 主力资金流向 |
| ~~EnhancedAdviceAgent 接入 report-search + business-query~~ | ✅ 研报 + 经营数据 |
| ~~基本资料 + 股东股本接入 EnhancedAdviceAgent~~ | ✅ basicinfo + shareholders |
| ~~同花顺 API 并行化优化~~ | ✅ ThreadPoolExecutor 并行调度 |
| ~~验证同花顺 API 实际返回格式~~ | ✅ 导入验证 + parallel_fetch 单元测试通过 |
| ~~考虑 hithink-market-query 接入~~ | ✅ 已接入 SectorAgent |

## 2 遗留问题

| 问题 | 优先级 | 说明 |
| --- | --- | --- |
| 同花顺 API 实际运行验证 | 高 | 需配置 IWENCAI_API_KEY 后实测各接口返回数据格式 |
| 副图指标面板未实现 | 中 | MACD/KDJ/RSI 数值已传至前端，独立子图待实现 |
| Agent 全链路响应时间 | 中 | 已并行化，但需实测验证性能提升效果 |
| 缺少大盘整体数据看板 | 中 | 宏观环境页有 LLM 分析结论，但缺直观数字看板 |
| 历史关注列表无前端入口 | 低 | GET /api/focus/history 已实现，前端暂无展示入口 |
| 快照面板需手动刷新日期列表 | 低 | Agent 刷新后快照面板不会自动更新日期列表 |

## 3 待开发事项

### 3.1 第三阶段功能（产品设计文档 5.3 节）

| 功能 | 章节 | 说明 |
| --- | --- | --- |
| 智能选股推荐 | 2.9 | 基于画像筛选标的，覆盖个股和 ETF |
| 复盘模块 | 2.10 | 单笔复盘 + 周期性报告（周报/月报） |
| 回测功能 | 2.11 | 策略历史数据回测 |
| 通知与提醒 | 2.12 | 价格触达、公告、指标信号、止盈止损提醒 |

### 3.2 第二阶段剩余功能

| 功能 | 章节 | 说明 |
| --- | --- | --- |
| 对比基准分析 | 2.2.3 | 个股 vs 大盘/板块对比 |
| 分时走势图 | 2.2.1 | 交易时段分时数据 |
| 止盈止损触达提醒 | 2.7.2 | 价格监控 + 主动通知 |
| 风险预警 | 2.7.3 | 连续亏损冷静期、异常波动预警 |
| 大盘数据看板 | 2.5 | 大盘 K 线、涨跌家数分布、成交额、北向资金等 |

## 4 优化建议

### 4.1 性能优化

- SSE 流式返回：先展示已完成 Agent 结果，再展示综合建议
- LLM 调用优化：Prompt 中数据过长时需要更精细的截断策略

### 4.2 工程质量

- 自动化测试：当前无测试覆盖，需补充 Agent 单元测试和 API 集成测试
- 错误监控：Agent 错误目前仅记录在日志和缓存表，缺少聚合监控

### 4.3 功能增强

- Prompt 版本管理：Agent Prompt 模板可外置为配置文件，便于迭代优化
- 多模型切换：Settings 页直接切换不同 LLM 模型
- SnapshotPanel 与 Agent 刷新联动

## 5 后续计划

1. 配置 IWENCAI_API_KEY 实测所有新增接口返回数据格式
2. 根据实测结果调整 Prompt 中的数据解析说明
3. 优先补充副图指标面板（MACD/KDJ/RSI 独立子图）
4. 补充核心路径自动化测试
5. 启动第三阶段功能规划
