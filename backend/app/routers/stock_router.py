from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import FocusStock, TradeRecord, StockPosition
from app.models.schemas import (
    FocusStockCreate,
    FocusStockResponse,
    TimeFrameUpdate,
    TradeRecordCreate,
    TradeRecordResponse,
    TradeRecordUpdate,
    PositionCreate,
    PositionUpdate,
    PositionResponse,
)

router = APIRouter(prefix="/api", tags=["stocks"])


# ==================== 股票关注 ====================

@router.get("/focus", response_model=FocusStockResponse | None)
def get_focus_stock(db: Session = Depends(get_db)):
    """获取当前关注的股票"""
    stock = db.query(FocusStock).filter(FocusStock.is_active == 1).first()
    return stock


@router.post("/focus", response_model=FocusStockResponse)
def set_focus_stock(data: FocusStockCreate, db: Session = Depends(get_db)):
    """设置当前关注的股票（自动取消之前的关注）"""
    db.query(FocusStock).filter(FocusStock.is_active == 1).update(
        {"is_active": 0}
    )
    stock = FocusStock(
        stock_code=data.stock_code,
        stock_name=data.stock_name,
        time_frame=data.time_frame,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


@router.put("/focus/timeframe", response_model=FocusStockResponse)
def update_timeframe(data: TimeFrameUpdate, db: Session = Depends(get_db)):
    """更新当前关注股票的时间框架"""
    stock = db.query(FocusStock).filter(FocusStock.is_active == 1).first()
    if not stock:
        raise HTTPException(status_code=404, detail="当前没有关注的股票")
    stock.time_frame = data.time_frame
    db.commit()
    db.refresh(stock)
    return stock


@router.get("/focus/history", response_model=list[FocusStockResponse])
def get_focus_history(db: Session = Depends(get_db)):
    """获取历史关注记录"""
    stocks = (
        db.query(FocusStock)
        .order_by(FocusStock.created_at.desc())
        .limit(50)
        .all()
    )
    return stocks


# ==================== 股票搜索 ====================

@router.get("/stocks/search")
def search_stocks(keyword: str):
    """搜索股票"""
    from app.services.stock_service import search_stocks as _search
    try:
        return _search(keyword)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== K线与技术指标 ====================

@router.get("/stocks/{stock_code}/kline")
def get_stock_kline(
    stock_code: str,
    period: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """获取K线数据"""
    from app.services.stock_service import get_kline_data
    try:
        return get_kline_data(stock_code, period, start_date, end_date, db=db)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{stock_code}/analysis")
def get_stock_analysis(
    stock_code: str,
    period: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """获取完整的股票分析（K线 + 技术指标 + 买卖建议）"""
    from app.services.stock_service import get_kline_data, calculate_indicators
    from app.services.advice_service import generate_advice

    try:
        kline = get_kline_data(stock_code, period, start_date, end_date, db=db)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    indicators = calculate_indicators(kline)

    # 获取时间框架
    focus = db.query(FocusStock).filter(
        FocusStock.stock_code == stock_code,
        FocusStock.is_active == 1,
    ).first()
    time_frame = focus.time_frame.value if focus else "short"

    advice = generate_advice(indicators, kline)

    return {
        "kline_data": kline,
        "indicators": indicators,
        "advice": advice,
        "time_frame": time_frame,
    }


# ==================== 持仓管理 ====================

@router.get("/positions/{stock_code}", response_model=PositionResponse | None)
def get_position(stock_code: str, db: Session = Depends(get_db)):
    """获取指定股票的持仓信息"""
    return db.query(StockPosition).filter(StockPosition.stock_code == stock_code).first()


@router.post("/positions", response_model=PositionResponse)
def create_position(data: PositionCreate, db: Session = Depends(get_db)):
    """创建持仓记录"""
    existing = db.query(StockPosition).filter(
        StockPosition.stock_code == data.stock_code
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="该股票已有持仓记录，请使用更新接口")
    position = StockPosition(**data.model_dump())
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


@router.put("/positions/{stock_code}", response_model=PositionResponse)
def update_position(
    stock_code: str,
    data: PositionUpdate,
    db: Session = Depends(get_db),
):
    """更新持仓记录"""
    position = db.query(StockPosition).filter(
        StockPosition.stock_code == stock_code
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="持仓记录不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(position, key, value)
    db.commit()
    db.refresh(position)
    return position


@router.delete("/positions/{stock_code}")
def delete_position(stock_code: str, db: Session = Depends(get_db)):
    """删除持仓记录"""
    position = db.query(StockPosition).filter(
        StockPosition.stock_code == stock_code
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="持仓记录不存在")
    db.delete(position)
    db.commit()
    return {"message": "删除成功"}


# ==================== 交易记录 ====================

@router.get("/trades", response_model=list[TradeRecordResponse])
def list_trades(
    stock_code: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """获取交易记录"""
    query = db.query(TradeRecord)
    if stock_code:
        query = query.filter(TradeRecord.stock_code == stock_code)
    return query.order_by(TradeRecord.traded_at.desc()).limit(limit).all()


@router.post("/trades", response_model=TradeRecordResponse)
def create_trade(data: TradeRecordCreate, db: Session = Depends(get_db)):
    """创建交易记录"""
    record = TradeRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/trades/{trade_id}", response_model=TradeRecordResponse)
def update_trade(
    trade_id: int,
    data: TradeRecordUpdate,
    db: Session = Depends(get_db),
):
    """更新交易记录（补充实际结果）"""
    record = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/trades/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """删除交易记录"""
    record = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    db.delete(record)
    db.commit()
    return {"message": "删除成功"}


# ==================== 炒股画像 ====================

@router.get("/profile")
def get_profile(
    stock_code: str | None = None,
    db: Session = Depends(get_db),
):
    """获取炒股画像"""
    from app.services.profile_service import generate_profile
    return generate_profile(db, stock_code)
