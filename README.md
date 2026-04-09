# Stock Foker

个人 A 股分析辅助应用，集成 K 线行情、技术指标、AI 多维度分析与交易记录管理。

## 功能概览

### 行情分析

- 日/周/月 K 线蜡烛图（ECharts），支持缩放与联动
- MA5 / MA10 / MA20 / MA60 均线叠加
- MACD / KDJ / RSI / 布林带技术指标
- 多指标综合评分买卖建议（含完整推理过程）
- AI 增强版综合建议：四维度雷达图 + 信号/置信度/仓位建议

### AI Agent 分析

- **消息面情绪分析**：基于 AKShare 个股新闻的 LLM 情绪研判
- **板块联动分析**：行业/概念板块走势与成分股排名
- **宏观环境感知**：大盘走势 + 北向资金 + 市场情绪综合分析
- Agent 结果每日 9:00 更新，9:00 前旧数据仍可查看并有过期提示

### 历史记录

- 四类 Agent（消息面/板块/宏观/AI 综合）每日快照，支持历史回溯

### 交易管理

- 结构化买卖记录（类型/价格/数量/理由/情绪/目标价/持有周期）
- 交易结果补录（实际盈亏）
- 炒股画像：胜率/盈亏比/持仓偏好/情绪准确率统计
- 持仓管理：成本价/数量/止盈止损价，与交易记录双向同步

## 技术栈

| 端 | 技术 |
| --- | --- |
| 前端 | React 18 + Vite + TypeScript + Ant Design（暗色主题） |
| 后端 | Python FastAPI + SQLAlchemy + SQLite |
| AI | OpenAI 兼容 API（默认 qwen3-plus），支持热重载配置 |
| 数据源 | AKShare + 新浪财经（双数据源容灾 + SQLite 本地缓存） |

## 快速开始

### 前提条件

- Python 3.10+
- Node.js 18+

### 配置 LLM

复制 `.env.example` 并填写 LLM 配置：

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，必填项：

```ini
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

### 启动

```bash
./start.sh
```

脚本会自动完成：

- 创建 Python 虚拟环境并安装依赖
- 安装前端 npm 依赖
- 启动后端（端口 8000）和前端开发服务器（端口 5173）

启动后访问：

- 前端：<http://127.0.0.1:5173>
- 后端 API 文档：<http://127.0.0.1:8000/docs>

### 停止

```bash
./stop.sh
```

### 日志

```bash
tail -f logs/backend.log
tail -f logs/frontend.log
```

## 项目结构

```text
stock_foker/
├── backend/
│   ├── app/
│   │   ├── agents/       # LLM Agent（消息面/板块/宏观/综合建议）
│   │   ├── routers/      # API 路由
│   │   ├── services/     # 数据获取与业务逻辑
│   │   ├── models/       # 数据库模型与 Schema
│   │   └── llm/          # LLM 客户端与配置
│   ├── .env              # 本地配置（不入库）
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/        # 各功能页面
│       ├── components/   # 公共组件（K线图/快照面板等）
│       ├── contexts/     # React Context（Agent 缓存）
│       └── services/     # API 调用封装
├── doc/                  # 产品文档、迭代记录、待办列表
├── start.sh
└── stop.sh
```

## 数据说明

- K 线数据本地 SQLite 缓存，增量更新，命中后响应约 0.18s
- AI Agent 结果缓存至数据库，每天 09:00 后首次分析时刷新
- 所有数据本地存储，无需连接外部数据库

## 配色约定

遵循 A 股习惯：**红色 = 涨，绿色 = 跌**。
