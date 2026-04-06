"""宏观环境感知 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import macro_prompt
from app.services.data_fetcher import fetch_index_data, fetch_north_flow, fetch_market_overview


class MacroAgent(BaseAgent):
    agent_name = "macro"

    def fetch_data(self, **kwargs: Any) -> dict:
        index_data = fetch_index_data()
        north_flow = fetch_north_flow()
        market_overview = fetch_market_overview()
        return {
            "index_data": index_data or {},
            "north_flow": north_flow or {},
            "market_overview": market_overview or {},
        }

    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        return macro_prompt(
            macro_data=raw_data,
            stock_code=kwargs.get("stock_code"),
            stock_name=kwargs.get("stock_name"),
        )

    def parse_response(self, llm_output: dict, *, raw_data: dict, **kwargs: Any) -> dict:
        return {
            "market_phase": llm_output.get("market_phase", "震荡市"),
            "market_sentiment": llm_output.get("market_sentiment", 0),
            "key_indicators": llm_output.get("key_indicators", []),
            "risk_level": llm_output.get("risk_level", "中"),
            "impact_on_stock": llm_output.get("impact_on_stock", ""),
            "analysis": llm_output.get("analysis", ""),
        }

    def fallback(self, *, raw_data: dict, **kwargs: Any) -> dict:
        index_data = raw_data.get("index_data", {})
        north_flow = raw_data.get("north_flow", {})
        market = raw_data.get("market_overview", {})

        indicators = []
        if index_data.get("change_pct") is not None:
            indicators.append({
                "name": "上证指数涨跌",
                "value": f"{index_data['change_pct']:.2f}%",
                "interpretation": "近期走势",
            })
        if north_flow.get("net_flow") is not None:
            indicators.append({
                "name": "北向资金净流入",
                "value": f"{north_flow['net_flow']:.2f}亿",
                "interpretation": "外资动向",
            })
        if market.get("up_count") is not None:
            indicators.append({
                "name": "涨跌家数",
                "value": f"涨{market['up_count']}/跌{market['down_count']}",
                "interpretation": "市场广度",
            })

        return {
            "market_phase": "震荡市",
            "market_sentiment": 0,
            "key_indicators": indicators,
            "risk_level": "中",
            "impact_on_stock": "",
            "analysis": "AI 分析不可用，展示原始宏观数据。",
        }
