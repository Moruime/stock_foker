# 交易记录与持仓联动

## 背景

当前交易记录（TradeRecord）和持仓信息（StockPosition）完全独立，新增交易记录不会影响持仓数据。用户需要：
1. **历史补录** — 补录过去的操作，不影响当前持仓
2. **实时交易** — 新增后自动同步到持仓（加权平均成本、数量增减）
3. 数据已持久化到 SQLite（`stock_foker.db`），无需额外处理

## 持仓同步规则

- **买入**：加权平均成本 `(原成本*原量 + 买价*买量) / (原量+买量)`，数量累加
- **卖出**：成本价不变，数量递减
- **清仓**：quantity=0，保留持仓记录（不删除）
- **无持仓时买入**：自动创建持仓
- **无持仓时卖出**：400 报错
- **卖出数量 > 持仓数量**：400 报错

## 修改文件清单（6个文件）

### 1. `backend/app/models/models.py` — 新增枚举和字段

- 新增 `RecordMode` 枚举：`BACKFILL = "backfill"`, `REALTIME = "realtime"`
- `TradeRecord` 新增 `record_mode` 列：`SAEnum(RecordMode)`, default=REALTIME, nullable=False

### 2. `backend/app/models/schemas.py` — Schema 扩展

- `TradeRecordCreate` 新增：`record_mode: RecordMode = RecordMode.REALTIME`（带默认值，向后兼容）
- `TradeRecordResponse` 新增：`record_mode: RecordMode`

### 3. `backend/app/routers/stock_router.py` — 核心逻辑（最大改动）

重构 `create_trade` 端点：

```
def create_trade(data, db):
    record = TradeRecord(**data.model_dump())
    db.add(record)

    if data.record_mode == "realtime":
        position = 查询持仓(data.stock_code)

        if buy:
            if position存在:
                新成本 = 加权平均(position, data)
                position.quantity += data.quantity
            else:
                创建新持仓(data.price, data.quantity, data.traded_at)

        if sell:
            if 无持仓: raise 400 "无持仓记录，无法卖出"
            if 卖出量 > 持仓量: raise 400 "卖出数量超过持仓数量"
            position.quantity -= data.quantity

    db.commit()  # 交易记录 + 持仓更新 原子提交
    return record
```

### 4. `frontend/src/types/index.ts` — 类型定义

- 新增 `type RecordMode = 'backfill' | 'realtime'`
- `TradeRecord` 新增 `record_mode: RecordMode`
- `TradeRecordCreate` 新增 `record_mode?: RecordMode`

### 5. `frontend/src/pages/TradesPage.tsx` — UI 改动

- 表单第一项新增「记录类型」Radio.Group：实时交易(默认) / 历史补录
- `handleCreate` 传递 `record_mode` 字段
- 实时交易成功后，递增 `positionKey` 触发 PositionCard 刷新
- catch 块增加 API 错误展示 `message.error(detail)`
- 交易记录列表中标识记录类型（实时/补录小标签）

### 6. 数据库迁移

已有 `trade_records` 表需执行：
```sql
ALTER TABLE trade_records ADD COLUMN record_mode VARCHAR(10) NOT NULL DEFAULT 'realtime';
```

## 实现顺序

1. 后端 models → schemas → router
2. 数据库迁移 SQL
3. curl 验证 API
4. 前端 types → TradesPage
5. TypeScript 检查 + 构建验证

## 验证方案

1. 实时买入（无持仓）→ 自动创建持仓，验证成本价和数量
2. 实时买入（有持仓）→ 验证加权平均成本计算
3. 实时卖出（部分）→ 验证数量减少、成本价不变
4. 实时卖出（清仓）→ 验证 quantity=0、记录保留
5. 实时卖出（无持仓）→ 验证 400 错误提示
6. 实时卖出（超量）→ 验证 400 错误提示
7. 历史补录 → 验证持仓不受影响
8. 前端 PositionCard 在实时交易后自动刷新
