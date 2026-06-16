"""MCP Server 熔断器中间件 — 复用 data_fetcher 的熔断逻辑。

MCP Server 运行在同一进程中，直接使用 data_fetcher 模块级的熔断状态。
此模块提供额外的 MCP Tool 用于暴露和管理熔断状态。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_circuit_breaker_tools(mcp: FastMCP) -> None:
    """注册熔断管理 Tool（可选）。"""

    @mcp.tool()
    def get_api_status() -> dict:
        """获取问财 API 当前熔断状态。

        返回 API 是否可用、熔断原因等信息。
        """
        from app.services.data_fetcher import get_iwencai_status
        return get_iwencai_status()

    @mcp.tool()
    def reset_api_circuit() -> dict:
        """重置问财 API 熔断状态（用于 API Key 更换后）。"""
        from app.services.data_fetcher import reset_iwencai_circuit, get_iwencai_status
        reset_iwencai_circuit()
        return get_iwencai_status()
