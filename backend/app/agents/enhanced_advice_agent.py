"""增强版买卖建议 Agent — 链路终结点，融合四个维度。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import enhanced_advice_prompt


class EnhancedAdviceAgent(BaseAgent):
    agent_name = "enhanced_advice"

    def fetch_data(self, **kwargs: Any) -> dict:
        """从 kwargs 获取上游数据（由 router 层预先准备）。"""
        from app.services.advice_service import generate_advice
        from app.services.profile_service import generate_profile
        from app.services.data_fetcher import fetch_hithink_finance_data, fetch_hithink_insresearch_data

        db = kwargs.get("db")
        stock_code = kwargs["stock_code"]
        stock_name = kwargs.get("stock_name", "")
        kline = kwargs.get("kline", [])
        indicators = kwargs.get("indicators", {})

        technical_advice = generate_advice(indicators, kline)
        profile = generate_profile(db, stock_code) if db else {}

        # 持仓信息
        position = None
        if db:
            from app.models.models import StockPosition

            pos = db.query(StockPosition).filter(
                StockPosition.stock_code == stock_code
            ).first()
            if pos:
                position = {
                    "cost_price": pos.cost_price,
                    "quantity": pos.quantity,
                    "take_profit_price": pos.take_profit_price,
                    "stop_loss_price": pos.stop_loss_price,
                }

        # 基本面数据（同花顺）
        fundamental_data = fetch_hithink_finance_data(stock_name)
        insresearch_data = fetch_hithink_insresearch_data(stock_name)

        return {
            "technical_advice": technical_advice,
            "profile": profile,
            "position": position,
            "fundamental_data": fundamental_data,
            "insresearch_data": insresearch_data,
        }

    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        return enhanced_advice_prompt(
            stock_code=kwargs["stock_code"],
            stock_name=kwargs["stock_name"],
            technical_advice=raw_data["technical_advice"],
            sentiment_result=kwargs.get("sentiment_result", {}),
            sector_result=kwargs.get("sector_result", {}),
            macro_result=kwargs.get("macro_result", {}),
            profile=raw_data["profile"],
            position=raw_data["position"],
            fundamental_data=raw_data.get("fundamental_data", {}),
            insresearch_data=raw_data.get("insresearch_data", {}),
        )

    def parse_response(self, llm_output: dict, *, raw_data: dict, **kwargs: Any) -> dict:
        technical = raw_data["technical_advice"]
        dim_scores = llm_output.get("dimension_scores", {})
        # 确保始终包含 fundamental 维度
        if "fundamental" not in dim_scores:
            dim_scores["fundamental"] = 0
        return {
            "signal": llm_output.get("signal", technical.get("signal", "hold")),
            "confidence": llm_output.get("confidence", technical.get("confidence", 0)),
            "reasoning": llm_output.get("reasoning", []),
            "indicators_summary": technical.get("indicators_summary", {}),
            "dimension_scores": dim_scores,
            "risk_warnings": llm_output.get("risk_warnings", []),
            "position_advice": llm_output.get("position_advice"),
            "summary": llm_output.get("summary", ""),
        }

    def fallback(self, *, raw_data: dict, **kwargs: Any) -> dict:
        technical = raw_data["technical_advice"]
        return {
            "signal": technical.get("signal", "hold"),
            "confidence": technical.get("confidence", 0),
            "reasoning": technical.get("reasoning", []),
            "indicators_summary": technical.get("indicators_summary", {}),
            "dimension_scores": {
                "technical": 0,
                "sentiment": 0,
                "sector": 0,
                "macro": 0,
                "fundamental": 0,
            },
            "risk_warnings": [],
            "position_advice": None,
            "summary": "AI 分析不可用，当前为纯技术指标建议。",
        }
