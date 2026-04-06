"""消息面情绪分析 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import sentiment_prompt
from app.services.data_fetcher import fetch_stock_news


class SentimentAgent(BaseAgent):
    agent_name = "sentiment"

    def fetch_data(self, **kwargs: Any) -> dict:
        stock_code: str = kwargs["stock_code"]
        news_list = fetch_stock_news(stock_code)
        return {"news_list": news_list or []}

    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        return sentiment_prompt(
            stock_code=kwargs["stock_code"],
            stock_name=kwargs["stock_name"],
            news_list=raw_data["news_list"],
        )

    def parse_response(self, llm_output: dict, *, raw_data: dict, **kwargs: Any) -> dict:
        return {
            "overall_sentiment": llm_output.get("overall_sentiment", 0),
            "sentiment_label": llm_output.get("sentiment_label", "中性"),
            "key_news": llm_output.get("key_news", []),
            "noise_ratio": llm_output.get("noise_ratio", 0),
            "analysis": llm_output.get("analysis", ""),
            "raw_news_count": len(raw_data["news_list"]),
        }

    def fallback(self, *, raw_data: dict, **kwargs: Any) -> dict:
        news = raw_data["news_list"]
        return {
            "overall_sentiment": 0,
            "sentiment_label": "中性",
            "key_news": [
                {
                    "title": n.get("title", ""),
                    "date": n.get("date", ""),
                    "sentiment": "中性",
                    "impact_level": "中",
                    "summary": n.get("title", ""),
                }
                for n in news[:10]
            ],
            "noise_ratio": 0,
            "analysis": "AI 分析不可用，展示原始新闻列表。",
            "raw_news_count": len(news),
        }
