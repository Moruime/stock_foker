"""消息面情绪分析 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import sentiment_prompt
from app.services.data_fetcher import fetch_stock_news, fetch_hithink_events


class SentimentAgent(BaseAgent):
    agent_name = "sentiment"

    def fetch_data(self, **kwargs: Any) -> dict:
        stock_name: str = kwargs.get("stock_name", "")
        news_data = fetch_stock_news(stock_name)
        events_data = fetch_hithink_events(stock_name)
        return {
            "news_data": news_data,
            "events_data": events_data,
        }

    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        return sentiment_prompt(
            stock_code=kwargs["stock_code"],
            stock_name=kwargs["stock_name"],
            news_data=raw_data["news_data"],
            events_data=raw_data.get("events_data", {}),
        )

    def parse_response(self, llm_output: dict, *, raw_data: dict, **kwargs: Any) -> dict:
        return {
            "overall_sentiment": llm_output.get("overall_sentiment", 0),
            "sentiment_label": llm_output.get("sentiment_label", "中性"),
            "key_news": llm_output.get("key_news", []),
            "noise_ratio": llm_output.get("noise_ratio", 0),
            "analysis": llm_output.get("analysis", ""),
            "raw_news_count": len(raw_data["news_data"].get("datas", [])) if isinstance(raw_data["news_data"], dict) else 0,
        }

    def fallback(self, *, raw_data: dict, **kwargs: Any) -> dict:
        return {
            "overall_sentiment": 0,
            "sentiment_label": "中性",
            "key_news": [],
            "noise_ratio": 0,
            "analysis": "AI 分析不可用，无法获取消息面数据。",
            "raw_news_count": 0,
        }
