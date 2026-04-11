"""数据源 API 路由 — 独立于 Agent，提供原始数据获取/缓存端点。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import DataSourceCache
from app.services.data_source_service import (
    VALID_SOURCE_TYPES,
    get_data_source,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-source", tags=["data-source"])


@router.get("/{stock_code}/{source_type}")
def get_source(
    stock_code: str,
    source_type: str,
    stock_name: str = Query("", description="股票名称（首次获取时需要）"),
    db: Session = Depends(get_db),
):
    """获取数据源：优先返回缓存，缓存未命中则调用 API。"""
    if source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"无效的数据源类型: {source_type}")
    try:
        data, ts, from_cache = get_data_source(db, stock_code, stock_name, source_type)
        return {
            "source_type": source_type,
            "stock_code": stock_code,
            "data": data,
            "timestamp": ts.isoformat(),
            "from_cache": from_cache,
        }
    except Exception as e:
        logger.error("获取数据源失败 stock=%s type=%s: %s", stock_code, source_type, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{stock_code}/{source_type}/refresh")
def refresh_source(
    stock_code: str,
    source_type: str,
    stock_name: str = Query("", description="股票名称"),
    db: Session = Depends(get_db),
):
    """强制刷新数据源（跳过缓存重新获取）。"""
    if source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"无效的数据源类型: {source_type}")
    try:
        data, ts, _ = get_data_source(db, stock_code, stock_name, source_type, force_refresh=True)
        return {
            "source_type": source_type,
            "stock_code": stock_code,
            "data": data,
            "timestamp": ts.isoformat(),
            "from_cache": False,
        }
    except Exception as e:
        logger.error("刷新数据源失败 stock=%s type=%s: %s", stock_code, source_type, e)
        raise HTTPException(status_code=500, detail=str(e))
