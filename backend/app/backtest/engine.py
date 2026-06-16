"""回测引擎核心 — 基于历史快照的 Agent 推荐回测。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backtest.metrics import calculate_metrics, BacktestMetrics

logger = logging.getLogger(__name__)


@dataclass
class SimTrade:
    """模拟交易记录。"""
    entry_date: str
    exit_date: str
    signal: str          # buy / sell
    confidence: float
    entry_price: float
    exit_price: float
    return_pct: float    # 收益率百分比
    hold_days: int
    is_win: bool


@dataclass
class BacktestReport:
    """回测报告。"""
    stock_code: str
    start_date: str
    end_date: str
    metrics: BacktestMetrics
    trades: list[SimTrade] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)  # [{date, value}]

    def to_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "metrics": asdict(self.metrics),
            "trades": [asdict(t) for t in self.trades],
            "equity_curve": self.equity_curve,
        }


class BacktestEngine:
    """基于历史快照的 Agent 推荐回测引擎。

    回测逻辑:
    1. 从 DailyAgentSnapshot 取历史 enhanced_advice 快照（含 signal + confidence）
    2. 从 KlineCache 取同期实际行情
    3. 模拟交易: confidence > threshold 的信号 → 持仓 hold_days 天后平仓
    4. 计算各项指标
    """

    def __init__(
        self,
        db: Session,
        hold_days: int = 3,
        confidence_threshold: float = 0.5,
    ) -> None:
        self._db = db
        self._hold_days = hold_days
        self._confidence_threshold = confidence_threshold

    def run(self, stock_code: str, start_date: str = "", end_date: str = "") -> BacktestReport:
        """运行回测。

        Args:
            stock_code: 股票代码
            start_date: 起始日期（YYYY-MM-DD），默认全部
            end_date: 结束日期，默认今天
        """
        # 1. 获取历史信号
        signals = self._get_signals(stock_code, start_date, end_date)
        if not signals:
            return BacktestReport(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                metrics=BacktestMetrics.empty(),
            )

        # 2. 获取行情数据
        kline_map = self._get_kline_map(stock_code)
        if not kline_map:
            return BacktestReport(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                metrics=BacktestMetrics.empty(),
            )

        # 3. 模拟交易
        trades = self._simulate_trades(signals, kline_map)

        # 4. 计算指标
        metrics = calculate_metrics(trades)

        # 5. 构建净值曲线
        equity_curve = self._build_equity_curve(trades)

        actual_start = signals[0]["date"] if signals else start_date
        actual_end = signals[-1]["date"] if signals else end_date

        report = BacktestReport(
            stock_code=stock_code,
            start_date=actual_start,
            end_date=actual_end,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
        )

        # 6. 持久化结果
        self._save_report(report)

        return report

    def _get_signals(self, stock_code: str, start_date: str, end_date: str) -> list[dict]:
        """从 DailyAgentSnapshot 获取 enhanced_advice 历史信号。"""
        from app.models.models import DailyAgentSnapshot

        query = self._db.query(DailyAgentSnapshot).filter(
            DailyAgentSnapshot.agent_type == "enhanced_advice",
            DailyAgentSnapshot.stock_code == stock_code,
        )
        if start_date:
            query = query.filter(DailyAgentSnapshot.date >= start_date)
        if end_date:
            query = query.filter(DailyAgentSnapshot.date <= end_date)

        rows = query.order_by(DailyAgentSnapshot.date.asc()).all()

        signals = []
        for row in rows:
            try:
                data = json.loads(row.snapshot_data)
                signal = data.get("signal", "hold")
                confidence = data.get("confidence", 0)
                if signal in ("buy", "sell") and confidence >= self._confidence_threshold:
                    signals.append({
                        "date": row.date,
                        "signal": signal,
                        "confidence": confidence,
                    })
            except (json.JSONDecodeError, AttributeError):
                continue

        return signals

    def _get_kline_map(self, stock_code: str) -> dict[str, dict]:
        """获取 K 线数据映射 {date: {open, close, high, low}}。"""
        from app.models.models import KlineCache

        rows = self._db.query(KlineCache).filter(
            KlineCache.stock_code == stock_code,
            KlineCache.period == "daily",
        ).order_by(KlineCache.date.asc()).all()

        return {
            row.date: {
                "open": row.open,
                "close": row.close,
                "high": row.high,
                "low": row.low,
                "volume": row.volume,
            }
            for row in rows
        }

    def _simulate_trades(self, signals: list[dict], kline_map: dict[str, dict]) -> list[SimTrade]:
        """将信号转化为模拟交易。"""
        sorted_dates = sorted(kline_map.keys())
        date_index = {d: i for i, d in enumerate(sorted_dates)}

        trades: list[SimTrade] = []
        last_exit_idx = -1  # 避免重叠持仓

        for sig in signals:
            entry_date = sig["date"]
            if entry_date not in date_index:
                continue
            entry_idx = date_index[entry_date]

            # 避免重叠
            if entry_idx <= last_exit_idx:
                continue

            exit_idx = entry_idx + self._hold_days
            if exit_idx >= len(sorted_dates):
                continue

            exit_date = sorted_dates[exit_idx]
            entry_price = kline_map[entry_date]["close"]
            exit_price = kline_map[exit_date]["close"]

            if entry_price <= 0:
                continue

            # 计算收益
            if sig["signal"] == "buy":
                return_pct = (exit_price - entry_price) / entry_price * 100
            else:  # sell signal → 做空逻辑（用跌幅作为收益）
                return_pct = (entry_price - exit_price) / entry_price * 100

            trades.append(SimTrade(
                entry_date=entry_date,
                exit_date=exit_date,
                signal=sig["signal"],
                confidence=sig["confidence"],
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=round(return_pct, 4),
                hold_days=self._hold_days,
                is_win=return_pct > 0,
            ))
            last_exit_idx = exit_idx

        return trades

    def _build_equity_curve(self, trades: list[SimTrade]) -> list[dict]:
        """构建累计净值曲线。"""
        if not trades:
            return []

        equity = 1.0
        curve = [{"date": trades[0].entry_date, "value": 1.0}]

        for t in trades:
            equity *= (1 + t.return_pct / 100)
            curve.append({"date": t.exit_date, "value": round(equity, 4)})

        return curve

    def _save_report(self, report: BacktestReport) -> None:
        """持久化回测结果。"""
        from app.models.models import BacktestResult
        from datetime import datetime as dt

        try:
            # 覆盖同 stock_code 的最新报告
            existing = self._db.query(BacktestResult).filter(
                BacktestResult.stock_code == report.stock_code,
            ).first()

            data = report.to_dict()
            if existing:
                existing.start_date = report.start_date
                existing.end_date = report.end_date
                existing.total_signals = report.metrics.total_signals
                existing.win_rate = report.metrics.win_rate
                existing.avg_return = report.metrics.avg_return
                existing.sharpe_ratio = report.metrics.sharpe_ratio
                existing.max_drawdown = report.metrics.max_drawdown
                existing.accuracy = report.metrics.accuracy
                existing.detail_json = json.dumps(data, ensure_ascii=False)
                existing.created_at = dt.now()
            else:
                row = BacktestResult(
                    stock_code=report.stock_code,
                    start_date=report.start_date,
                    end_date=report.end_date,
                    total_signals=report.metrics.total_signals,
                    win_rate=report.metrics.win_rate,
                    avg_return=report.metrics.avg_return,
                    sharpe_ratio=report.metrics.sharpe_ratio,
                    max_drawdown=report.metrics.max_drawdown,
                    accuracy=report.metrics.accuracy,
                    detail_json=json.dumps(data, ensure_ascii=False),
                )
                self._db.add(row)
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.warning("回测结果保存失败: %s", e)
