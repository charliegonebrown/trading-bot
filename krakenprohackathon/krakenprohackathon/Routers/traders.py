from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Trade, TradeStatus
from typing import List

router = APIRouter()


@router.get("/")
def get_all_trades(db: Session = Depends(get_db)):
    trades = db.query(Trade).order_by(Trade.opened_at.desc()).all()
    return [
        {
            "id":           t.id,
            "symbol":       t.symbol,
            "market_type":  t.market_type,
            "side":         t.side,
            "entry_price":  t.entry_price,
            "exit_price":   t.exit_price,
            "quantity":     t.quantity,
            "notional":     t.notional,
            "take_profit":  t.take_profit,
            "stop_loss":    t.stop_loss,
            "pnl":          t.pnl,
            "status":       t.status.value if t.status else None,
            "strategy":     t.strategy,
            "reason":       t.reason,
            "opened_at":    t.opened_at.isoformat() if t.opened_at else None,
            "closed_at":    t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


@router.get("/open")
def get_open_trades(db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).all()
    return [
        {
            "id":           t.id,
            "symbol":       t.symbol,
            "market_type":  t.market_type,
            "side":         t.side,
            "entry_price":  t.entry_price,
            "quantity":     t.quantity,
            "notional":     t.notional,
            "take_profit":  t.take_profit,
            "stop_loss":    t.stop_loss,
            "status":       t.status.value if t.status else None,
            "strategy":     t.strategy,
            "reason":       t.reason,
            "opened_at":    t.opened_at.isoformat() if t.opened_at else None,
        }
        for t in trades
    ]


@router.get("/closed")
def get_closed_trades(db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(
        Trade.status != TradeStatus.OPEN
    ).order_by(Trade.closed_at.desc()).all()
    return [
        {
            "id":           t.id,
            "symbol":       t.symbol,
            "market_type":  t.market_type,
            "side":         t.side,
            "entry_price":  t.entry_price,
            "exit_price":   t.exit_price,
            "quantity":     t.quantity,
            "notional":     t.notional,
            "pnl":          t.pnl,
            "status":       t.status.value if t.status else None,
            "strategy":     t.strategy,
            "opened_at":    t.opened_at.isoformat() if t.opened_at else None,
            "closed_at":    t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


@router.delete("/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(trade)
    db.commit()
    return {"message": f"Trade {trade_id} deleted"}
