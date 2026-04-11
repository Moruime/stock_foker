# Stock Foker 第一期代码审查 — 修复报告

> 修复日期：2026-04-11
> 对应审查报告：`2026-04-11-phase1-architecture-review.md`

## 修复总览

| 级别 | 总数 | 已修复 | 跳过 |
| ------ | ------ | ------ | ------ |
| P0（严重） | 2 | 2 | 0 |
| P1（中等） | 7 | 7 | 0 |
| P2（轻微） | 7 | 6 | 1 |

跳过说明：P2 4.6（httpx SSL 验证）为同花顺 API 的已知限制，个人项目可接受，暂不修改。

---

## 一、P0 严重问题修复

### 1.1 SQLite Session 跨线程共享（对应审查 2.1）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/routers/agent_router.py` |
| 修复方式 | 新增 `_run_agent_in_thread()`，子线程创建独立 Session，用完关闭 |

```python
def _run_agent_in_thread(agent, **kwargs) -> dict:
    """在独立线程中执行 Agent（创建独立 DB Session 避免跨线程共享）。"""
    thread_db = SessionLocal()
    try:
        kwargs["db"] = thread_db
        return agent.execute(**kwargs).to_dict()
    finally:
        thread_db.close()
```

### 1.2 SectorAgent 降级路径签名不匹配（对应审查 2.2）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/agents/sector_agent.py` |
| 修复方式 | `else` 分支调用改为 `fetch_concept_boards(stock_name)` |

---

## 二、P1 中等问题修复

### 2.1 LLM 重试无退避间隔（对应审查 3.1）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/llm/client.py` |
| 修复方式 | 在重试循环的 except 块末尾添加指数退避 |

```python
if attempt < 2:
    time.sleep(2 ** attempt)  # 指数退避: 1s, 2s
```

### 2.2 数据源缓存双重查询（对应审查 3.2）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/services/data_source_service.py` |
| 修复方式 | `_get_cached_source` 返回 `(data, created_at)` 元组，避免二次查询 |

### 2.3 快照校验错误消息不完整（对应审查 3.3）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/routers/snapshot_router.py` |
| 修复方式 | 错误消息改为动态拼接 `_VALID_AGENT_TYPES` |

### 2.4 删除交易记录未回滚持仓（对应审查 3.4）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/routers/stock_router.py` |
| 修复方式 | `delete_trade` 中对 realtime 记录反向调整持仓 |

修复逻辑：

- 删除**买入**记录 → 减少持仓数量，重新计算成本价；数量归零则删除持仓
- 删除**卖出**记录 → 恢复持仓数量

### 2.5 K 线缓存盘中更新遗漏 turnover（对应审查 3.5）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/services/stock_service.py` |
| 修复方式 | `.update()` 补充 turnover 字段 |

### 2.6 前端内存缓存无上限（对应审查 3.6）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `AgentCacheContext.tsx` + `useDataSource.ts` |
| 修复方式 | 两处缓存均添加基于数量的淘汰机制 |

- Agent 缓存：`MAX_STOCKS = 20`（每股 4 条缓存 = 上限 80 条），超限后按 `cachedAt` 淘汰最旧 4 条
- 数据源缓存：`MAX_DS_ENTRIES = 240`（约 20 股 × 12 类数据源），超限后淘汰最旧 12 条

### 2.7 FocusStock 并发设置竞态（对应审查 3.7）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/routers/stock_router.py` |
| 修复方式 | `set_focus_stock` 中 update 后添加 `db.flush()`，确保旧记录落盘后再插入新记录，降低竞态窗口 |

---

## 三、P2 轻微问题修复

### 3.1 缺少数据库索引（对应审查 4.1）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/models/models.py` |
| 修复方式 | 添加 `index=True` |

新增索引列：

- `FocusStock.stock_code`
- `FocusStock.is_active`
- `TradeRecord.stock_code`

### 3.2 `@app.on_event("startup")` 已弃用（对应审查 4.2）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/main.py` |
| 修复方式 | 迁移到 lifespan 上下文管理器模式 |

### 3.3 stock_service 全局列表缓存无过期（对应审查 4.3）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/services/stock_service.py` |
| 修复方式 | 新增 `_cache_ts` 时间戳字典和 `_cache_expired()` 函数，TTL 设为 4 小时 |

```python
_CACHE_TTL: float = 4 * 3600

def _cache_expired(key: str) -> bool:
    ts = _cache_ts.get(key)
    return ts is None or (time.time() - ts) > _CACHE_TTL
```

### 3.4 数据库 WAL 模式未启用（对应审查 4.4）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/db/database.py` |
| 修复方式 | 通过 SQLAlchemy event listener 在连接建立时执行 `PRAGMA journal_mode=WAL` |

### 3.5 CORS 仅限开发地址（对应审查 4.5）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/main.py` |
| 修复方式 | 从环境变量 `CORS_ORIGINS` 读取，默认 localhost |

### 3.6 K 线缓存无清理机制（对应审查 4.7）

| 项目 | 说明 |
| ------ | ------ |
| 文件 | `backend/app/services/stock_service.py` |
| 修复方式 | 在 `_get_kline_with_cache` 写入新数据时，顺带删除 400 天前的旧缓存记录 |

### 3.7 httpx SSL 证书验证（对应审查 4.6）— 跳过

同花顺 API 的 SSL 证书链不完整，禁用验证为已知且必要的妥协。个人项目风险可接受，暂不修改。

---

## 四、变更文件汇总

| 文件 | 修复项 |
| ------ | ------ |
| `backend/app/routers/agent_router.py` | P0-1 |
| `backend/app/agents/sector_agent.py` | P0-2 |
| `backend/app/llm/client.py` | P1-1 |
| `backend/app/services/data_source_service.py` | P1-2 |
| `backend/app/routers/snapshot_router.py` | P1-3 |
| `backend/app/routers/stock_router.py` | P1-4, P1-7 |
| `backend/app/services/stock_service.py` | P1-5, P2-3, P2-6 |
| `frontend/src/contexts/AgentCacheContext.tsx` | P1-6 |
| `frontend/src/hooks/useDataSource.ts` | P1-6 |
| `backend/app/models/models.py` | P2-1 |
| `backend/app/main.py` | P2-2, P2-5 |
| `backend/app/db/database.py` | P2-4 |

## 五、验证结果

| 验证项 | 结果 |
| ------ | ------ |
| 后端导入 `from app.main import app` | 通过 |
| 前端类型检查 `npx tsc --noEmit` | 通过 |
