from datetime import datetime
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import FocusStock, TradeRecord, StockPosition, RecordMode, TradeType
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
    db.flush()  # 确保 update 落地后再 insert，防止并发请求产生多条 active
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
    refresh: bool = False,
    db: Session = Depends(get_db),
):
    """获取K线数据"""
    from app.services.stock_service import get_kline_data
    try:
        return get_kline_data(stock_code, period, start_date, end_date, db=db, force_refresh=refresh)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{stock_code}/analysis")
def get_stock_analysis(
    stock_code: str,
    period: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
    refresh: bool = False,
    db: Session = Depends(get_db),
):
    """获取完整的股票分析（K线 + 技术指标 + 买卖建议）"""
    from app.services.stock_service import get_kline_data, calculate_indicators
    from app.services.advice_service import generate_advice

    try:
        kline = get_kline_data(stock_code, period, start_date, end_date, db=db, force_refresh=refresh)
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


# ==================== 对比基准 ====================

@router.get("/stocks/{stock_code}/benchmark")
def get_stock_benchmark(
    stock_code: str,
    period: str = "daily",
    days: int = 120,
    db: Session = Depends(get_db),
):
    """获取个股 vs 大盘指数的对比基准数据"""
    from app.services.stock_service import get_benchmark_comparison

    # 获取股票名称
    focus = db.query(FocusStock).filter(
        FocusStock.stock_code == stock_code,
        FocusStock.is_active == 1,
    ).first()
    stock_name = focus.stock_name if focus else stock_code

    try:
        return get_benchmark_comparison(stock_code, stock_name, period, days, db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """创建交易记录，实时交易模式下自动同步持仓"""
    record = TradeRecord(**data.model_dump())
    db.add(record)

    # 实时交易模式：同步更新持仓
    if data.record_mode == RecordMode.REALTIME:
        position = db.query(StockPosition).filter(
            StockPosition.stock_code == data.stock_code
        ).first()

        if data.trade_type.value == "buy":
            if position:
                # 加权平均成本
                old_total = position.cost_price * position.quantity
                new_total = data.price * data.quantity
                new_quantity = position.quantity + data.quantity
                position.cost_price = (old_total + new_total) / new_quantity
                position.quantity = new_quantity
            else:
                # 自动创建持仓
                position = StockPosition(
                    stock_code=data.stock_code,
                    stock_name=data.stock_name,
                    cost_price=data.price,
                    quantity=data.quantity,
                    first_buy_date=data.traded_at,
                )
                db.add(position)

        elif data.trade_type.value == "sell":
            if not position or position.quantity <= 0:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail="无持仓记录，无法卖出",
                )
            if data.quantity > position.quantity:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"卖出数量({data.quantity})超过持仓数量({position.quantity})",
                )
            position.quantity -= data.quantity

    db.commit()
    db.refresh(record)
    return record


