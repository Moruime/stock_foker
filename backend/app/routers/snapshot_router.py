"""Agent 每日快照查询路由。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import DailyAgentSnapshot
from app.models.schemas import SnapshotResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])

_VALID_AGENT_TYPES = {"sentiment", "sector", "macro", "enhanced_advice"}


def _check_agent_type(agent_type: str) -> None:
    if agent_type not in _VALID_AGENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"agent_type 必须为 {' / '.join(sorted(_VALID_AGENT_TYPES))}，收到: {agent_type}",
        )


def _row_to_response(row: DailyAgentSnapshot) -> SnapshotResponse:
    """ORM 对象 → SnapshotResponse，反序列化 JSON 字段。"""
    return SnapshotResponse(
        id=row.id,
        agent_type=row.agent_type,
        stock_code=row.stock_code,
        date=row.date,
        snapshot_data=json.loads(row.snapshot_data),
        llm_used=bool(row.llm_used),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/{agent_type}/dates")
def list_snapshot_dates(
    agent_type: str,
    stock_code: str,
    db: Session = Depends(get_db),
) -> list[str]:
    """返回指定股票 + Agent 类型下所有有记录的日期列表（降序）。"""
    _check_agent_type(agent_type)
    rows = (
        db.query(DailyAgentSnapshot.date)
        .filter(
            DailyAgentSnapshot.agent_type == agent_type,
            DailyAgentSnapshot.stock_code == stock_code,
        )
        .order_by(DailyAgentSnapshot.date.desc())
        .all()
    )
    return [r.date for r in rows]


@router.get("/{agent_type}/{date}", response_model=SnapshotResponse)
def get_snapshot(
    agent_type: str,
    date: str,
    stock_code: str,
    db: Session = Depends(get_db),
) -> SnapshotResponse:
    """返回指定日期的快照详情。"""
    _check_agent_type(agent_type)
    row = (
        db.query(DailyAgentSnapshot)
        .filter(
            DailyAgentSnapshot.agent_type == agent_type,
            DailyAgentSnapshot.stock_code == stock_code,
            DailyAgentSnapshot.date == date,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="快照不存在")
    return _row_to_response(row)
