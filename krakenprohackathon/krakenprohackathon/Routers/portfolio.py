from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Portfolio, Trade, TradeStatus

router = APIRouter()


@router.get("/")
def get_portfolio(db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        portfolio = Portfolio(
            balance=100000.0,
            initial_balance=100000.0,
            total_pnl=0.0,
            total_trades=0,
            winning_trades=0,
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

    open_trades  = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).count()
    win_rate     = (
        round((portfolio.winning_trades / portfolio.total_trades) * 100, 1)
        if portfolio.total_trades and portfolio.total_trades > 0
        else 0.0
    )
    total_return = (
        round(((portfolio.balance - portfolio.initial_balance) / portfolio.initial_balance) * 100, 2)
        if portfolio.initial_balance and portfolio.initial_balance > 0
        else 0.0
    )

    return {
        "balance":          round(portfolio.balance, 2),
        "initial_balance":  round(portfolio.initial_balance, 2),
        "total_pnl":        round(portfolio.total_pnl or 0.0, 2),
        "total_trades":     portfolio.total_trades or 0,
        "winning_trades":   portfolio.winning_trades or 0,
        "open_trades":      open_trades,
        "win_rate":         win_rate,
        "total_return_pct": total_return,
    }


@router.post("/reset")
def reset_portfolio(db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        portfolio = Portfolio()
        db.add(portfolio)

    portfolio.balance         = 100000.0
    portfolio.initial_balance = 100000.0
    portfolio.total_pnl       = 0.0
    portfolio.total_trades    = 0
    portfolio.winning_trades  = 0

    db.query(Trade).delete()
    db.commit()
    return {"message": "Portfolio reset to $100,000", "balance": 100000.0}


class PortfolioPatch(BaseModel):
    balance: float


@router.patch("/")
def patch_portfolio(payload: PortfolioPatch, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    portfolio.balance = round(payload.balance, 2)
    db.commit()
    db.refresh(portfolio)
    return {
        "balance":          round(portfolio.balance, 2),
        "initial_balance":  round(portfolio.initial_balance, 2),
        "total_pnl":        round(portfolio.total_pnl or 0.0, 2),
        "total_trades":     portfolio.total_trades or 0,
        "winning_trades":   portfolio.winning_trades or 0,
    }