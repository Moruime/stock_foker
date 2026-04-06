import json
import re
import time

import akshare as ak
import pandas as pd
import pandas_ta as ta
import requests as _requests
from datetime import datetime, timedelta
from typing import Optional


_SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn",
}

# K线周期映射: period -> sina scale (分钟数, 240=日K)
_PERIOD_SCALE = {"daily": 240, "weekly": 1200, "monthly": 7200}


def _retry_call(fn, retries: int = 3, delay: float = 2.0):
    """带重试的函数调用"""
    last_err = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if i < retries - 1:
                time.sleep(delay * (i + 1))
    raise last_err  # type: ignore[misc]


_stock_list_cache: list[dict] | None = None


def _load_stock_list() -> list[dict]:
    """加载并缓存 A 股股票列表"""
    global _stock_list_cache
    if _stock_list_cache is not None:
        return _stock_list_cache
    try:
        df = _retry_call(ak.stock_info_a_code_name)
        _stock_list_cache = [
            {"stock_code": str(row["code"]), "stock_name": str(row["name"])}
            for _, row in df.iterrows()
        ]
        return _stock_list_cache
    except Exception:
        return []


def search_stocks(keyword: str) -> list[dict]:
    """搜索股票，返回匹配的股票列表"""
    try:
        stocks = _load_stock_list()
        results = [
            s for s in stocks
            if keyword in s["stock_code"] or keyword in s["stock_name"]
        ]
        return results[:20]
    except Exception as e:
        raise RuntimeError(f"搜索股票失败: {e}")


def _sina_symbol(stock_code: str) -> str:
    """将纯数字股票代码转为新浪格式 (sz000001, sh600000)"""
    if stock_code.startswith("6") or stock_code.startswith("9"):
        return f"sh{stock_code}"
    return f"sz{stock_code}"


def _get_kline_sina(stock_code: str, period: str, datalen: int = 300) -> list[dict]:
    """通过新浪财经接口获取K线数据"""
    symbol = _sina_symbol(stock_code)
    scale = _PERIOD_SCALE.get(period, 240)
    url = (
        f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_data=/"
        f"CN_MarketDataService.getKLineData"
        f"?symbol={symbol}&scale={scale}&ma=no&datalen={datalen}"
    )
    resp = _requests.get(url, headers=_SINA_HEADERS, timeout=15)
    resp.raise_for_status()

    # 解析 JSONP: var _data=([...]);
    match = re.search(r"\((\[.*\])\)", resp.text, re.DOTALL)
    if not match:
        raise RuntimeError("无法解析新浪K线数据")

    raw = json.loads(match.group(1))
    records = []
    for item in raw:
        o, c, h, l = float(item["open"]), float(item["close"]), float(item["high"]), float(item["low"])
        vol = float(item["volume"])
        # 新浪不返回成交额，用均价*成交量估算
        avg_price = (o + c + h + l) / 4
        records.append({
            "date": item["day"],
            "open": o,
            "close": c,
            "high": h,
            "low": l,
            "volume": vol,
            "turnover": round(avg_price * vol, 2),
        })
    return records


def _get_kline_akshare(
    stock_code: str, period: str, start_date: str, end_date: str,
) -> list[dict]:
    """通过 AKShare(东方财富) 获取K线数据"""
    df = ak.stock_zh_a_hist(
        symbol=stock_code,
        period=period,
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
        timeout=8,
    )
    records = []
    for _, row in df.iterrows():
        records.append({
            "date": str(row["日期"]),
            "open": float(row["开盘"]),
            "close": float(row["收盘"]),
            "high": float(row["最高"]),
            "low": float(row["最低"]),
            "volume": float(row["成交量"]),
            "turnover": float(row.get("成交额", 0)),
        })
    return records


def get_kline_data(
    stock_code: str,
    period: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db=None,
) -> list[dict]:
    """获取K线数据，本地缓存优先，缺失部分增量拉取远程

    策略:
    1. 从 SQLite 读取已有缓存
    2. 判断缓存是否覆盖到最近交易日
    3. 仅拉取缺失的增量数据并写入缓存
    4. 合并返回
    """
    if db is not None:
        return _get_kline_with_cache(stock_code, period, db)

    # 无 db 时直接走远程（兼容旧调用）
    return _fetch_remote_kline(stock_code, period)


