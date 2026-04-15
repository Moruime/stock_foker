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

# ------------------------------------------------------------------
# 问财 API 熔断机制：检测到 user limit (403) 后跳过后续调用
# ------------------------------------------------------------------
_iwencai_circuit_open = False  # True = 已熔断，跳过所有问财调用
_iwencai_circuit_reason = ""   # 熔断原因描述


def _check_iwencai_403(exc: Exception) -> bool:
    """判断是否为问财 API 额度耗尽 (HTTP 403 + user limit)，若是则触发熔断。"""
    global _iwencai_circuit_open, _iwencai_circuit_reason
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 403:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        if "user limit" in body.lower() or "user_limit" in body.lower():
            _iwencai_circuit_open = True
            _iwencai_circuit_reason = "问财 API 调用额度已耗尽 (HTTP 403 user limit)"
            logger.warning("问财 API 熔断: %s", _iwencai_circuit_reason)
            return True
        # 其他 403 也触发熔断（可能是 key 失效）
        _iwencai_circuit_open = True
        _iwencai_circuit_reason = f"问财 API 返回 403: {body[:200]}"
        logger.warning("问财 API 熔断: %s", _iwencai_circuit_reason)
        return True
    return False


def get_iwencai_status() -> dict:
    """获取问财 API 当前状态，供前端展示。"""
    return {
        "available": not _iwencai_circuit_open,
        "reason": _iwencai_circuit_reason if _iwencai_circuit_open else "",
    }


def reset_iwencai_circuit():
    """重置问财 API 熔断状态（用于手动恢复或 key 更换后）。"""
    global _iwencai_circuit_open, _iwencai_circuit_reason
    _iwencai_circuit_open = False
    _iwencai_circuit_reason = ""
    logger.info("问财 API 熔断已重置")


def _call_hithink_api(query: str, limit: int = 5) -> dict:
    """调用同花顺问财 API，失败静默返回空 dict。"""
    if _iwencai_circuit_open:
        return {}
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
        _check_iwencai_403(e)
        logger.warning("同花顺问财查询失败(%s): %s", query, e)
    return {}


def _call_hithink_search_api(query: str, channels: list[str]) -> dict:
    """调用同花顺问财综合搜索 API（新闻/公告/研报），失败静默返回空 dict。"""
    if _iwencai_circuit_open:
        return {}
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
        _check_iwencai_403(e)
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


def _akshare_macro_fallback() -> dict:
    """AKShare 宏观指标兜底（问财不可用时）。使用东方财富数据源。"""
    import akshare as ak
    import re

    def _to_datas(value: float | None, time_str: str, label: str = "") -> dict:
        if value is None:
            return {}
        return {"datas": [{"指标": label, "指标值": value, "时间": time_str}]}

    def _parse_month(month_str: str) -> str:
        """'2026年03月份' → '202603'"""
        m = re.match(r"(\d{4})年(\d{2})月", str(month_str))
        return f"{m.group(1)}{m.group(2)}" if m else ""

    results: dict = {}
    # CPI 同比（东方财富/国家统计局）
    try:
        df = ak.macro_china_cpi()
        if df is not None and not df.empty:
            row = df.iloc[0]  # 最新在第一行
            results["cpi"] = _to_datas(
                float(row["全国-同比增长"]), _parse_month(row["月份"]),
                "CPI同比",
            )
    except Exception:
        pass
    # PPI 同比
    try:
        df = ak.macro_china_ppi()
        if df is not None and not df.empty:
            row = df.iloc[0]
            results["ppi"] = _to_datas(
                float(row["当月同比增长"]), _parse_month(row["月份"]),
                "PPI同比",
            )
    except Exception:
        pass
    # PMI 制造业
    try:
        df = ak.macro_china_pmi()
        if df is not None and not df.empty:
            row = df.iloc[0]
            results["pmi"] = _to_datas(
                float(row["制造业-指数"]), _parse_month(row["月份"]),
                "制造业PMI",
            )
    except Exception:
        pass
    # LPR 1Y
    try:
        df = ak.macro_china_lpr()
        if df is not None and not df.empty:
            row = df.iloc[-1]
            d = str(row.get("TRADE_DATE", ""))[:10].replace("-", "")
            results["lpr"] = _to_datas(float(row.get("LPR1Y", 0)), d[:6], "LPR(1Y)")
    except Exception:
        pass
    # M2 同比
    try:
        df = ak.macro_china_money_supply()
        if df is not None and not df.empty:
            row = df.iloc[0]
            results["m2"] = _to_datas(
                float(row["货币和准货币(M2)-同比增长"]), _parse_month(row["月份"]),
                "M2同比",
            )
    except Exception:
        pass
    # 新增信贷同比（macro_china_new_financial_credit，数据更及时）
    try:
        df = ak.macro_china_new_financial_credit()
        if df is not None and not df.empty:
            row = df.iloc[0]  # 最新在第一行
            yoy = row.get("当月-同比增长")
            if yoy is not None:
                results["shibor"] = _to_datas(
                    round(float(yoy), 1), _parse_month(row["月份"]),
                    "新增信贷同比",
                )
    except Exception:
        pass
    # 标记数据源
    results["_source"] = "akshare"
    return results


