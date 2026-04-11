"""板块联动分析 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import sector_prompt
from app.services.data_fetcher import fetch_industry_board, fetch_concept_boards


class SectorAgent(BaseAgent):
    agent_name = "sector"

    def fetch_data(self, **kwargs: Any) -> dict:
        stock_name: str = kwargs.get("stock_name", "")
        industry = fetch_industry_board(stock_name)
        concepts = fetch_concept_boards()
        return {
            "industry": industry or {},
            "concepts": concepts or {},
        }

    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        return sector_prompt(
            stock_code=kwargs["stock_code"],
            stock_name=kwargs["stock_name"],
            sector_data=raw_data,
        )

    def parse_response(self, llm_output: dict, *, raw_data: dict, **kwargs: Any) -> dict:
        # 如果 LLM 返回的 top_peers 缺少 code，用原始数据补充
        llm_peers = llm_output.get("top_peers", [])
        raw_peers = raw_data.get("industry", {}).get("top_stocks", [])
        raw_map = {p.get("name", ""): p.get("code", "") for p in raw_peers}
        for p in llm_peers:
            if not p.get("code") and p.get("name") in raw_map:
                p["code"] = raw_map[p["name"]]

        return {
            "sector_name": llm_output.get("sector_name", ""),
            "sector_trend": llm_output.get("sector_trend", "震荡"),
            "relative_strength": llm_output.get("relative_strength", 0),
            "sector_rotation_signal": llm_output.get("sector_rotation_signal", "稳定"),
            "related_concepts": llm_output.get("related_concepts", []),
            "top_peers": llm_peers,
            "analysis": llm_output.get("analysis", ""),
        }

    def fallback(self, *, raw_data: dict, **kwargs: Any) -> dict:
        return {
            "sector_name": "未知",
            "sector_trend": "震荡",
            "relative_strength": 0,
            "sector_rotation_signal": "稳定",
            "related_concepts": [],
            "top_peers": [],
            "analysis": "AI 分析不可用，无法获取板块数据。",
        }
