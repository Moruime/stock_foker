from sqlalchemy.orm import Session
from app.models.models import TradeRecord, TradeType
from collections import Counter


def generate_profile(db: Session, stock_code: str | None = None) -> dict:
    """基于交易记录生成炒股画像"""
    query = db.query(TradeRecord)
    if stock_code:
        query = query.filter(TradeRecord.stock_code == stock_code)
    records = query.order_by(TradeRecord.traded_at.desc()).all()

    if not records:
        return _empty_profile()

    total = len(records)
    buys = [r for r in records if r.trade_type == TradeType.BUY]
    sells = [r for r in records if r.trade_type == TradeType.SELL]

    # 有结果的交易
    closed = [r for r in records if r.actual_result is not None]
    wins = [r for r in closed if r.actual_result > 0]
    losses = [r for r in closed if r.actual_result < 0]

    win_rate = len(wins) / len(closed) if closed else 0
    avg_profit = (
        sum(r.actual_result for r in wins) / len(wins) if wins else 0
    )
    avg_loss = (
        sum(r.actual_result for r in losses) / len(losses) if losses else 0
    )
    profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0

    # 持仓周期分析
    hold_days_list = [
        r.expected_hold_days for r in records if r.expected_hold_days
    ]
    avg_hold_days = (
        sum(hold_days_list) / len(hold_days_list) if hold_days_list else 0
    )

    # 时间框架偏好
    if avg_hold_days <= 5:
        preferred_tf = "短线"
    elif avg_hold_days <= 30:
        preferred_tf = "中线"
    else:
        preferred_tf = "长线"

    # 交易频率
    if total >= 20:
        freq = "高频"
    elif total >= 5:
        freq = "中频"
    else:
        freq = "低频"

    # 情绪判断准确率
    sentiment_records = [
        r for r in closed if r.market_sentiment is not None
    ]
    sentiment_correct = 0
    for r in sentiment_records:
        if r.actual_result is not None:
            if r.market_sentiment == "optimistic" and r.actual_result > 0:
                sentiment_correct += 1
            elif r.market_sentiment == "pessimistic" and r.actual_result < 0:
                sentiment_correct += 1
    sentiment_accuracy = (
        sentiment_correct / len(sentiment_records) if sentiment_records else 0
    )

    # 常见买卖理由
    buy_reasons = Counter(
        r.reason for r in buys if r.reason
    ).most_common(5)
    sell_reasons = Counter(
        r.reason for r in sells if r.reason
    ).most_common(5)

    return {
        "total_trades": total,
        "win_rate": round(win_rate, 4),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_loss_ratio": round(profit_loss_ratio, 2),
        "avg_hold_days": round(avg_hold_days, 1),
        "trade_frequency": freq,
        "preferred_time_frame": preferred_tf,
        "sentiment_accuracy": round(sentiment_accuracy, 4),
        "common_buy_reasons": [
            {"reason": r, "count": c} for r, c in buy_reasons
        ],
        "common_sell_reasons": [
            {"reason": r, "count": c} for r, c in sell_reasons
        ],
    }


def _empty_profile() -> dict:
    return {
        "total_trades": 0,
        "win_rate": 0,
        "avg_profit": 0,
        "avg_loss": 0,
        "profit_loss_ratio": 0,
        "avg_hold_days": 0,
        "trade_frequency": "无数据",
        "preferred_time_frame": "无数据",
        "sentiment_accuracy": 0,
        "common_buy_reasons": [],
        "common_sell_reasons": [],
    }
