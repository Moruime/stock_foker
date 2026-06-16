"""宏观经济数据 Tool 组 — 5 个 Tool。"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_macro_tools(mcp: FastMCP) -> None:
    """注册宏观数据相关的 MCP Tool。"""

    @mcp.tool()
    def fetch_macro_indicators() -> dict:
        """获取宏观经济关键指标（CPI/PPI/PMI/LPR/M2/社融）。

        用于判断当前宏观经济环境对股市的整体影响。
        优先使用同花顺问财 API，熔断时自动回退 AKShare。
        """
        from app.services.data_fetcher import fetch_hithink_macro_indicators
        return fetch_hithink_macro_indicators()

    @mcp.tool()
    def fetch_index_data() -> dict:
        """获取上证指数近期走势（最近5个交易日收盘价、涨跌幅、成交量）。

        用于判断大盘短期趋势。
        """
        from app.services.data_fetcher import fetch_index_data as _fetch
        return _fetch()

    @mcp.tool()
    def fetch_north_flow() -> dict:
        """获取沪深港通北向资金流向汇总。

        北向资金是市场重要风向标，净流入通常预示看好A股。
        数据源：AKShare / 东方财富。
        """
        from app.services.data_fetcher import fetch_north_flow as _fetch
        return _fetch()

    @mcp.tool()
    def fetch_market_overview() -> dict:
        """获取今日A股市场涨跌概况（上涨/下跌/涨停/跌停家数）。

        用于判断市场整体情绪温度。
        优先问财，回退 AKShare（乐股）。
        """
        from app.services.data_fetcher import fetch_market_overview as _fetch
        return _fetch()

    @mcp.tool()
    def fetch_main_index_data() -> dict:
        """获取主要指数最新行情（上证指数/沪深300/创业板指的收盘价、涨跌幅、成交额）。

        优先问财，回退 AKShare（新浪）。
        """
        from app.services.data_fetcher import fetch_hithink_index_data as _fetch
        return _fetch()
