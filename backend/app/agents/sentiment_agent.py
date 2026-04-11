"""消息面情绪分析 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import sentiment_prompt
from app.services.data_fetcher import fetch_stock_news, fetch_hithink_events, parallel_fetch


class SentimentAgent(BaseAgent):
    agent_name = "sentiment"

    def fetch_data(self, **kwargs: Any) -> dict:
        stock_code: str = kwargs.get("stock_code", "")
        stock_name: str = kwargs.get("stock_name", "")
        db = kwargs.get("db")

        # 非缓存数据源（仅供 LLM 分析使用，不需要独立展示）
        base_results = parallel_fetch({
            "news_data": (fetch_stock_news, (stock_name,)),
            "events_data": (fetch_hithink_events, (stock_name,)),
        })

        # 使用数据源缓存服务获取资讯和公告（支持独立缓存）
        if db:
            from app.services.data_source_service import get_data_source
            hithink_news, _, _ = get_data_source(db, stock_code, stock_name, "hithink_news")
            announcements, _, _ = get_data_source(db, stock_code, stock_name, "announcements")
        else:
            from app.services.data_fetcher import fetch_hithink_news, fetch_hithink_announcements
            hithink_news = fetch_hithink_news(stock_name)
            announcements = fetch_hithink_announcements(stock_name)

        return {
            **base_results,
            "hithink_news": hithink_news,
            "announcements": announcements,
        }

    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        return sentiment_prompt(
            stock_code=kwargs["stock_code"],
            stock_name=kwargs["stock_name"],
            news_data=raw_data["news_data"],
            events_data=raw_data.get("events_data", {}),
            hithink_news=raw_data.get("hithink_news", {}),
            announcements=raw_data.get("announcements", {}),
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
