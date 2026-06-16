"""ReAct Mixin — 为 Agent 添加多轮推理能力（Thought → Action → Observation → Reflection）。

通过环境变量 REACT_ENABLED=true 启用。
关闭时退化为现有单轮 execute() 流程。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.agents.base_agent import AgentResult

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5  # 最多推理轮次


def is_react_enabled() -> bool:
    """检查 ReAct 模式是否启用。"""
    return os.getenv("REACT_ENABLED", "false").lower() == "true"


class ReactMixin:
    """ReAct 多轮推理混入类。

    为 BaseAgent 子类添加 execute_react() 方法，支持：
    - Thought: 分析当前信息是否充分
    - Action: 通过 MCP Client 调用 Tool 获取更多数据
    - Observation: 整合 Tool 返回结果
    - Reflection: 质量自检
    - Final Answer: 输出最终结构化结果
    """

    def execute_react(self, **kwargs: Any) -> AgentResult:
        """ReAct 循环执行。

        要求:
        - self.llm 可用
        - self.agent_name 已定义
        - kwargs 中包含 mcp_client（MCPToolClient 实例）
        """
        mcp_client = kwargs.get("mcp_client")
        if not mcp_client:
            logger.warning("ReAct 模式需要 mcp_client，退化为普通执行")
            return self.execute(**kwargs)  # type: ignore

        try:
            # 1. 获取基础数据
            raw_data = self.fetch_data(**kwargs)  # type: ignore

            # 2. 获取可用 Tool 列表
            tool_schemas = mcp_client.get_tool_schemas()
            tools_desc = self._format_tools_for_prompt(tool_schemas)

            # 3. ReAct 循环
            observations: list[dict] = []
            for iteration in range(MAX_ITERATIONS):
                messages = self._build_react_prompt(
                    raw_data, observations, tools_desc, **kwargs
                )
                response = self.llm.chat(messages, caller=f"{self.agent_name}_react")  # type: ignore

                step = self._parse_react_step(response)

                if step["type"] == "final_answer":
                    # 解析最终答案
                    try:
                        result_data = json.loads(step["content"])
                    except (json.JSONDecodeError, TypeError):
                        result_data = self.parse_response(  # type: ignore
                            {"summary": step.get("content", "")},
                            raw_data=raw_data, **kwargs,
                        )
                    return AgentResult(
                        agent_name=self.agent_name,  # type: ignore
                        status="success",
                        data=result_data,
                        llm_used=True,
                    )

                if step["type"] == "action":
                    # 调用 Tool
                    import asyncio
                    tool_result = asyncio.run(
                        mcp_client.call_tool(step["tool_name"], step.get("tool_args", {}))
                    )
                    observations.append({
                        "iteration": iteration + 1,
                        "thought": step.get("thought", ""),
                        "action": f"{step['tool_name']}({json.dumps(step.get('tool_args', {}), ensure_ascii=False)})",
                        "observation": json.dumps(tool_result, ensure_ascii=False)[:500],
                    })

                elif step["type"] == "reflection":
                    observations.append({
                        "iteration": iteration + 1,
                        "reflection": step.get("content", ""),
                    })

                else:
                    # 无法解析，强制结束
                    break

            # 超过最大轮次，使用标准流程兜底
            logger.info("ReAct 达到最大轮次 %d，使用标准流程输出", MAX_ITERATIONS)
            messages = self.build_prompt(raw_data=raw_data, **kwargs)  # type: ignore
            llm_output = self.llm.chat_json(messages, caller=self.agent_name)  # type: ignore
            parsed = self.parse_response(llm_output, raw_data=raw_data, **kwargs)  # type: ignore
            return AgentResult(
                agent_name=self.agent_name,  # type: ignore
                status="success",
                data=parsed,
                llm_used=True,
            )

        except Exception as e:
            logger.error("ReAct 执行失败: %s，回退标准流程", e)
            return self.execute(**kwargs)  # type: ignore

    def _build_react_prompt(
        self, raw_data: dict, observations: list[dict], tools_desc: str, **kwargs
    ) -> list[dict[str, str]]:
        """构建 ReAct Prompt。"""
        stock_name = kwargs.get("stock_name", "")
        stock_code = kwargs.get("stock_code", "")

        history = ""
        if observations:
            history = "\n\n已完成的推理步骤:\n"
            for obs in observations:
                if "reflection" in obs:
                    history += f"[轮次{obs['iteration']}] Reflection: {obs['reflection']}\n"
                else:
                    history += (
                        f"[轮次{obs['iteration']}] Thought: {obs.get('thought', '')}\n"
                        f"  Action: {obs.get('action', '')}\n"
                        f"  Observation: {obs.get('observation', '')}\n"
                    )

        data_summary = json.dumps(raw_data, ensure_ascii=False)[:1000]

        return [
            {
                "role": "system",
                "content": (
                    "你是一个使用 ReAct 模式的股票分析 Agent。\n"
                    "每一步你可以选择以下动作之一:\n"
                    "1. [ACTION] 调用工具获取更多数据\n"
                    "2. [REFLECTION] 自检当前分析质量\n"
                    "3. [FINAL_ANSWER] 给出最终结构化结果\n\n"
                    f"可用工具:\n{tools_desc}\n\n"
                    "输出格式要求:\n"
                    "Thought: <你的思考>\n"
                    "然后选择一个动作:\n"
                    "- Action: <tool_name> | Args: <json args>\n"
                    "- Reflection: <自检内容>\n"
                    "- Final Answer: <JSON 格式最终结果>\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"分析股票: {stock_name}({stock_code})\n\n"
                    f"已有基础数据:\n{data_summary}\n"
                    f"{history}\n"
                    "请继续下一步推理。如果信息已充分，直接给出 Final Answer。"
                ),
            },
        ]

    def _parse_react_step(self, response: str) -> dict:
        """解析 ReAct 响应。"""
        response = response.strip()

        # 检测 Final Answer
        if "Final Answer:" in response or "FINAL_ANSWER" in response:
            # 提取 Final Answer 后的内容
            for marker in ["Final Answer:", "FINAL_ANSWER:", "[FINAL_ANSWER]"]:
                if marker in response:
                    content = response.split(marker, 1)[1].strip()
                    return {"type": "final_answer", "content": content}

        # 检测 Action
        if "Action:" in response or "[ACTION]" in response:
            thought = ""
            if "Thought:" in response:
                thought = response.split("Thought:", 1)[1].split("\n")[0].strip()

            # 提取工具名和参数
            action_line = ""
            for line in response.split("\n"):
                if "Action:" in line:
                    action_line = line.split("Action:", 1)[1].strip()
                    break

            tool_name = action_line.split("|")[0].strip() if "|" in action_line else action_line.strip()
            tool_args = {}
            if "Args:" in action_line:
                try:
                    args_str = action_line.split("Args:", 1)[1].strip()
                    tool_args = json.loads(args_str)
                except (json.JSONDecodeError, IndexError):
                    pass

            return {
                "type": "action",
                "thought": thought,
                "tool_name": tool_name,
                "tool_args": tool_args,
            }

        # 检测 Reflection
        if "Reflection:" in response or "[REFLECTION]" in response:
            for marker in ["Reflection:", "[REFLECTION]"]:
                if marker in response:
                    content = response.split(marker, 1)[1].strip()
                    return {"type": "reflection", "content": content}

        # 无法识别，尝试作为 Final Answer
        return {"type": "final_answer", "content": response}

    def _format_tools_for_prompt(self, tool_schemas: list[dict]) -> str:
        """格式化 Tool 列表为 Prompt 可用的描述。"""
        if not tool_schemas:
            return "（无可用工具）"

        lines = []
        for t in tool_schemas[:15]:  # 限制数量避免 prompt 过长
            name = t.get("name", "")
            desc = t.get("description", "")[:80]
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)
