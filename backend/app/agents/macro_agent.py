"""宏观环境感知 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import macro_prompt
from app.services.data_fetcher import fetch_index_data, fetch_north_flow, fetch_market_overview, fetch_hithink_macro_indicators


class MacroAgent(BaseAgent):
    agent_name = "macro"

    def fetch_data(self, **kwargs: Any) -> dict:
        index_data = fetch_index_data()
        north_flow = fetch_north_flow()
        market_overview = fetch_market_overview()
        hithink_macro = fetch_hithink_macro_indicators()
        return {
            "index_data": index_data or {},
            "north_flow": north_flow or {},
            "market_overview": market_overview or {},
            "hithink_macro": hithink_macro,
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
        indicators = []
        # 从问财返回的原始数据中提取概要信息
        for key, label in [("index_data", "上证指数"), ("north_flow", "北向资金"), ("market_overview", "市场概况")]:
            data = raw_data.get(key, {})
            if data and data.get("datas"):
                indicators.append({
                    "name": label,
                    "value": "已获取",
                    "interpretation": "详见原始数据",
                })

        return {
            "market_phase": "震荡市",
            "market_sentiment": 0,
            "key_indicators": indicators,
            "risk_level": "中",
            "impact_on_stock": "",
            "analysis": "AI 分析不可用，展示原始宏观数据。",
        }
