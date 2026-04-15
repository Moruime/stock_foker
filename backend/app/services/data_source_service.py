"""数据源缓存服务 — 独立于 Agent，管理原始 hithink API 数据的获取与缓存。

每个数据源类型对应一个 fetch 函数，缓存以 (stock_code, source_type, date) 为粒度。
缓存新鲜度边界与 Agent 保持一致：每天 09:00 。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.models import DataSourceCache
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.data_fetcher import (
    fetch_hithink_news,
    fetch_hithink_announcements,
    fetch_hithink_industry_data,
    fetch_hithink_industry_finance,
    fetch_hithink_industry_peers,
    fetch_hithink_market_data,
    fetch_hithink_index_data,
    fetch_hithink_reports,
    fetch_hithink_basicinfo,
    fetch_hithink_business_data,
    fetch_hithink_shareholders,
    fetch_concept_boards,
    fetch_north_flow,
    fetch_market_overview,
    fetch_hithink_macro_indicators,
    fetch_hithink_events,
    fetch_stock_news,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 数据源注册表
# ------------------------------------------------------------------

# key: source_type, value: (fetch_fn, needs_stock_name, priority)
# fetch_fn 签名: (stock_name: str) -> dict  或  () -> dict
# priority: 数值越小越优先执行。综合搜索 API（不易触发熔断）排在前面，
#           query2data API 排在后面，避免先耗尽额度导致搜索 API 也被连带跳过。
_SOURCE_REGISTRY: dict[str, tuple[Callable[..., dict], bool, int]] = {
    # --- 综合搜索 API (comprehensive/search)，优先级 0 ---
    "hithink_news":         (fetch_hithink_news, True, 0),
    "announcements":        (fetch_hithink_announcements, True, 0),
    "reports":              (fetch_hithink_reports, True, 0),
    # --- AKShare / 兜底数据源，优先级 1 ---
    "north_flow":           (fetch_north_flow, False, 1),
    "market_overview":      (fetch_market_overview, False, 1),
    "hithink_index":        (fetch_hithink_index_data, False, 1),
    "hithink_macro":        (fetch_hithink_macro_indicators, False, 1),
    # --- query2data API，优先级 2 ---
    "stock_news":           (fetch_stock_news, True, 2),
    "hithink_events":       (fetch_hithink_events, True, 2),
    "basicinfo":            (fetch_hithink_basicinfo, True, 2),
    "business":             (fetch_hithink_business_data, True, 2),
    "shareholders":         (fetch_hithink_shareholders, True, 2),
    "industry_valuation":   (fetch_hithink_industry_data, True, 2),
    "market_data":          (fetch_hithink_market_data, True, 2),
    "industry_finance":     (fetch_hithink_industry_finance, True, 2),
    "industry_peers":       (fetch_hithink_industry_peers, True, 2),
    "concept_boards":       (fetch_concept_boards, True, 2),
}

VALID_SOURCE_TYPES = set(_SOURCE_REGISTRY.keys())


# ------------------------------------------------------------------
# 缓存新鲜度
# ------------------------------------------------------------------

def _last_9am() -> datetime:
    now = datetime.now()
    today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    return today_9am if now >= today_9am else today_9am - timedelta(days=1)


def _cache_key_today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ------------------------------------------------------------------
# 缓存读写
# ------------------------------------------------------------------

def _get_cached_source(db: Session, stock_code: str, source_type: str) -> tuple[dict, datetime] | None:
    """查询新鲜缓存（09:00 边界后生成的数据）。返回 (data, created_at) 或 None。"""
    row = db.query(DataSourceCache).filter(
        DataSourceCache.stock_code == stock_code,
        DataSourceCache.source_type == source_type,
        DataSourceCache.created_at >= _last_9am(),
    ).order_by(DataSourceCache.created_at.desc()).first()
    if row:
        return json.loads(row.data), row.created_at
    return None


def _get_latest_history_cache(db: Session, stock_code: str, source_type: str) -> tuple[dict, datetime] | None:
    """查询最近一条有效历史缓存（不限新鲜度），用于 API 不可用时降级。

    跳过空数据记录，最多查找 5 条。
    """
    rows = db.query(DataSourceCache).filter(
        DataSourceCache.stock_code == stock_code,
        DataSourceCache.source_type == source_type,
    ).order_by(DataSourceCache.created_at.desc()).limit(5).all()
    for row in rows:
        data = json.loads(row.data)
        if not _is_empty_data(data):
            return data, row.created_at
    return None


def _save_source_cache(db: Session, stock_code: str, source_type: str, data: dict) -> datetime:
    """写入或更新数据源缓存，返回写入时间。"""
    cache_key = _cache_key_today()
    now = datetime.now()
    existing = db.query(DataSourceCache).filter(
        DataSourceCache.stock_code == stock_code,
        DataSourceCache.source_type == source_type,
        DataSourceCache.cache_key == cache_key,
    ).first()
    data_json = json.dumps(data, ensure_ascii=False)
    if existing:
        existing.data = data_json
        existing.created_at = now
    else:
        row = DataSourceCache(
            stock_code=stock_code,
            source_type=source_type,
            cache_key=cache_key,
            data=data_json,
            created_at=now,
        )
        db.add(row)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("数据源缓存写入失败 stock=%s type=%s: %s", stock_code, source_type, exc)
    return now


# ------------------------------------------------------------------
# 公共 API
# ------------------------------------------------------------------

def _is_empty_data(data: dict) -> bool:
    """判断 API 返回的数据是否为空（熔断/失败时通常返回 {}）。"""
    if not data:
        return True
    # query2data 格式: {"datas": [...], "chunks_info": {...}}
    if "datas" in data and not data["datas"]:
        return True
    # comprehensive/search 格式: {"data": [...]}
    if "data" in data and not data["data"]:
        return True
    return False


def get_data_source(
    db: Session,
    stock_code: str,
    stock_name: str,
    source_type: str,
    force_refresh: bool = False,
) -> tuple[dict, datetime, bool]:
    """获取数据源。返回 (data, timestamp, from_cache)。

    优先级：
    1. 当日新鲜缓存（09:00 边界后）
    2. API 实时调用
    3. 历史缓存回退（API 返回空数据时降级使用最近一次有效缓存）
    """
    if source_type not in _SOURCE_REGISTRY:
        raise ValueError(f"未知数据源类型: {source_type}")

    # 1. 当日新鲜缓存命中（且数据非空）
    if not force_refresh:
        cached = _get_cached_source(db, stock_code, source_type)
        if cached is not None:
            data, ts = cached
            if not _is_empty_data(data):
                return data, ts, True

    # 2. 调用 API
    fetch_fn, needs_name, _priority = _SOURCE_REGISTRY[source_type]
    if needs_name:
        data = fetch_fn(stock_name)
    else:
        data = fetch_fn()

    # API 返回有效数据 → 写入缓存并返回
    if not _is_empty_data(data):
        ts = _save_source_cache(db, stock_code, source_type, data)
        return data, ts, False

    # 3. API 返回空数据 → 回退到最近历史缓存
    history = _get_latest_history_cache(db, stock_code, source_type)
    if history is not None:
        hist_data, hist_ts = history
        logger.info(
            "数据源 %s 回退到历史缓存 stock=%s ts=%s",
            source_type, stock_code, hist_ts.strftime("%Y-%m-%d %H:%M"),
        )
        return hist_data, hist_ts, True

    # 无任何缓存 — 不写入空记录，避免污染缓存
    logger.info(
        "数据源 %s 无有效数据且无历史缓存 stock=%s（跳过缓存写入）",
        source_type, stock_code,
    )
    return data, datetime.now(), False


def get_data_source_cached_only(
    db: Session,
    stock_code: str,
    source_type: str,
) -> tuple[dict, datetime] | None:
    """仅查询缓存，不触发 API 调用。未命中返回 None。"""
    return _get_cached_source(db, stock_code, source_type)


def parallel_get_data_sources(
    db: Session,
    stock_code: str,
    stock_name: str,
    source_types: list[str],
    force_refresh: bool = False,
) -> dict[str, dict]:
    """并行获取多个数据源。每个线程创建独立 DB Session 避免跨线程问题。

    返回 {source_type: data} 字典。
    """
    from app.db.database import SessionLocal

    results: dict[str, dict] = {}

    def _fetch_one(source_type: str) -> tuple[str, dict]:
        thread_db = SessionLocal()
        try:
            data, _, _ = get_data_source(thread_db, stock_code, stock_name, source_type, force_refresh)
            return source_type, data
        except Exception as exc:
            logger.warning("并行获取数据源失败 type=%s: %s", source_type, exc)
            return source_type, {}
        finally:
            thread_db.close()

    # 按优先级排序：综合搜索 API (0) > AKShare 兜底 (1) > query2data (2)
    # ThreadPoolExecutor 按提交顺序分配 worker，优先提交的先执行，
    # 让不易触发熔断的数据源先跑，减少额度浪费。
    sorted_types = sorted(
        source_types,
        key=lambda st: _SOURCE_REGISTRY.get(st, (None, None, 99))[2],
    )

    with ThreadPoolExecutor(max_workers=min(len(sorted_types), 8)) as executor:
        futures = {executor.submit(_fetch_one, st): st for st in sorted_types}
        for future in as_completed(futures):
            st, data = future.result()
            results[st] = data

    return results