def fetch_hithink_macro_indicators() -> dict:
    """获取宏观经济关键指标（CPI/PPI/PMI/LPR/M2/社融）。

    优先问财 API，熔断时回退 AKShare。
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
    # 问财全部失败 → AKShare 兜底
    if not results:
        logger.info("问财宏观指标全部失败，回退 AKShare")
        results = _akshare_macro_fallback()
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
    """获取沪深港通北向资金流向汇总（AKShare / 东方财富）。

    返回格式与问财兼容的 dict，包含 datas 列表。
    2024-08 起北向个股明细停披露，仅有汇总级数据。
    """
    try:
        import akshare as ak
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df is None or df.empty:
            return {}
        records = []
        for _, row in df.iterrows():
            direction = str(row.get("资金方向", ""))
            net_buy = float(row.get("成交净买额", 0))
            net_flow = float(row.get("资金净流入", 0))
            # 2024-08 起北向成交净买额/资金净流入不再实时披露，API 返回 0
            # 用 None 标记未披露，前端显示 '--'
            trading_status = row.get("交易状态")
            north_undisclosed = (direction == "北向" and net_buy == 0 and net_flow == 0)
            record: dict = {
                "板块": row.get("板块", ""),
                "方向": direction,
                "成交净买额(亿)": None if north_undisclosed else round(net_buy, 4),
                "资金净流入(亿)": None if north_undisclosed else round(net_flow, 4),
                "交易日": str(row.get("交易日", "")),
            }
            # 上涨/下跌/指数 —— 北向和南向都有
            up = row.get("上涨数")
            down = row.get("下跌数")
            if up is not None and not (isinstance(up, float) and up != up):  # skip NaN
                record["上涨数"] = int(up)
            if down is not None and not (isinstance(down, float) and down != down):
                record["下跌数"] = int(down)
            idx_name = row.get("相关指数", "")
            if idx_name:
                record["相关指数"] = idx_name
            idx_chg = row.get("指数涨跌幅")
            if idx_chg is not None and not (isinstance(idx_chg, float) and idx_chg != idx_chg):
                record["指数涨跌幅"] = round(float(idx_chg), 2)
            records.append(record)
        return {"datas": records} if records else {}
    except Exception as e:
        logger.warning("AKShare 北向资金获取失败: %s", e)
        return {}


def fetch_market_overview() -> dict:
    """获取市场涨跌概况。优先问财，回退 AKShare（乐股）。"""
    data = _call_hithink_api(
        "今日A股上涨家数 下跌家数 涨停家数 跌停家数", limit=5
    )
    if data and data.get("datas"):
        return data
    # AKShare 兜底
    try:
        import akshare as ak
        df = ak.stock_market_activity_legu()
        if df is None or df.empty:
            return {}
        mapping: dict[str, str] = {}
        for _, row in df.iterrows():
            item = str(row.get("item", "")).strip()
            val = row.get("value")
            if item == "上涨":
                mapping["上涨家数"] = int(val) if val is not None else 0
            elif item == "下跌":
                mapping["下跌家数"] = int(val) if val is not None else 0
            elif item == "涨停":
                mapping["涨停家数"] = int(val) if val is not None else 0
            elif item == "跌停":
                mapping["跌停家数"] = int(val) if val is not None else 0
        if mapping:
            logger.info("涨跌概况回退 AKShare（乐股）")
            return {"datas": [mapping]}
        return {}
    except Exception as e:
        logger.warning("AKShare 涨跌概况获取失败: %s", e)
        return {}


def fetch_hithink_index_data() -> dict:
    """获取主要指数最新行情（上证/沪深300/创业板指）。优先问财，回退 AKShare（新浪）。"""
    data = _call_hithink_api("上证指数 沪深300 创业板指最新收盘价涨跌幅成交额", limit=5)
    if data and data.get("datas"):
        return data
    # AKShare 兜底
    try:
        import akshare as ak
        df = ak.stock_zh_index_spot_sina()
        if df is None or df.empty:
            return {}
        targets = ["上证指数", "沪深300", "创业板指"]
        records = []
        for name in targets:
            row = df[df["名称"] == name]
            if row.empty:
                continue
            r = row.iloc[0]
            records.append({
                "指数简称": name,
                "最新价": round(float(r.get("最新价", 0)), 2),
                "涨跌幅": round(float(r.get("涨跌幅", 0)), 2),
                "成交额": float(r.get("成交额", 0)),
            })
        if records:
            logger.info("指数行情回退 AKShare（新浪）")
            return {"datas": records}
        return {}
    except Exception as e:
        logger.warning("AKShare 指数行情获取失败: %s", e)
        return {}
