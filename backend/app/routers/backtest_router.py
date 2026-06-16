"""回测 API 路由。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import BacktestResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run/{stock_code}")
def run_backtest(
    stock_code: str,
    start_date: str = "",
    end_date: str = "",
    hold_days: int = 3,
    confidence_threshold: float = 0.5,
    db: Session = Depends(get_db),
):
    """运行回测。

    Args:
        stock_code: 股票代码
        start_date: 起始日期（YYYY-MM-DD）
        end_date: 结束日期
        hold_days: 持仓天数
        confidence_threshold: 信号置信度门槛
    """
    from app.backtest.engine import BacktestEngine

    engine = BacktestEngine(
        db=db,
        hold_days=hold_days,
        confidence_threshold=confidence_threshold,
    )
    report = engine.run(stock_code, start_date, end_date)
    return report.to_dict()


@router.get("/report/{stock_code}")
def get_backtest_report(stock_code: str, db: Session = Depends(get_db)):
    """获取最近的回测报告。"""
    row = db.query(BacktestResult).filter(
        BacktestResult.stock_code == stock_code,
    ).order_by(BacktestResult.created_at.desc()).first()

    if not row:
        return {"message": "未找到回测报告", "stock_code": stock_code}

    if row.detail_json:
        try:
            return json.loads(row.detail_json)
        except json.JSONDecodeError:
            pass

    return {
        "stock_code": row.stock_code,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "metrics": {
            "total_signals": row.total_signals,
            "win_rate": row.win_rate,
            "avg_return": row.avg_return,
            "sharpe_ratio": row.sharpe_ratio,
            "max_drawdown": row.max_drawdown,
            "accuracy": row.accuracy,
        },
    }


@router.get("/summary")
def get_backtest_summary(db: Session = Depends(get_db)):
    """全部股票回测汇总指标。"""
    rows = db.query(BacktestResult).order_by(BacktestResult.created_at.desc()).all()

    return [
        {
            "stock_code": r.stock_code,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "total_signals": r.total_signals,
            "win_rate": r.win_rate,
            "avg_return": r.avg_return,
            "sharpe_ratio": r.sharpe_ratio,
            "max_drawdown": r.max_drawdown,
            "accuracy": r.accuracy,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
