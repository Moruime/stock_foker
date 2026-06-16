"""市场数据 Tool 组 — 4 个 Tool。"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_market_tools(mcp: FastMCP) -> None:
    """注册市场/行业数据相关的 MCP Tool。"""

    @mcp.tool()
    def fetch_industry_valuation(stock_name: str) -> dict:
        """获取个股所属行业估值/盈利数据（PE/PB/ROE/行业涨跌幅排名）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_industry_data
        return fetch_hithink_industry_data(stock_name)

    @mcp.tool()
    def fetch_market_fund_flow(stock_name: str) -> dict:
        """获取个股/板块主力资金流向数据（净流入/大单净量/换手率/量比）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_market_data
        return fetch_hithink_market_data(stock_name)

    @mcp.tool()
    def fetch_industry_finance(stock_name: str) -> dict:
        """获取个股所属行业财务概况（营收增速/净利润增速/毛利率/行业排名）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_industry_finance
        return fetch_hithink_industry_finance(stock_name)

    @mcp.tool()
    def fetch_industry_peers(stock_name: str) -> dict:
        """获取个股所属行业市值龙头（涨跌幅/市盈率/总市值/主力资金流向）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_industry_peers
        return fetch_hithink_industry_peers(stock_name)