def _get_kline_with_cache(stock_code: str, period: str, db) -> list[dict]:
    """带本地缓存的 K 线获取"""
    from app.models.models import KlineCache

    # 1. 读取本地缓存
    cached_rows = (
        db.query(KlineCache)
        .filter(KlineCache.stock_code == stock_code, KlineCache.period == period)
        .order_by(KlineCache.date.asc())
        .all()
    )

    cached_data = [
        {
            "date": r.date,
            "open": r.open,
            "close": r.close,
            "high": r.high,
            "low": r.low,
            "volume": r.volume,
            "turnover": r.turnover or 0.0,
        }
        for r in cached_rows
    ]

    # 2. 判断是否需要增量更新
    last_cached_date = cached_rows[-1].date if cached_rows else None
    today = datetime.now().strftime("%Y-%m-%d")

    need_fetch = True
    if last_cached_date:
        # 如果最后缓存日期是今天或者昨天(非交易日也算)，不需要更新
        days_gap = (datetime.now() - datetime.strptime(last_cached_date, "%Y-%m-%d")).days
        if days_gap <= 1:
            need_fetch = False

    if not need_fetch and len(cached_data) >= 60:
        return cached_data

    # 3. 拉取远程数据
    try:
        remote_data = _fetch_remote_kline(stock_code, period)
    except Exception:
        # 远程失败但有缓存，用缓存
        if cached_data:
            return cached_data
        raise

    # 4. 增量写入缓存（只写本地没有的日期）
    cached_dates = {r.date for r in cached_rows}
    new_rows = []
    for item in remote_data:
        if item["date"] not in cached_dates:
            new_rows.append(KlineCache(
                stock_code=stock_code,
                period=period,
                date=item["date"],
                open=item["open"],
                close=item["close"],
                high=item["high"],
                low=item["low"],
                volume=item["volume"],
                turnover=item.get("turnover", 0.0),
            ))
        else:
            # 更新最后一天的数据（盘中数据可能变化）
            if item["date"] == today:
                db.query(KlineCache).filter(
                    KlineCache.stock_code == stock_code,
                    KlineCache.period == period,
                    KlineCache.date == today,
                ).update({
                    "open": item["open"],
                    "close": item["close"],
                    "high": item["high"],
                    "low": item["low"],
                    "volume": item["volume"],
                })

    if new_rows:
        db.add_all(new_rows)
    db.commit()

    # 5. 合并返回：用远程数据（更完整）
    return remote_data


def _fetch_remote_kline(stock_code: str, period: str) -> list[dict]:
    """从远程获取K线数据，AKShare优先（含成交额），新浪降级"""
    import logging
    logger = logging.getLogger(__name__)
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")
    try:
        # AKShare 单次尝试，不重试，快速降级
        data = _get_kline_akshare(stock_code, period, start_date, end_date)
        logger.info("K线数据来源: AKShare, records=%d", len(data))
        return data
    except Exception as e:
        logger.warning("AKShare获取失败: %s, 降级到新浪", e)

    try:
        data = _retry_call(lambda: _get_kline_sina(stock_code, period))
        logger.info("K线数据来源: 新浪, records=%d", len(data))
        return data
    except Exception as e:
        raise RuntimeError(f"获取K线数据失败: {e}")


def calculate_indicators(kline_data: list[dict], time_frame: str = "short") -> dict:
    """计算技术指标"""
    df = pd.DataFrame(kline_data)
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # 均线
    ma5 = ta.sma(close, length=5)
    ma10 = ta.sma(close, length=10)
    ma20 = ta.sma(close, length=20)
    ma60 = ta.sma(close, length=60)

    # MACD
    macd_result = ta.macd(close, fast=12, slow=26, signal=9)
    macd_dict = {}
    if macd_result is not None:
        cols = macd_result.columns.tolist()
        macd_dict = {
            "dif": _series_to_list(macd_result[cols[0]]),
            "dea": _series_to_list(macd_result[cols[1]]),
            "histogram": _series_to_list(macd_result[cols[2]]),
        }

    # KDJ
    kdj_result = ta.kdj(high, low, close, length=9, signal=3)
    kdj_dict = {}
    if kdj_result is not None:
        cols = kdj_result.columns.tolist()
        kdj_dict = {
            "k": _series_to_list(kdj_result[cols[0]]),
            "d": _series_to_list(kdj_result[cols[1]]),
            "j": _series_to_list(kdj_result[cols[2]]),
        }

    # RSI
    rsi = ta.rsi(close, length=14)

    # 布林带
    boll_result = ta.bbands(close, length=20, std=2)
    boll_dict = {}
    if boll_result is not None:
        cols = boll_result.columns.tolist()
        boll_dict = {
            "upper": _series_to_list(boll_result[cols[0]]),
            "middle": _series_to_list(boll_result[cols[1]]),
            "lower": _series_to_list(boll_result[cols[2]]),
        }

    return {
        "ma5": _series_to_list(ma5),
        "ma10": _series_to_list(ma10),
        "ma20": _series_to_list(ma20),
        "ma60": _series_to_list(ma60),
        "macd": macd_dict,
        "kdj": kdj_dict,
        "rsi": _series_to_list(rsi),
        "boll": boll_dict,
        "volumes": df["volume"].tolist(),
    }


def _series_to_list(s: Optional[pd.Series]) -> list:
    """将 pandas Series 转为 list，NaN 转 None"""
    if s is None:
        return []
    return [None if pd.isna(v) else round(float(v), 4) for v in s]
