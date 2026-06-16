"""Token 成本监控 API — Dashboard 统计 + 预算管理。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import LLMUsageLog, TokenBudget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/token", tags=["token"])


# ------------------------------------------------------------------
# 使用量统计
# ------------------------------------------------------------------

@router.get("/usage/today")
def get_today_usage(db: Session = Depends(get_db)):
    """今日 Token 使用统计。"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(
        sa_func.sum(LLMUsageLog.input_tokens).label("input_tokens"),
        sa_func.sum(LLMUsageLog.output_tokens).label("output_tokens"),
        sa_func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
        sa_func.sum(LLMUsageLog.cost_yuan).label("total_cost"),
        sa_func.count(LLMUsageLog.id).label("call_count"),
        sa_func.avg(LLMUsageLog.latency_ms).label("avg_latency_ms"),
    ).filter(LLMUsageLog.created_at >= today_start).first()

    return {
        "date": today_start.strftime("%Y-%m-%d"),
        "input_tokens": rows.input_tokens or 0,
        "output_tokens": rows.output_tokens or 0,
        "total_tokens": rows.total_tokens or 0,
        "total_cost_yuan": round(rows.total_cost or 0, 4),
        "call_count": rows.call_count or 0,
        "avg_latency_ms": int(rows.avg_latency_ms or 0),
    }


@router.get("/usage/history")
def get_usage_history(days: int = 30, db: Session = Depends(get_db)):
    """历史 Token 使用趋势（按天聚合）。"""
    since = datetime.now() - timedelta(days=days)
    rows = db.query(
        sa_func.date(LLMUsageLog.created_at).label("date"),
        sa_func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
        sa_func.sum(LLMUsageLog.cost_yuan).label("total_cost"),
        sa_func.count(LLMUsageLog.id).label("call_count"),
    ).filter(
        LLMUsageLog.created_at >= since,
    ).group_by(
        sa_func.date(LLMUsageLog.created_at),
    ).order_by(
        sa_func.date(LLMUsageLog.created_at),
    ).all()

    return [
        {
            "date": str(r.date),
            "total_tokens": r.total_tokens or 0,
            "total_cost_yuan": round(r.total_cost or 0, 4),
            "call_count": r.call_count or 0,
        }
        for r in rows
    ]


@router.get("/usage/by-caller")
def get_usage_by_caller(days: int = 7, db: Session = Depends(get_db)):
    """按 Agent/Caller 维度的 Token 使用分布。"""
    since = datetime.now() - timedelta(days=days)
    rows = db.query(
        LLMUsageLog.caller,
        sa_func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
        sa_func.sum(LLMUsageLog.cost_yuan).label("total_cost"),
        sa_func.count(LLMUsageLog.id).label("call_count"),
        sa_func.avg(LLMUsageLog.latency_ms).label("avg_latency_ms"),
    ).filter(
        LLMUsageLog.created_at >= since,
    ).group_by(
        LLMUsageLog.caller,
    ).all()

    return [
        {
            "caller": r.caller,
            "total_tokens": r.total_tokens or 0,
            "total_cost_yuan": round(r.total_cost or 0, 4),
            "call_count": r.call_count or 0,
            "avg_latency_ms": int(r.avg_latency_ms or 0),
        }
        for r in rows
    ]


# ------------------------------------------------------------------
# 预算管理
# ------------------------------------------------------------------

@router.get("/budget/status")
def get_budget_status(db: Session = Depends(get_db)):
    """获取预算使用状态。"""
    # 获取预算配置（没有则创建默认值）
    budget = db.query(TokenBudget).filter(TokenBudget.period == "daily").first()
    if not budget:
        budget = TokenBudget(
            period="daily",
            budget_tokens=1000000,
            budget_yuan=10.0,
            alert_threshold=0.8,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

    # 今日使用量
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    usage = db.query(
        sa_func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
        sa_func.sum(LLMUsageLog.cost_yuan).label("total_cost"),
    ).filter(LLMUsageLog.created_at >= today_start).first()

    used_tokens = usage.total_tokens or 0
    used_cost = usage.total_cost or 0

    token_usage_ratio = used_tokens / budget.budget_tokens if budget.budget_tokens > 0 else 0
    cost_usage_ratio = used_cost / budget.budget_yuan if budget.budget_yuan > 0 else 0
    usage_ratio = max(token_usage_ratio, cost_usage_ratio)

    # 降级状态判断
    if usage_ratio >= 1.0:
        degradation_level = "full"   # 全部走 fallback
    elif usage_ratio >= 0.95:
        degradation_level = "high"   # 跳过上游 Agent LLM
    elif usage_ratio >= budget.alert_threshold:
        degradation_level = "low"    # 降低 max_tokens
    else:
        degradation_level = "none"

    return {
        "period": budget.period,
        "budget_tokens": budget.budget_tokens,
        "budget_yuan": budget.budget_yuan,
        "used_tokens": used_tokens,
        "used_cost_yuan": round(used_cost, 4),
        "usage_ratio": round(usage_ratio, 4),
        "alert_threshold": budget.alert_threshold,
        "degradation_level": degradation_level,
    }


@router.put("/budget")
def update_budget(
    budget_tokens: int = 1000000,
    budget_yuan: float = 10.0,
    alert_threshold: float = 0.8,
    db: Session = Depends(get_db),
):
    """更新每日预算配置。"""
    budget = db.query(TokenBudget).filter(TokenBudget.period == "daily").first()
    if not budget:
        budget = TokenBudget(period="daily")
        db.add(budget)

    budget.budget_tokens = budget_tokens
    budget.budget_yuan = budget_yuan
    budget.alert_threshold = alert_threshold
    db.commit()
    return {"message": "预算配置已更新", "budget_tokens": budget_tokens, "budget_yuan": budget_yuan}


# ------------------------------------------------------------------
# 最近调用记录
# ------------------------------------------------------------------

@router.get("/usage/recent")
def get_recent_calls(limit: int = 20, db: Session = Depends(get_db)):
    """最近的 LLM 调用记录。"""
    rows = db.query(LLMUsageLog).order_by(
        LLMUsageLog.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": r.id,
            "model": r.model,
            "caller": r.caller,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "total_tokens": r.total_tokens,
            "latency_ms": r.latency_ms,
            "cost_yuan": round(r.cost_yuan, 6),
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
