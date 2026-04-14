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
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 数据源注册表
# ------------------------------------------------------------------

# key: source_type, value: (fetch_fn, needs_stock_name)
# fetch_fn 签名: (stock_name: str) -> dict  或  () -> dict
_SOURCE_REGISTRY: dict[str, tuple[Callable[..., dict], bool]] = {
    "hithink_news":         (fetch_hithink_news, True),
    "announcements":        (fetch_hithink_announcements, True),
    "industry_valuation":   (fetch_hithink_industry_data, True),
    "market_data":          (fetch_hithink_market_data, True),
    "industry_finance":     (fetch_hithink_industry_finance, True),
    "industry_peers":       (fetch_hithink_industry_peers, True),
    "hithink_index":        (fetch_hithink_index_data, False),
    "reports":              (fetch_hithink_reports, True),
    "basicinfo":            (fetch_hithink_basicinfo, True),
    "business":             (fetch_hithink_business_data, True),
    "shareholders":         (fetch_hithink_shareholders, True),
    "concept_boards":       (fetch_concept_boards, True),
    "north_flow":           (fetch_north_flow, False),
    "market_overview":      (fetch_market_overview, False),
    "hithink_macro":        (fetch_hithink_macro_indicators, False),
    "hithink_events":       (fetch_hithink_events, True),
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

def get_data_source(
    db: Session,
    stock_code: str,
    stock_name: str,
    source_type: str,
    force_refresh: bool = False,
) -> tuple[dict, datetime, bool]:
    """获取数据源。返回 (data, timestamp, from_cache)。

    优先返回缓存；缓存未命中或 force_refresh 时调用 API 并写入缓存。
    """
    if source_type not in _SOURCE_REGISTRY:
        raise ValueError(f"未知数据源类型: {source_type}")

    # 缓存命中
    if not force_refresh:
        cached = _get_cached_source(db, stock_code, source_type)
        if cached is not None:
            data, ts = cached
            return data, ts, True

    # 调用 API
    fetch_fn, needs_name = _SOURCE_REGISTRY[source_type]
    if needs_name:
        data = fetch_fn(stock_name)
    else:
        data = fetch_fn()

    ts = _save_source_cache(db, stock_code, source_type, data)
    return data, ts, False


def get_data_source_cached_only(
    db: Session,
    stock_code: str,
    source_type: str,
) -> tuple[dict, datetime] | None:
    """仅查询缓存，不触发 API 调用。未命中返回 None。"""
    return _get_cached_source(db, stock_code, source_type)