@router.post("/trades/import")
async def import_trades(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """批量导入同花顺导出的交易记录（GBK 编码 TSV / .xls 文件）"""
    content = await file.read()

    # 尝试 GBK TSV 解析（同花顺导出的 .xls 实际是 TSV 文本）
    try:
        df = pd.read_csv(BytesIO(content), sep="\t", encoding="gbk")
    except Exception:
        try:
            df = pd.read_csv(BytesIO(content), sep="\t", encoding="utf-8")
        except Exception:
            raise HTTPException(status_code=400, detail="文件解析失败，仅支持同花顺导出的 xls/tsv 文件")

    # 验证必需列
    required_cols = {"成交日期", "证券代码", "证券名称", "操作", "成交均价", "成交数量"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少必需列: {', '.join(missing)}")

    success_count = 0
    skip_count = 0
    dup_count = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        line = idx + 2  # Excel 行号（含表头）
        try:
            # 解析操作类型
            op = str(row["操作"]).strip()
            if "买入" in op:
                trade_type = TradeType.BUY
            elif "卖出" in op:
                trade_type = TradeType.SELL
            else:
                skip_count += 1
                continue  # 跳过非买卖操作（如申购、配股等）

            # 解析日期：支持 20260402 整数 或 2026-04-02 字符串
            raw_date = row["成交日期"]
            if isinstance(raw_date, (int, float)):
                date_str = str(int(raw_date))
                traded_at = datetime.strptime(date_str, "%Y%m%d")
            else:
                traded_at = datetime.strptime(str(raw_date).strip(), "%Y-%m-%d")

            # 股票代码补零
            code_raw = str(int(row["证券代码"])).zfill(6)
            stock_name = str(row["证券名称"]).strip()
            price = float(row["成交均价"])
            quantity = abs(int(row["成交数量"]))  # 卖出数量为负，取绝对值

            if quantity == 0 or price <= 0:
                skip_count += 1
                continue

            # 去重：按日期+代码+价格+数量+方向判断
            exists = db.query(TradeRecord).filter(
                TradeRecord.stock_code == code_raw,
                TradeRecord.trade_type == trade_type,
                TradeRecord.price == price,
                TradeRecord.quantity == quantity,
                TradeRecord.traded_at == traded_at,
            ).first()
            if exists:
                dup_count += 1
                continue

            record = TradeRecord(
                stock_code=code_raw,
                stock_name=stock_name,
                trade_type=trade_type,
                price=price,
                quantity=quantity,
                traded_at=traded_at,
                record_mode=RecordMode.BACKFILL,
            )
            db.add(record)
            success_count += 1

        except Exception as e:
            errors.append(f"第{line}行: {str(e)}")

    db.commit()
    return {
        "success": success_count,
        "skipped": skip_count,
        "duplicated": dup_count,
        "errors": errors,
        "total": len(df),
    }


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
    """删除交易记录，实时模式记录会反向调整持仓"""
    record = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="交易记录不存在")

    # 实时交易模式：反向调整持仓
    if record.record_mode == RecordMode.REALTIME:
        position = db.query(StockPosition).filter(
            StockPosition.stock_code == record.stock_code
        ).first()
        if position:
            if record.trade_type.value == "buy":
                # 删除买入记录 → 减仓
                if position.quantity >= record.quantity:
                    if position.quantity == record.quantity:
                        # 持仓清零时按原价还原成本无意义，直接删持仓
                        db.delete(position)
                    else:
                        old_total = position.cost_price * position.quantity
                        new_quantity = position.quantity - record.quantity
                        position.cost_price = (
                            (old_total - record.price * record.quantity) / new_quantity
                        )
                        position.quantity = new_quantity
            elif record.trade_type.value == "sell":
                # 删除卖出记录 → 加回持仓
                position.quantity += record.quantity

    db.delete(record)
    db.commit()
    return {"message": "删除成功"}


@router.post("/trades/batch-delete")
def batch_delete_trades(
    ids: list[int],
    db: Session = Depends(get_db),
):
    """批量删除交易记录，实时交易记录会反向调整持仓"""
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的记录")

    records = db.query(TradeRecord).filter(TradeRecord.id.in_(ids)).all()
    deleted = 0
    realtime_adjusted = 0

    for record in records:
        # 实时交易模式：反向调整持仓
        if record.record_mode == RecordMode.REALTIME:
            position = db.query(StockPosition).filter(
                StockPosition.stock_code == record.stock_code
            ).first()
            if position:
                if record.trade_type.value == "buy":
                    if position.quantity >= record.quantity:
                        if position.quantity == record.quantity:
                            db.delete(position)
                        else:
                            old_total = position.cost_price * position.quantity
                            new_qty = position.quantity - record.quantity
                            position.cost_price = (
                                (old_total - record.price * record.quantity)
                                / new_qty
                            )
                            position.quantity = new_qty
                elif record.trade_type.value == "sell":
                    position.quantity += record.quantity
            realtime_adjusted += 1

        db.delete(record)
        deleted += 1

    db.commit()
    return {
        "deleted": deleted,
        "realtime_adjusted": realtime_adjusted,
        "total": len(ids),
    }


# ==================== 炒股画像 ====================

@router.get("/profile")
def get_profile(
    stock_code: str | None = None,
    db: Session = Depends(get_db),
):
    """获取炒股画像"""
    from app.services.profile_service import generate_profile
    return generate_profile(db, stock_code)
