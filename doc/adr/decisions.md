# ADR-001: MCP Server 架构选型

## 状态

已采纳

## 背景

Stock Foker 的 20+ 数据查询函数硬编码在 `data_fetcher.py`，Agent 通过静态 import 调用。需要解耦 Tool 与 Agent，支持动态发现和热插拔扩展。

## 决策

采用 MCP (Model Context Protocol) 标准协议：

- **传输**: stdio（单机零网络开销）
- **SDK**: `mcp[cli]` 官方 Python SDK 的 FastMCP
- **兼容策略**: 环境变量 `MCP_ENABLED=true` 控制，关闭时 fallback 到直接 import

## 理由

1. MCP 是 2024 年 Anthropic 发布的开放协议，已成为 Agent-Tool 交互的事实标准
2. stdio 传输适合单机部署，零运维成本
3. FastMCP 基于 type hints + docstring 自动生成 Tool schema，开发体验好
4. 保留 fallback 路径确保生产稳定性

## 后果

- 正面：Agent 与 Tool 完全解耦，支持 MCP Inspector 调试，面试亮点
- 负面：多进程通信增加少量延迟（~10ms），需维护 fallback 映射表

---

# ADR-002: Memory 系统存储选型

## 状态

已采纳

## 决策

- **短期记忆**: SQLite 表 + 轮次粒度滑动窗口
- **长期记忆**: SQLite + 关键词检索（预留 sqlite-vec 向量检索）
- **嵌入模型**: DashScope text-embedding-v3（备用）

## 理由

1. sqlite-vec 是 SQLite 扩展，与现有 WAL 模式 DB 无缝兼容
2. 千级别记忆量下，关键词匹配已满足需求
3. 避免引入 ChromaDB 等独立进程

---

# ADR-003: 回测引擎数据源

## 状态

已采纳

## 决策

使用已有 `DailyAgentSnapshot` 表中的历史快照作为信号源，不重跑历史 Agent。

## 理由

1. 零 LLM 成本（不消耗 token）
2. 数据真实（是历史实际推荐）
3. 增量积累：每天自动新增快照

## 约束

- 需要 ≥20 个交易日数据才计算夏普比率
- 早期数据不足时前端展示"数据积累中"

---

# ADR-004: ReAct 实现策略

## 状态

已采纳

## 决策

使用 Mixin 模式实现 ReAct，通过 `REACT_ENABLED=true` 环境变量启用。

## 理由

1. 不破坏现有 Template Method 继承体系
2. 可选启用，生产环境默认关闭避免 token 消耗爆炸
3. MAX_ITERATIONS=5 硬限制 + TokenBudget 实时检查防止失控
