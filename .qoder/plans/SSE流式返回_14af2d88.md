# SSE 流式返回

## 背景

当前 AI 综合分析流程：前端 POST -> 后端并行跑 3 个上游 Agent + 1 个增强建议 Agent -> 全部完成后一次性返回。整个过程 10-30s 无任何反馈，用户体验差。

## 设计方案

### SSE 事件流设计

后端通过 `text/event-stream` 逐步推送以下事件：

```
event: stage
data: {"stage": "cache_hit", "result": {...}}     // 命中缓存，直接返回完整结果

event: stage  
data: {"stage": "upstream_start", "agents": ["sentiment","sector","macro"]}

event: stage
data: {"stage": "sentiment_done", "result": {...}} // 情绪分析完成

event: stage
data: {"stage": "sector_done", "result": {...}}    // 板块分析完成

event: stage
data: {"stage": "macro_done", "result": {...}}     // 宏观分析完成

event: stage
data: {"stage": "enhanced_start"}                  // 开始综合分析

event: stage
data: {"stage": "complete", "result": {...}}       // 最终完整结果

event: error
data: {"message": "..."}                           // 异常
```

## Task 1: 后端 - 新增 SSE 端点

文件：`backend/app/routers/agent_router.py`

新增 `POST /api/agent/enhanced-analysis-stream` 端点，使用 FastAPI `StreamingResponse`：

```python
from fastapi.responses import StreamingResponse

@router.post("/enhanced-analysis-stream")
def run_enhanced_analysis_stream(req: AgentRunRequest, db: Session = Depends(get_db)):
    return StreamingResponse(
        _enhanced_analysis_generator(req, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

核心是将现有 `run_enhanced_analysis()` 的逻辑拆分为 generator 函数 `_enhanced_analysis_generator()`，在每个关键节点 yield SSE 事件。

关键实现细节：
- 缓存命中时直接 yield `cache_hit` 事件并 return
- 上游 Agent 并行执行，每完成一个就 yield 对应事件
- 使用 `queue.Queue` + `ThreadPoolExecutor` 收集并行结果
- 增强建议完成后 yield `complete` 事件
- 保留原有的 `POST /enhanced-analysis` 同步端点不变（缓存查询等仍需要）

## Task 2: 前端 - api.ts 新增 SSE 调用

文件：`frontend/src/services/api.ts`

新增 `streamEnhancedAnalysis()` 函数，使用 `fetch` + `ReadableStream` 消费 SSE：

```typescript
export function streamEnhancedAnalysis(
  stockCode: string,
  stockName: string,
  onEvent: (stage: string, data: Record<string, unknown>) => void,
): AbortController {
  const ctrl = new AbortController();
  fetch('/api/agent/enhanced-analysis-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stock_code: stockCode, stock_name: stockName }),
    signal: ctrl.signal,
  }).then(async (resp) => {
    const reader = resp.body!.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    // 逐行解析 SSE
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // 按双换行分割事件
      ...parse and call onEvent...
    }
  });
  return ctrl; // 支持取消
}
```

## Task 3: 前端 - AnalysisPage 流式 UI

文件：`frontend/src/pages/AnalysisPage.tsx`

改造 `handleAiAnalysis` 和 `handleAiRefresh`，使用流式调用替代一次性请求：

1. 新增状态：`aiStage` 跟踪当前阶段（如 "正在分析消息面..."、"正在分析板块..."）
2. 在 AI 卡片 loading 区域显示实时进度：
   - 每完成一个上游 Agent，显示对应的完成标记
   - 进入增强分析阶段时更新提示文案
3. 流完成后，复用现有的完整结果渲染逻辑

进度展示设计（在 `aiLoading` 期间替代当前的 Spin）：

```
[ok] 消息面分析   2.3s
[ok] 板块联动分析  3.1s  
[..] 宏观环境分析
[ ] AI 综合建议
```

使用 Ant Design `Steps` 或自定义列表实现，每个步骤完成时打勾并显示耗时。

## Task 4: 验证

- TypeScript 编译检查
- 后端导入验证
- 重启服务测试完整 SSE 流程
- 验证缓存命中时的快速返回路径
- 验证取消请求（切换股票时 abort）
