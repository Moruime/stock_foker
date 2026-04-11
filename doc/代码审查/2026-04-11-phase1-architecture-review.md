# Stock Foker 第一期代码审查报告

> 审查日期：2026-04-11
> 审查范围：全项目架构、前后端交互、Agent 交互、
> 数据传递、缓存与数据库存储

## 一、审查概述

本次审查覆盖后端全部 Python 模块和前端全部
TypeScript 模块，共计约 5500 行有效代码。

整体评价：项目分层清晰、缓存策略完善、
错误处理覆盖面广。以下按严重程度分级列出问题。

---

## 二、严重问题（P0 — 需尽快修复）

### 2.1 SQLite Session 跨线程共享

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `agent_router.py` L284-294 |
| 描述 | ThreadPoolExecutor 并行 3 个 Agent，同一 db Session 被传入所有线程 |
| 风险 | 并发写入可能触发 ProgrammingError 或数据损坏 |
| 建议 | 每线程创建独立 Session，用完关闭 |

### 2.2 SectorAgent 降级路径签名不匹配

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `sector_agent.py` L37 |
| 描述 | else 分支调用 `fetch_concept_boards()` 不传 stock_name，导致 TypeError |
| 风险 | 无 db 场景下直接崩溃 |
| 建议 | 改为 `fetch_concept_boards(stock_name)` |

---

## 三、中等问题（P1 — 建议近期修复）

### 3.1 LLM 重试无退避间隔

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `llm/client.py` L60-75 |
| 描述 | `chat()` 3 次重试无 sleep，对限流 API 无帮助 |
| 建议 | 加入指数退避 `time.sleep(2 ** attempt)` |

### 3.2 数据源缓存双重查询

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `data_source_service.py` L76-147 |
| 描述 | 先查 data 再查 created_at，合计 2 次 SQL |
| 建议 | 返回 `(data, created_at)` 元组，一次查询 |

### 3.3 快照校验错误消息不完整

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `snapshot_router.py` L22-27 |
| 描述 | 错误消息写死，未包含 enhanced_advice |
| 建议 | 动态拼接 `_VALID_AGENT_TYPES` |

### 3.4 删除交易记录未回滚持仓

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `stock_router.py` L275-283 |
| 描述 | 删除 realtime 记录时未反向更新持仓 |
| 风险 | 持仓数量/成本不一致 |
| 建议 | 删除时反向更新持仓 |

### 3.5 K 线缓存盘中更新遗漏 turnover

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `stock_service.py` L298-310 |
| 描述 | 当日数据 `.update()` 遗漏 turnover 字段 |
| 建议 | 补充 turnover 字段 |

### 3.6 前端内存缓存无上限

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `AgentCacheContext.tsx` + `useDataSource.ts` |
| 描述 | Map 缓存随浏览股票持续增长，无淘汰机制 |
| 风险 | 长时间使用后内存占用上升 |
| 建议 | 加入 LRU 或按数量上限裁剪 |

### 3.7 FocusStock 并发设置竞态

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `stock_router.py` L31-44 |
| 描述 | 并发请求可能产生两条 is_active=1 记录 |
| 建议 | commit 前加 `db.flush()` 降低竞态窗口 |

---

## 四、轻微问题（P2 — 可择机优化）

### 4.1 缺少数据库索引

| 表 | 缺失索引列 | 影响 |
| ------ | ------ | ------ |
| focus_stock | is_active、stock_code | 无索引全表扫描 |
| trade_records | stock_code、traded_at | 数据量增长后变慢 |
| kline_cache | 仅有 stock_code | 已有唯一约束覆盖 |

建议：为高频查询列添加 `index=True`。

### 4.2 on_event startup 已弃用

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `main.py` L55-58 |
| 描述 | FastAPI 0.95+ 推荐 lifespan 替代 on_event |
| 建议 | 迁移到 lifespan 上下文管理器模式 |

