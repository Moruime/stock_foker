"""个股数据 Tool 组 — 12 个 Tool。"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_stock_tools(mcp: FastMCP) -> None:
    """注册个股数据相关的 MCP Tool。"""

    @mcp.tool()
    def fetch_stock_finance(stock_name: str) -> dict:
        """获取个股财务指标（ROE/营业收入/净利润/毛利率/负债率/PE）。

        Args:
            stock_name: 股票名称，如"贵州茅台"
        """
        from app.services.data_fetcher import fetch_hithink_finance_data
        return fetch_hithink_finance_data(stock_name)

    @mcp.tool()
    def fetch_stock_insresearch(stock_name: str) -> dict:
        """获取机构研究评级和目标价（一致预期）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_insresearch_data
        return fetch_hithink_insresearch_data(stock_name)

    @mcp.tool()
    def fetch_stock_events(stock_name: str) -> dict:
        """获取个股近期重要事件（业绩预告为主，含预告类型/净利润/变动原因）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_events
        return fetch_hithink_events(stock_name)

    @mcp.tool()
    def fetch_stock_reports(stock_name: str) -> dict:
        """获取个股研究报告（券商研报）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_reports
        return fetch_hithink_reports(stock_name)

    @mcp.tool()
    def fetch_stock_business(stock_name: str) -> dict:
        """获取公司经营数据（主营构成/收入占比/主要客户/供应商）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_business_data
        return fetch_hithink_business_data(stock_name)

    @mcp.tool()
    def fetch_stock_basicinfo(stock_name: str) -> dict:
        """获取股票基本资料（行业分类/上市日期/总股本/流通股本/总市值）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_basicinfo
        return fetch_hithink_basicinfo(stock_name)

    @mcp.tool()
    def fetch_stock_shareholders(stock_name: str) -> dict:
        """获取股东信息（股东户数/户均持股/前十大股东/实控人）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_shareholders
        return fetch_hithink_shareholders(stock_name)

    @mcp.tool()
    def fetch_stock_news(stock_name: str) -> dict:
        """获取个股相关新闻（近期重大新闻公告事件）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_stock_news as _fetch
        return _fetch(stock_name)

    @mcp.tool()
    def fetch_stock_hithink_news(stock_name: str) -> dict:
        """获取个股财经资讯（通过综合搜索 API）。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_news
        return fetch_hithink_news(stock_name)

    @mcp.tool()
    def fetch_stock_announcements(stock_name: str) -> dict:
        """获取个股公告信息。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_hithink_announcements
        return fetch_hithink_announcements(stock_name)

    @mcp.tool()
    def fetch_stock_industry_board(stock_name: str) -> dict:
        """获取个股所属行业板块信息。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_industry_board
        return fetch_industry_board(stock_name)

    @mcp.tool()
    def fetch_stock_concept_boards(stock_name: str) -> dict:
        """获取个股所属概念板块详情（涨跌幅/成份股数量）。

        采用两步策略：先获取概念名称列表，再并行查询各概念板块详情。

        Args:
            stock_name: 股票名称
        """
        from app.services.data_fetcher import fetch_concept_boards
        return fetch_concept_boards(stock_name)
