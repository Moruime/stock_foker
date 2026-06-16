"""MCP Tool Client — 连接 MCP Server，动态发现并调用 Tool。

通过 MCP_ENABLED=true 环境变量启用。
连接失败时自动 fallback 到直接 import data_fetcher。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

# MCP Server 脚本路径
_SERVER_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "mcp_server", "server.py",
)


def is_mcp_enabled() -> bool:
    """检查 MCP 模式是否启用。"""
    return os.getenv("MCP_ENABLED", "false").lower() == "true"


class MCPToolClient:
    """MCP Tool 统一调用客户端。

    使用 stdio 传输连接本地 MCP Server，支持：
    - 动态发现可用 Tool
    - 按名称调用 Tool
    - 连接失败时 fallback 到直接 import
    """

    def __init__(self) -> None:
        self._session = None
        self._tools: list[dict] = []
        self._connected = False
        self._read = None
        self._write = None

    async def connect(self) -> bool:
        """连接 MCP Server（stdio 传输）。"""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=sys.executable,
                args=[_SERVER_SCRIPT],
                env={**os.environ},
            )

            self._transport = stdio_client(server_params)
            self._read, self._write = await self._transport.__aenter__()
            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()
            await self._session.initialize()

            # 缓存 Tool 列表
            result = await self._session.list_tools()
            self._tools = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in result.tools
            ]
            self._connected = True
            logger.info("MCP Client 已连接，发现 %d 个 Tool", len(self._tools))
            return True

        except Exception as e:
            logger.warning("MCP Client 连接失败: %s，将使用 fallback 模式", e)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """断开连接。"""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
        if hasattr(self, "_transport") and self._transport:
            try:
                await self._transport.__aexit__(None, None, None)
            except Exception:
                pass
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def get_tool_schemas(self) -> list[dict]:
        """返回所有 Tool 的 schema（供 ReAct LLM function calling 使用）。"""
        return self._tools

    def get_tool_names(self) -> list[str]:
        """返回所有 Tool 名称列表。"""
        return [t["name"] for t in self._tools]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict:
        """调用指定 Tool。

        Args:
            name: Tool 名称
            arguments: Tool 参数字典

        Returns:
            Tool 返回的结果字典

        Raises:
            如果 MCP 调用失败，尝试 fallback 到直接调用。
        """
        if not self._connected or not self._session:
            return await self._fallback_call(name, arguments or {})

        try:
            result = await self._session.call_tool(name, arguments or {})
            # MCP Tool 返回的 content 是 list[TextContent]
            if result.content and len(result.content) > 0:
                text = result.content[0].text
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw": text}
            return {}
        except Exception as e:
            logger.warning("MCP Tool '%s' 调用失败: %s，尝试 fallback", name, e)
            return await self._fallback_call(name, arguments or {})

    async def _fallback_call(self, name: str, arguments: dict) -> dict:
        """Fallback: 直接 import 调用 data_fetcher 中的对应函数。"""
        from app.services.data_fetcher import (
            fetch_hithink_macro_indicators,
            fetch_index_data,
            fetch_north_flow,
            fetch_market_overview,
            fetch_hithink_index_data,
            fetch_hithink_finance_data,
            fetch_hithink_insresearch_data,
            fetch_hithink_events,
            fetch_hithink_reports,
            fetch_hithink_business_data,
            fetch_hithink_basicinfo,
            fetch_hithink_shareholders,
            fetch_stock_news,
            fetch_hithink_news,
            fetch_hithink_announcements,
            fetch_industry_board,
            fetch_concept_boards,
            fetch_hithink_industry_data,
            fetch_hithink_market_data,
            fetch_hithink_industry_finance,
            fetch_hithink_industry_peers,
        )

        # Tool 名称到函数的映射
        _TOOL_MAP = {
            "fetch_macro_indicators": (fetch_hithink_macro_indicators, []),
            "fetch_index_data": (fetch_index_data, []),
            "fetch_north_flow": (fetch_north_flow, []),
            "fetch_market_overview": (fetch_market_overview, []),
            "fetch_main_index_data": (fetch_hithink_index_data, []),
            "fetch_stock_finance": (fetch_hithink_finance_data, ["stock_name"]),
            "fetch_stock_insresearch": (fetch_hithink_insresearch_data, ["stock_name"]),
            "fetch_stock_events": (fetch_hithink_events, ["stock_name"]),
            "fetch_stock_reports": (fetch_hithink_reports, ["stock_name"]),
            "fetch_stock_business": (fetch_hithink_business_data, ["stock_name"]),
            "fetch_stock_basicinfo": (fetch_hithink_basicinfo, ["stock_name"]),
            "fetch_stock_shareholders": (fetch_hithink_shareholders, ["stock_name"]),
            "fetch_stock_news": (fetch_stock_news, ["stock_name"]),
            "fetch_stock_hithink_news": (fetch_hithink_news, ["stock_name"]),
            "fetch_stock_announcements": (fetch_hithink_announcements, ["stock_name"]),
            "fetch_stock_industry_board": (fetch_industry_board, ["stock_name"]),
            "fetch_stock_concept_boards": (fetch_concept_boards, ["stock_name"]),
            "fetch_industry_valuation": (fetch_hithink_industry_data, ["stock_name"]),
            "fetch_market_fund_flow": (fetch_hithink_market_data, ["stock_name"]),
            "fetch_industry_finance": (fetch_hithink_industry_finance, ["stock_name"]),
            "fetch_industry_peers": (fetch_hithink_industry_peers, ["stock_name"]),
        }

        if name not in _TOOL_MAP:
            logger.warning("未知 Tool: %s", name)
            return {}

        fn, arg_names = _TOOL_MAP[name]
        args = [arguments.get(a, "") for a in arg_names]
        try:
            return fn(*args) or {}
        except Exception as e:
            logger.warning("Fallback 调用 '%s' 失败: %s", name, e)
            return {}


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_client: MCPToolClient | None = None


def get_mcp_client() -> MCPToolClient | None:
    """获取 MCP Client 单例（未启用时返回 None）。"""
    global _client
    if not is_mcp_enabled():
        return None
    if _client is None:
        _client = MCPToolClient()
    return _client


async def ensure_mcp_connected() -> MCPToolClient | None:
    """确保 MCP Client 已连接（用于 lifespan 初始化）。"""
    client = get_mcp_client()
    if client and not client.connected:
        await client.connect()
    return client
