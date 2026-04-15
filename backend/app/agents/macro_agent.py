"""宏观环境感知 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import macro_prompt
from app.services.data_fetcher import fetch_index_data


class MacroAgent(BaseAgent):
    agent_name = "macro"

    def fetch_data(self, **kwargs: Any) -> dict:
        stock_code: str = kwargs.get("stock_code", "")
        stock_name: str = kwargs.get("stock_name", "")
        db = kwargs.get("db")

        if db:
            from app.services.data_source_service import parallel_get_data_sources, get_data_source
            # 4 个全局数据源统一走缓存体系
            global_key = stock_code or "__GLOBAL__"
            cached = parallel_get_data_sources(
                db, global_key, stock_name,
                ["north_flow", "market_overview", "hithink_macro", "hithink_index"],
            )
            # index_data 不在缓存注册表，仍直接调用
            return {
                "index_data": fetch_index_data(),
                "north_flow": cached.get("north_flow", {}),
                "market_overview": cached.get("market_overview", {}),
                "hithink_macro": cached.get("hithink_macro", {}),
                "hithink_index": cached.get("hithink_index", {}),
            }

        # 无 db 时回退直接调用
        from app.services.data_fetcher import (
            fetch_north_flow, fetch_market_overview,
            fetch_hithink_macro_indicators, fetch_hithink_index_data, parallel_fetch,
        )
        base_results = parallel_fetch({
            "index_data": (fetch_index_data, ()),
            "north_flow": (fetch_north_flow, ()),
            "market_overview": (fetch_market_overview, ()),
            "hithink_macro": (fetch_hithink_macro_indicators, ()),
            "hithink_index": (fetch_hithink_index_data, ()),
        })
        return base_results

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
