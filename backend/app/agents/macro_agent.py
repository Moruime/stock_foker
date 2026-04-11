"""宏观环境感知 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import macro_prompt
from app.services.data_fetcher import fetch_index_data, fetch_north_flow, fetch_market_overview, fetch_hithink_macro_indicators, fetch_hithink_index_data, parallel_fetch


class MacroAgent(BaseAgent):
    agent_name = "macro"

    def fetch_data(self, **kwargs: Any) -> dict:
        stock_code: str = kwargs.get("stock_code", "")
        stock_name: str = kwargs.get("stock_name", "")
        db = kwargs.get("db")

        # 非缓存数据源
        base_results = parallel_fetch({
            "index_data": (fetch_index_data, ()),
            "north_flow": (fetch_north_flow, ()),
            "market_overview": (fetch_market_overview, ()),
            "hithink_macro": (fetch_hithink_macro_indicators, ()),
        })
        base_results.setdefault("index_data", {})
        base_results.setdefault("north_flow", {})
        base_results.setdefault("market_overview", {})

        # 使用数据源缓存服务获取指数行情
        if db:
            from app.services.data_source_service import get_data_source
            # hithink_index 不依赖 stock_code，但用 stock_code 作为缓存 key
            hithink_index, _, _ = get_data_source(db, stock_code or "__GLOBAL__", stock_name, "hithink_index")
        else:
            hithink_index = fetch_hithink_index_data()

        return {
            **base_results,
            "hithink_index": hithink_index,
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
