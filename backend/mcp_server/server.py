"""MCP Server 入口 — 注册所有 Tool 并启动 stdio 传输。

启动方式:
    python -m mcp_server.server
"""

from __future__ import annotations

import sys
import os

# 将 backend 目录加入 Python path，以便复用 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from mcp.server.fastmcp import FastMCP

# 创建 MCP Server 实例
mcp = FastMCP(
    "stock-foker-data",
    instructions="Stock Foker 金融数据 MCP Server，提供宏观经济、个股基本面、市场行情等 20+ 数据查询工具。",
)

# 注册各 Tool 分组
from mcp_server.tools.macro_tools import register_macro_tools
from mcp_server.tools.stock_tools import register_stock_tools
from mcp_server.tools.market_tools import register_market_tools

register_macro_tools(mcp)
register_stock_tools(mcp)
register_market_tools(mcp)


def main():
    """MCP Server 入口点。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
