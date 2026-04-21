from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum as SQLEnum
from database import Base
import enum
from datetime import datetime, timezone


class TradeStatus(enum.Enum):
    OPEN      = "open"
    CLOSED_TP = "closed_tp"   # hit take profit — win
    CLOSED_SL = "closed_sl"   # hit stop loss  — loss
    CLOSED    = "closed"      # manually closed or legacy


class MarketType(enum.Enum):
    CRYPTO = "crypto"
    STOCK  = "stock"


class Portfolio(Base):
    __tablename__ = "portfolios"
    id              = Column(Integer, primary_key=True, index=True)
    balance         = Column(Float, default=100000.0)
    initial_balance = Column(Float, default=100000.0)
    total_pnl       = Column(Float, default=0.0)
    total_trades    = Column(Integer, default=0)
    winning_trades  = Column(Integer, default=0)


class Trade(Base):
    __tablename__ = "trades"
    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String)
    market_type = Column(String, nullable=True)
    side        = Column(String)
    entry_price = Column(Float)
    exit_price  = Column(Float, nullable=True)
    quantity    = Column(Float)
    notional    = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    stop_loss   = Column(Float, nullable=True)
    pnl         = Column(Float, nullable=True)
    status      = Column(
        SQLEnum(TradeStatus, values_callable=lambda x: [e.value for e in x]),
        default=TradeStatus.OPEN,
    )
    strategy    = Column(String, nullable=True)
    reason      = Column(String, nullable=True)
    opened_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at   = Column(DateTime(timezone=True), nullable=True)


class BotSettings(Base):
    __tablename__ = "bot_settings"
    id                 = Column(Integer, primary_key=True, index=True)
    is_running         = Column(Boolean, default=False)
    strategy           = Column(String, default="hybrid")
    max_risk_per_trade = Column(Float, default=2.0)
    min_ai_confidence  = Column(Float, default=0.7)