### 4.3 stock_service 全局列表缓存无过期

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `stock_service.py` L35-37 |
| 描述 | 列表缓存为模块级全局变量，进程内不更新 |
| 风险 | 新上市标的在重启前搜索不到 |
| 建议 | 加入 TTL 机制 |

### 4.4 数据库 WAL 模式未启用

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `database.py` |
| 描述 | SQLite 默认 journal 模式，并发性能较差 |
| 建议 | 执行 `PRAGMA journal_mode=WAL` |

### 4.5 CORS 仅限开发地址

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `main.py` L42-43 |
| 描述 | allow_origins 硬编码为 localhost:5173 |
| 建议 | 从环境变量读取 |

### 4.6 httpx SSL 证书验证

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `data_fetcher.py` L30-31 |
| 描述 | 同花顺 API 禁用了 SSL 验证 |
| 风险 | 中间人攻击（个人项目可接受） |

### 4.7 K 线缓存无清理机制

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `stock_service.py` |
| 描述 | K 线缓存持续追加，无过期删除逻辑 |
| 建议 | 定期清理旧数据，或只保留最近 N 天 |

---

## 五、架构层面观察

### 5.1 数据流一致性

三层缓存（前端内存 → 后端 DB → 远程 API）
的 09:00 边界一致：

- `AgentCacheContext.last9am()` — 前端 Agent 缓存
- `useDataSource._last9amMs()` — 前端数据源缓存
- `agent_router._last_9am()` — 后端 Agent 缓存
- `data_source_service._last_9am()` — 后端数据源缓存

四处实现逻辑一致，时间边界对齐。

### 5.2 Agent 模板方法模式

`BaseAgent.execute()` → `fetch_data` →
`build_prompt` → `parse_response` → `fallback`

清晰的模板方法，新增 Agent 只需实现 4 个抽象方法。

### 5.3 前后端类型契约

前端 `types/index.ts` 与后端 `schemas.py`
字段定义基本一致，但缺少自动化校验手段。
建议后续引入 OpenAPI codegen 或定期对照。

### 5.4 数据源注册表模式

`_SOURCE_REGISTRY` 统一管理 12 类数据源，
新增数据源只需添加一行注册。

### 5.5 错误处理分层

- `data_fetcher`：独立 try-except，返回空 dict
- `BaseAgent.execute()`：catch all 后降级 fallback
- `agent_router`：线程内异常 catch 返回 error
- 前端：`.catch()` 展示友好错误消息

四层错误隔离确保单点故障不影响整体。

---

## 六、安全性检查

| 检查项 | 状态 | 说明 |
| ------ | ------ | ------ |
| SQL 注入 | 安全 | SQLAlchemy ORM 参数化查询 |
| API Key | 安全 | `.env` 读取，接口脱敏显示 |
| CORS | 限制 | 仅允许 localhost:5173 |
| 输入验证 | Pydantic | POST/PUT 使用 schema 验证 |
| XSS | React | 默认转义 HTML |
| 路径遍历 | 无风险 | 无文件上传/下载功能 |

---

## 七、性能观察

| 场景 | 当前表现 | 潜在瓶颈 |
| ------ | ------ | ------ |
| 首次 Agent | 约 10-30s | 同花顺 API 超时 |
| 缓存命中 | < 100ms | 无 |
| K 线加载 | 首次 1-3s | AKShare 偶尔不稳定 |
| 页面切换 | 即时 | 无 |
| 数据库增长 | 15-20 条/天/股 | 年度需定期清理 |

---

## 八、优先修复建议

| 优先级 | 问题 | 预计工作量 |
| ------ | ------ | ------ |
| P0 | SQLite Session 跨线程共享 | 1h |
| P0 | SectorAgent 降级签名不匹配 | 5min |
| P1 | LLM 重试无退避 | 10min |
| P1 | 数据源缓存双重查询 | 20min |
| P1 | 快照校验错误消息 | 5min |
| P1 | 删除交易未回滚持仓 | 30min |
| P1 | K 线更新遗漏 turnover | 5min |
| P2 | 数据库索引优化 | 15min |
| P2 | 前端缓存淘汰机制 | 30min |
