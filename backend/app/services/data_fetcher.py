"""新闻、板块、宏观数据获取服务 — 统一使用同花顺问财 API。

每个函数独立 try-except，失败返回 None / {} 不阻断流程。
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 同花顺问财 API 通用客户端
# ------------------------------------------------------------------

def _call_hithink_api(query: str, limit: int = 5) -> dict:
    """调用同花顺问财 API，失败静默返回空 dict。"""
    try:
        api_key = os.environ.get("IWENCAI_API_KEY", "")
        if not api_key:
            return {}
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        payload = {
            "query": query,
            "page": "1",
            "limit": str(limit),
            "is_cache": "1",
            "expand_index": "true",
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            "https://openapi.iwencai.com/v1/query2data",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        # 使用空代理 opener，绕过 macOS 系统代理，直连同花顺接口
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ssl_ctx),
        )
        with opener.open(req, timeout=12) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if isinstance(result, dict) and result.get("status_code", -1) == 0:
            return {
                "datas": result.get("datas", []),
                "chunks_info": result.get("chunks_info", {}),
            }
    except Exception as e:
        logger.warning("同花顺问财查询失败(%s): %s", query, e)
    return {}


def fetch_hithink_macro_indicators() -> dict:
    """获取宏观经济关键指标（CPI/PPI/PMI/LPR/M2）。"""
    queries = [
        ("price_activity", "最近一期CPI同比增速 PPI同比增速 PMI数据"),
        ("monetary", "最新LPR利率 M2同比增速 社融数据"),
    ]
    results = {}
    for key, q in queries:
        data = _call_hithink_api(q, limit=5)
        if data:
            results[key] = data
    return results


def fetch_hithink_finance_data(stock_name: str) -> dict:
    """获取个股财务指标（ROE/营业收入/净利润/毛利率/负债率/PE）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}最新ROE净利润增速毛利率负债率PE估值", limit=5)


def fetch_hithink_insresearch_data(stock_name: str) -> dict:
    """获取机构研究评级和目标价。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}机构评级目标价一致预期", limit=5)


def fetch_hithink_events(stock_name: str) -> dict:
    """获取个股近期重要事件（业绩预告/解禁/减持/增持）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}近期业绩预告解禁减持增持", limit=5)


# ------------------------------------------------------------------
# 消息面
# ------------------------------------------------------------------

def fetch_stock_news(stock_name: str) -> dict:
    """获取个股相关新闻（同花顺问财）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}近期重大新闻公告事件", limit=20)


# ------------------------------------------------------------------
# 板块联动
# ------------------------------------------------------------------

def fetch_industry_board(stock_name: str) -> dict:
    """获取个股所属行业板块信息（同花顺问财）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(
        f"{stock_name}所属行业 行业涨跌幅 行业换手率 行业成交额 行业内涨跌幅前5个股",
        limit=10,
    )


def fetch_concept_boards() -> dict:
    """获取今日热门概念板块（同花顺问财）。"""
    return _call_hithink_api("今日涨幅最大的概念板块前10 涨跌幅", limit=10)


# ------------------------------------------------------------------
# 宏观环境
# ------------------------------------------------------------------

def fetch_index_data() -> dict:
    """获取上证指数近期走势（同花顺问财）。"""
    return _call_hithink_api("上证指数最近5个交易日收盘价涨跌幅成交量", limit=5)


def fetch_north_flow() -> dict:
    """获取北向资金最新数据（同花顺问财）。"""
    return _call_hithink_api("最近一个交易日北向资金净流入沪股通深股通", limit=3)


def fetch_market_overview() -> dict:
    """获取市场涨跌概况（同花顺问财）。"""
    return _call_hithink_api("今日A股行业板块涨跌家数 平均涨跌幅 涨幅前5板块", limit=20)
