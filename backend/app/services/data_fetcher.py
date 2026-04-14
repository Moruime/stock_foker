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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

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


def _call_hithink_search_api(query: str, channels: list[str]) -> dict:
    """调用同花顺问财综合搜索 API（新闻/公告/研报），失败静默返回空 dict。"""
    try:
        api_key = os.environ.get("IWENCAI_API_KEY", "")
        if not api_key:
            return {}
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        payload = {
            "channels": channels,
            "app_id": "AIME_SKILL",
            "query": query,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            "https://openapi.iwencai.com/v1/comprehensive/search",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ssl_ctx),
        )
        with opener.open(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if isinstance(result, dict):
            return {
                "data": result.get("data", []),
            }
    except Exception as e:
        logger.warning("同花顺综合搜索失败(%s, %s): %s", query, channels, e)
    return {}


def parallel_fetch(tasks: dict[str, tuple[Callable, tuple]]) -> dict[str, Any]:
    """并行执行多个 fetch 调用，返回 {key: result} 字典。

    tasks 格式: {"label": (callable, (arg1, arg2, ...))}
    每个 callable 独立 try-except，此处再加一层保底。
    """
    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as executor:
        future_to_key = {
            executor.submit(fn, *args): key
            for key, (fn, args) in tasks.items()
        }
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as e:
                logger.warning("parallel_fetch '%s' 异常: %s", key, e)
                results[key] = {}
    return results


def fetch_hithink_macro_indicators() -> dict:
    """获取宏观经济关键指标（CPI/PPI/PMI/LPR/M2）。

    拆分为独立查询避免问财 API 多指标合并时丢数据。
    """
    queries = [
        ("cpi", "中国CPI当月同比最新值"),
        ("ppi", "最新月度PPI当月同比"),
        ("pmi", "最近一期制造业PMI"),
        ("lpr", "最新1年期LPR利率"),
        ("m2", "最新M2同比增速"),
        ("shibor", "最新社融规模存量同比"),
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
    """获取个股近期重要事件（业绩预告为主）。

    问财 API 对复合事件查询支持有限，聚焦业绩预告可获取
    预告类型、预告净利润、摘要等详细字段。
    """
    if not stock_name:
        return {}
    return _call_hithink_api(
        f"{stock_name}最新业绩预告 预告类型 预告净利润 变动原因", limit=5
    )


def fetch_hithink_reports(stock_name: str) -> dict:
    """通过同花顺综合搜索获取个股研究报告。"""
    if not stock_name:
        return {}
    return _call_hithink_search_api(f"{stock_name}研究报告", channels=["report"])


def fetch_hithink_business_data(stock_name: str) -> dict:
    """获取公司经营数据（主营构成/客户/供应商）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}主营业务构成 收入占比 主要客户 主要供应商", limit=10)


def fetch_hithink_basicinfo(stock_name: str) -> dict:
    """获取股票基本资料（行业分类、上市日期、总股本等）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}所属行业 上市日期 总股本 流通股本 总市值", limit=5)


def fetch_hithink_shareholders(stock_name: str) -> dict:
    """获取股东股本信息（股东户数、前十大股东、实控人）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}股东户数 户均持股 前十大股东 实控人", limit=10)


# ------------------------------------------------------------------
# 消息面
# ------------------------------------------------------------------

def fetch_stock_news(stock_name: str) -> dict:
    """获取个股相关新闻（同花顺问财）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}近期重大新闻公告事件", limit=20)


def fetch_hithink_news(stock_name: str) -> dict:
    """通过同花顺综合搜索获取个股财经资讯。"""
    if not stock_name:
        return {}
    return _call_hithink_search_api(f"{stock_name}最新动态", channels=["news"])


def fetch_hithink_announcements(stock_name: str) -> dict:
    """通过同花顺综合搜索获取个股公告信息。"""
    if not stock_name:
        return {}
    return _call_hithink_search_api(f"{stock_name}公告", channels=["announcement"])


# ------------------------------------------------------------------
# 板块联动
# ------------------------------------------------------------------

