# 简历亮点 (Resume Highlights)

完成 Stock Foker 深度改造后，可用于简历/面试的描述：

---

## MCP Server (P0-1)

> 独立设计并实现标准 MCP (Model Context Protocol) Server，将 21 个金融数据查询函数封装为可动态发现的 Tool；Agent 通过 MCP Client 协议调用，支持热插拔扩展与零感知降级（Server 不可用时自动 fallback 到进程内直接调用）。

---

## Memory System (P0-2)

> 实现分层 Memory 系统：滑动窗口 + LLM 摘要压缩的短期记忆管理对话上下文；SQLite 持久化的长期记忆存储用户投资偏好与历史洞察，推理时通过关键词检索自动注入相关记忆到 Agent Prompt，提升个性化建议准确度。

---

## 量化回测 (P0-3)

> 构建历史数据回测引擎，基于 Agent 每日快照信号与实际 K 线行情模拟交易，输出胜率、夏普比率、最大回撤等量化指标；回测结果 API 化并可视化，验证 AI 推荐的实际效果。

---

## ReAct Pattern (P1-1)

> EnhancedAdviceAgent 支持 ReAct 多轮推理循环（Thought → Action → Observation → Reflection），根据初步分析结果动态决定是否调用更多 MCP Tool 补充数据，具备自检反思能力，最多 5 轮迭代后收敛输出。

---

## Token 成本监控 (P1-2)

> 全链路 Token 成本追踪：每次 LLM 调用自动记录 input/output token、耗时与成本；实现三级自动降级策略（80% 预算降低 token → 95% 跳过非核心 Agent → 100% 全 fallback），日均成本可控。
