"""消息面情绪分析 Agent。"""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompts import sentiment_prompt


# 全部 8 个数据源统一走缓存服务
_SENTIMENT_SOURCES = [
    "stock_news",       # 问财近期重大新闻（LLM section 一）
    "hithink_events",   # 业绩预告（LLM section 二 + 前端"业绩预告"Tab）
    "hithink_news",     # 综合搜索资讯（LLM section 三 + 前端"财经资讯"Tab）
    "announcements",    # 综合搜索公告（LLM section 四 + 前端"公司公告"Tab）
    "reports",          # 综合搜索研报（LLM section 五 + 前端"研报观点"Tab）
    "basicinfo",        # 问财基本资料（LLM section 六 + 前端"公司概况"）
    "business",         # 问财经营数据（LLM section 七 + 前端"公司概况"表格）
    "shareholders",     # 问财股东信息（LLM section 八 + 前端"股东信息"Tab）
]


class SentimentAgent(BaseAgent):
    agent_name = "sentiment"

    def fetch_data(self, **kwargs: Any) -> dict:
        stock_code: str = kwargs.get("stock_code", "")
        stock_name: str = kwargs.get("stock_name", "")
        db = kwargs.get("db")

        if db:
            from app.services.data_source_service import parallel_get_data_sources
            sources = parallel_get_data_sources(db, stock_code, stock_name, _SENTIMENT_SOURCES)
        else:
            from app.services.data_fetcher import (
                fetch_stock_news, fetch_hithink_events,
                fetch_hithink_news, fetch_hithink_announcements,
                fetch_hithink_reports, fetch_hithink_basicinfo,
                fetch_hithink_business_data, fetch_hithink_shareholders,
            )
            from app.services.data_fetcher import parallel_fetch
            sources = parallel_fetch({
                "stock_news": (fetch_stock_news, (stock_name,)),
                "hithink_events": (fetch_hithink_events, (stock_name,)),
                "hithink_news": (fetch_hithink_news, (stock_name,)),
                "announcements": (fetch_hithink_announcements, (stock_name,)),
                "reports": (fetch_hithink_reports, (stock_name,)),
                "basicinfo": (fetch_hithink_basicinfo, (stock_name,)),
                "business": (fetch_hithink_business_data, (stock_name,)),
                "shareholders": (fetch_hithink_shareholders, (stock_name,)),
            })

        # 兼容 prompt 中使用的 key 名
        return {
            "news_data": sources.get("stock_news", {}),
            "events_data": sources.get("hithink_events", {}),
            "hithink_news": sources.get("hithink_news", {}),
            "announcements": sources.get("announcements", {}),
            "reports": sources.get("reports", {}),
            "basicinfo": sources.get("basicinfo", {}),
            "business": sources.get("business", {}),
            "shareholders": sources.get("shareholders", {}),
        }

    def build_prompt(self, *, raw_data: dict, **kwargs: Any) -> list[dict[str, str]]:
        return sentiment_prompt(
            stock_code=kwargs["stock_code"],
            stock_name=kwargs["stock_name"],
            news_data=raw_data["news_data"],
            events_data=raw_data.get("events_data", {}),
            hithink_news=raw_data.get("hithink_news", {}),
            announcements=raw_data.get("announcements", {}),
            reports=raw_data.get("reports", {}),
            basicinfo=raw_data.get("basicinfo", {}),
            business=raw_data.get("business", {}),
            shareholders=raw_data.get("shareholders", {}),
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
