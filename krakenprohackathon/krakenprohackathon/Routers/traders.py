from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Trade, TradeStatus

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


class ManualTradeRequest(BaseModel):
    symbol:         str
    side:           str
    quantity:       float
    entry_price:    float
    take_profit:    Optional[float] = None
    stop_loss:      Optional[float] = None
    notional:       Optional[float] = None
    strategy:       Optional[str]   = "Manual"
    reason:         Optional[str]   = "Manual order"
    ai_confidence:  Optional[float] = None
    mc_probability: Optional[float] = None


@router.post("/")
def create_manual_trade(payload: ManualTradeRequest, db: Session = Depends(get_db)):
    try:
        new_trade = Trade(
            symbol      = payload.symbol,
            market_type = "crypto" if payload.symbol.endswith("USDT") else "stock",
            side        = payload.side,
            quantity    = payload.quantity,
            entry_price = payload.entry_price,
            take_profit = payload.take_profit,
            stop_loss   = payload.stop_loss,
            notional    = payload.notional,
            strategy    = payload.strategy,
            reason      = payload.reason,
            status      = TradeStatus.OPEN,
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)
        return {
            "id":          new_trade.id,
            "symbol":      new_trade.symbol,
            "side":        new_trade.side,
            "entry_price": new_trade.entry_price,
            "quantity":    new_trade.quantity,
            "notional":    new_trade.notional,
            "take_profit": new_trade.take_profit,
            "stop_loss":   new_trade.stop_loss,
            "status":      new_trade.status.value,
            "strategy":    new_trade.strategy,
            "reason":      new_trade.reason,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))