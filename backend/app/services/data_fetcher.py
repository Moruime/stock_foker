"""新闻、板块、宏观数据获取服务。

每个函数独立 try-except，失败返回 None 不阻断流程。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 消息面
# ------------------------------------------------------------------

def fetch_stock_news(stock_code: str) -> list[dict] | None:
    """获取个股新闻（东方财富）。"""
    try:
        df = ak.stock_news_em(symbol=stock_code)
        if df is None or df.empty:
            return []
        records = []
        for _, row in df.head(30).iterrows():
            records.append({
                "title": str(row.get("新闻标题", "")),
                "content": str(row.get("新闻内容", ""))[:200],
                "date": str(row.get("发布时间", "")),
                "source": str(row.get("文章来源", "")),
            })
        return records
    except Exception as e:
        logger.warning("获取个股新闻失败(%s): %s", stock_code, e)
        return None


# ------------------------------------------------------------------
# 板块联动
# ------------------------------------------------------------------

def fetch_industry_board(stock_code: str) -> dict | None:
    """获取个股所属行业板块及板块数据。"""
    try:
        # 获取个股所属行业
        info_df = ak.stock_individual_info_em(symbol=stock_code)
        industry_name = ""
        if info_df is not None and not info_df.empty:
            for _, row in info_df.iterrows():
                if "行业" in str(row.get("item", "")):
                    industry_name = str(row.get("value", ""))
                    break

        # 获取行业板块列表
        board_df = ak.stock_board_industry_name_em()
        if board_df is None or board_df.empty:
            return {"board_name": industry_name}

        # 找到匹配的板块
        matched = board_df[board_df["板块名称"].str.contains(industry_name, na=False)] if industry_name else pd.DataFrame()
        if matched.empty and industry_name:
            matched = board_df.head(1)

        board_info = {}
        if not matched.empty:
            row = matched.iloc[0]
            board_info = {
                "board_name": str(row.get("板块名称", industry_name)),
                "change_pct": float(row.get("涨跌幅", 0)),
                "turnover_rate": float(row.get("换手率", 0)) if "换手率" in row.index else 0,
                "total_amount": float(row.get("总市值", 0)) if "总市值" in row.index else 0,
            }

            # 获取板块成分股（前10只）
            try:
                cons_df = ak.stock_board_industry_cons_em(symbol=board_info["board_name"])
                if cons_df is not None and not cons_df.empty:
                    top_stocks = []
                    for _, s in cons_df.head(10).iterrows():
                        top_stocks.append({
                            "name": str(s.get("名称", "")),
                            "code": str(s.get("代码", "")),
                            "change_pct": float(s.get("涨跌幅", 0)),
                        })
                    board_info["top_stocks"] = top_stocks
            except Exception:
                pass

        return board_info or {"board_name": industry_name}
    except Exception as e:
        logger.warning("获取行业板块失败(%s): %s", stock_code, e)
        return None


def fetch_concept_boards(stock_code: str) -> list[dict] | None:
    """获取与个股相关的概念板块。"""
    try:
        df = ak.stock_board_concept_name_em()
        if df is None or df.empty:
            return []
        # 取涨跌幅最大的前 10 个概念板块作为市场热点
        df_sorted = df.sort_values("涨跌幅", ascending=False).head(10)
        records = []
        for _, row in df_sorted.iterrows():
            records.append({
                "board_name": str(row.get("板块名称", "")),
                "change_pct": float(row.get("涨跌幅", 0)),
            })
        return records
    except Exception as e:
        logger.warning("获取概念板块失败(%s): %s", stock_code, e)
        return None


# ------------------------------------------------------------------
# 宏观环境
# ------------------------------------------------------------------

def fetch_index_data() -> dict | None:
    """获取上证指数近期走势。"""
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        df = ak.stock_zh_index_daily_em(
            symbol="sh000001",
            start_date=start,
            end_date=end,
        )
        if df is None or df.empty:
            return {}
        recent = df.tail(5)
        last = recent.iloc[-1]
        first = recent.iloc[0]
        change_pct = ((float(last["close"]) - float(first["close"])) / float(first["close"])) * 100
        return {
            "index_name": "上证指数",
            "current": float(last["close"]),
            "change_pct": round(change_pct, 2),
            "recent_data": [
                {
                    "date": str(row["date"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume", 0)),
                }
                for _, row in recent.iterrows()
            ],
        }
    except Exception as e:
        logger.warning("获取大盘指数失败: %s", e)
        return None


def fetch_north_flow() -> dict | None:
    """获取北向资金数据。"""
    try:
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        if df is None or df.empty:
            return {}
        last = df.iloc[-1]
        return {
            "date": str(last.get("日期", "")),
            "net_flow": float(last.get("当日净流入", 0)) / 1e8,
        }
    except Exception as e:
        logger.warning("获取北向资金失败: %s", e)
        return None


def fetch_market_overview() -> dict | None:
    """获取市场涨跌概况。"""
    try:
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return {}
        up_count = int((df["涨跌幅"] > 0).sum())
        down_count = int((df["涨跌幅"] < 0).sum())
        flat_count = int((df["涨跌幅"] == 0).sum())
        return {
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "avg_change_pct": round(float(df["涨跌幅"].mean()), 2),
        }
    except Exception as e:
        logger.warning("获取市场概况失败: %s", e)
        return None
