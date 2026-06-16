"""回测指标计算 — 胜率、夏普比率、最大回撤等。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.backtest.engine import SimTrade


@dataclass
class BacktestMetrics:
    """回测结果指标。"""
    total_signals: int
    total_trades: int
    win_rate: float          # 0-1
    avg_return: float        # 百分比
    sharpe_ratio: float
    max_drawdown: float      # 百分比
    accuracy: float          # 信号方向准确率
    profit_factor: float     # 总利润/总亏损
    total_return: float      # 累计收益率百分比

    @classmethod
    def empty(cls) -> "BacktestMetrics":
        return cls(
            total_signals=0,
            total_trades=0,
            win_rate=0.0,
            avg_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            accuracy=0.0,
            profit_factor=0.0,
            total_return=0.0,
        )


def calculate_metrics(trades: list) -> BacktestMetrics:
    """从模拟交易列表计算各项指标。"""
    if not trades:
        return BacktestMetrics.empty()

    total = len(trades)
    wins = sum(1 for t in trades if t.is_win)
    returns = [t.return_pct for t in trades]

    # 胜率
    win_rate = wins / total if total > 0 else 0

    # 平均收益
    avg_return = sum(returns) / total if total > 0 else 0

    # 夏普比率 (年化，假设日频交易，rf = 1.5%/252)
    rf_daily = 0.015 / 252
    if len(returns) >= 2:
        mean_r = sum(returns) / len(returns) / 100  # 转换为小数
        std_r = _std(returns) / 100
        if std_r > 0:
            # 年化夏普 = (mean - rf) / std * sqrt(252)
            sharpe_ratio = (mean_r - rf_daily) / std_r * math.sqrt(252)
        else:
            sharpe_ratio = 0.0
    else:
        sharpe_ratio = 0.0

    # 最大回撤
    max_drawdown = _max_drawdown(returns)

    # 信号准确率（与胜率一致，因为我们只取 buy/sell 信号）
    accuracy = win_rate

    # 利润因子
    total_profit = sum(r for r in returns if r > 0)
    total_loss = abs(sum(r for r in returns if r < 0))
    profit_factor = total_profit / total_loss if total_loss > 0 else float("inf") if total_profit > 0 else 0

    # 累计收益率
    cumulative = 1.0
    for r in returns:
        cumulative *= (1 + r / 100)
    total_return = (cumulative - 1) * 100

    return BacktestMetrics(
        total_signals=total,
        total_trades=total,
        win_rate=round(win_rate, 4),
        avg_return=round(avg_return, 4),
        sharpe_ratio=round(sharpe_ratio, 4),
        max_drawdown=round(max_drawdown, 4),
        accuracy=round(accuracy, 4),
        profit_factor=round(profit_factor, 4) if profit_factor != float("inf") else 999.0,
        total_return=round(total_return, 4),
    )


def _std(values: list[float]) -> float:
    """计算标准差。"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _max_drawdown(returns_pct: list[float]) -> float:
    """从收益序列计算最大回撤（百分比）。"""
    if not returns_pct:
        return 0.0

    # 构建累计净值
    equity = [1.0]
    for r in returns_pct:
        equity.append(equity[-1] * (1 + r / 100))

    # 计算最大回撤
    peak = equity[0]
    max_dd = 0.0
    for v in equity[1:]:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return max_dd
