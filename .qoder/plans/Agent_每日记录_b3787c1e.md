# Agent 每日记录

## 数据字段设计

每种 Agent 仅抽取核心指标（不含新闻列表、成分股表格等大体量数据）：

| Agent | 快照字段 |
|---|---|
| sentiment | overall_sentiment, sentiment_label, raw_news_count, noise_ratio, analysis |
| sector | sector_name, sector_trend, relative_strength, sector_rotation_signal, analysis |
| macro | market_phase, market_sentiment, risk_level, impact_on_stock, analysis |

---

## Task 1: 后端 - 新增数据库模型

**文件**: `backend/app/models/models.py`

```python
class DailyAgentSnapshot(Base):
    __tablename__ = "daily_agent_snapshot"
    __table_args__ = (
        UniqueConstraint("agent_type", "stock_code", "date", name="uq_snapshot"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_type  = Column(String(20), nullable=False, index=True)  # sentiment|sector|macro
    stock_code  = Column(String(10), nullable=False, index=True)
    date        = Column(String(10), nullable=False)   # YYYY-MM-DD
    snapshot_data = Column(Text, nullable=False)       # JSON 关键指标
    llm_used    = Column(Integer, default=0)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## Task 2: 后端 - Pydantic Schema

**文件**: `backend/app/models/schemas.py`，新增：

```python
class SnapshotResponse(BaseModel):
    id: int
    agent_type: str
    stock_code: str
    date: str
    snapshot_data: dict[str, Any]
    llm_used: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
```

---

## Task 3: 后端 - Snapshot Router

**新建文件**: `backend/app/routers/snapshot_router.py`

两个端点：

```
GET /api/snapshots/{agent_type}/dates?stock_code=xxx
  → 返回该股票 + agent 类型下所有有记录的日期列表（降序）

GET /api/snapshots/{agent_type}/{date}?stock_code=xxx
  → 返回指定日期的快照详情
```

---

## Task 4: 后端 - 自动保存钩子

**文件**: `backend/app/routers/agent_router.py`

新增快照提取函数与保存逻辑，在 `_save_cache()` 之后调用（只保存 sentiment/sector/macro，不保存 enhanced_advice）：

```python
_SNAPSHOT_FIELDS = {
    "sentiment": ["overall_sentiment", "sentiment_label", "raw_news_count", "noise_ratio", "analysis"],
    "sector":    ["sector_name", "sector_trend", "relative_strength", "sector_rotation_signal", "analysis"],
    "macro":     ["market_phase", "market_sentiment", "risk_level", "impact_on_stock", "analysis"],
}

def _save_snapshot(db, result, stock_code):
    agent_name = result["agent_name"]
    if agent_name not in _SNAPSHOT_FIELDS:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    data = {k: result["data"].get(k) for k in _SNAPSHOT_FIELDS[agent_name]}
    # upsert: 存在则更新，不存在则插入
    ...
```

---

## Task 5: 后端 - 注册路由

**文件**: `backend/app/main.py`，添加：

```python
from app.routers.snapshot_router import router as snapshot_router
app.include_router(snapshot_router)
```

---

## Task 6: 前端 - 类型定义

**文件**: `frontend/src/types/index.ts`，新增：

```typescript
export interface AgentSnapshot {
  id: number;
  agent_type: string;
  stock_code: string;
  date: string;
  snapshot_data: Record<string, unknown>;
  llm_used: boolean;
  created_at: string;
  updated_at: string;
}
```

---

## Task 7: 前端 - API 函数

**文件**: `frontend/src/services/api.ts`，新增：

```typescript
export const getSnapshotDates = (agentType: string, stockCode: string) => ...
export const getSnapshotDetail = (agentType: string, date: string, stockCode: string) => ...
```

---

## Task 8: 前端 - 共用 SnapshotPanel 组件

**新建文件**: `frontend/src/components/SnapshotPanel.tsx`

Props: `{ agentType: 'sentiment' | 'sector' | 'macro', stockCode: string }`

布局：两栏
- 左栏：可用日期列表（最近 90 天内有记录的日期），点击高亮选中
- 右栏：所选日期的快照字段展示
  - sentiment: 情绪图标 + 分值 + 新闻量/噪音比 + 分析摘要
  - sector: 板块名/趋势 tag + 相对强度 + 轮动信号 + 分析摘要
  - macro: 市场阶段 + 情绪 + 风险等级（颜色） + 分析摘要

当无记录时显示"暂无历史记录，运行 Agent 后自动保存"。

---

## Task 9: 前端 - 嵌入三个页面

在 `SentimentPage` / `SectorPage` / `MacroPage` 各页面底部追加：

```tsx
{focus && (
  <SnapshotPanel agentType="sentiment" stockCode={focus.stock_code} />
)}
```

---

## 数据流

```
用户访问页面
  → useEffect fetchData()
    → 后端 /api/agent/sentiment
      → _save_cache()          ← 已有缓存逻辑
      → _save_snapshot()       ← 新增：抽取关键指标写入 daily_agent_snapshot
      → 返回结果
  → SnapshotPanel 加载日期列表
    → GET /api/snapshots/sentiment/dates?stock_code=xxx
  → 用户点击日期
    → GET /api/snapshots/sentiment/2026-04-09?stock_code=xxx
```