def fetch_industry_board(stock_name: str) -> dict:
    """获取个股所属行业板块信息（同花顺问财）。

    简化查询词避免复合条件导致 0 结果。
    """
    if not stock_name:
        return {}
    return _call_hithink_api(
        f"{stock_name}所属同花顺行业",
        limit=5,
    )


def fetch_concept_boards(stock_name: str) -> dict:
    """获取个股所属概念板块详情（涨跌幅、成份股数量）。

    问财 API 不支持“个股+概念+涨跌幅+成份股”复合查询（-2058），
    采用两步策略：先获取概念名称列表，再并行查询各概念板块详情。
    """
    if not stock_name:
        return {}
    # Step 1: 获取所属概念名称列表
    base = _call_hithink_api(f"{stock_name}所属概念板块", limit=1)
    if not base or not base.get("datas"):
        return base
    concepts = base["datas"][0].get("所属概念", [])
    if not concepts:
        return base

    # Step 2: 并行查询各概念板块的涨跌幅和成份股数量
    def _query_concept(name: str) -> dict | None:
        r = _call_hithink_api(
            f"{name}概念板块涨跌幅 成份股数量", limit=1
        )
        if r and r.get("datas"):
            return r["datas"][0]
        return None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    results: list[dict] = []
    seen_codes: set[str] = set()
    with ThreadPoolExecutor(max_workers=min(len(concepts), 8)) as exe:
        futs = {exe.submit(_query_concept, c): c for c in concepts}
        for fut in as_completed(futs):
            try:
                row = fut.result()
                if row:
                    code = row.get("指数代码") or row.get("指数简称", "")
                    # 过滤仅含代码/简称、无实质数据的记录
                    has_data = "成份股数量" in row or any(
                        "涨跌幅" in k for k in row
                    )
                    if code and code not in seen_codes and has_data:
                        seen_codes.add(code)
                        results.append(row)
            except Exception:
                pass

    return {"datas": results, "chunks_info": {}}


def fetch_hithink_industry_data(stock_name: str) -> dict:
    """获取个股所属行业估值/盈利数据（PE/PB/ROE/行业排名）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}所属行业PE PB ROE 行业涨跌幅排名", limit=10)


def fetch_hithink_market_data(stock_name: str) -> dict:
    """获取个股/板块主力资金流向数据。"""
    if not stock_name:
        return {}
    return _call_hithink_api(f"{stock_name}主力资金净流入 大单净量 换手率 量比", limit=5)


def fetch_hithink_industry_finance(stock_name: str) -> dict:
    """获取个股所属行业财务概况（营收增速、净利润增速、毛利率、行业排名等）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(
        f"{stock_name}所属行业 行业营业收入增长率 行业净利润增长率 行业毛利率 行业净利率 行业排名",
        limit=10,
    )


def fetch_hithink_industry_peers(stock_name: str) -> dict:
    """获取个股所属行业市值龙头（涨跌幅、市盈率、市值、主力资金等）。"""
    if not stock_name:
        return {}
    return _call_hithink_api(
        f"{stock_name}同行业个股 市值从大到小 涨跌幅 市盈率 总市值 主力资金流向",
        limit=10,
    )


# ------------------------------------------------------------------
# 宏观环境
# ------------------------------------------------------------------

def fetch_index_data() -> dict:
    """获取上证指数近期走势（同花顺问财）。"""
    return _call_hithink_api("上证指数最近5个交易日收盘价涨跌幅成交量", limit=5)


def fetch_north_flow() -> dict:
    """获取主力资金流向 Top10（同花顺问财）。

    问财 API 对北向资金查询返回的实际是主力资金流向数据，
    字段名为「主力资金流向[日期]」，单位为元。
    """
    return _call_hithink_api(
        "今日北向资金净买入额前10 净买入额 涨跌幅", limit=10
    )


def fetch_market_overview() -> dict:
    """获取市场涨跌概况（同花顺问财）。"""
    return _call_hithink_api(
        "今日A股上涨家数 下跌家数 涨停家数 跌停家数", limit=5
    )


def fetch_hithink_index_data() -> dict:
    """获取主要指数最新行情（上证/沪深300/创业板指）。"""
    return _call_hithink_api("上证指数 沪深300 创业板指最新收盘价涨跌幅成交额", limit=5)
