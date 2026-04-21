from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import BotSettings

router = APIRouter()


class SettingsUpdate(BaseModel):
    is_running:          bool  = None
    strategy:            str   = None
    max_risk_per_trade:  float = None
    min_ai_confidence:   float = None


@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(BotSettings).first()
    if not settings:
        # Auto-create default settings if none exist
        settings = BotSettings(
            is_running=False,
            strategy="hybrid",
            max_risk_per_trade=2.0,
            min_ai_confidence=0.7,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        "is_running":         settings.is_running,
        "strategy":           settings.strategy,
        "max_risk_per_trade": settings.max_risk_per_trade,
        "min_ai_confidence":  settings.min_ai_confidence,
    }


@router.put("/")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(BotSettings).first()
    if not settings:
        settings = BotSettings()
        db.add(settings)

    if payload.is_running is not None:
        settings.is_running = payload.is_running
    if payload.strategy is not None:
        settings.strategy = payload.strategy
    if payload.max_risk_per_trade is not None:
        settings.max_risk_per_trade = payload.max_risk_per_trade
    if payload.min_ai_confidence is not None:
        settings.min_ai_confidence = payload.min_ai_confidence

    db.commit()
    db.refresh(settings)

    return {
        "message":            "Settings updated",
        "is_running":         settings.is_running,
        "strategy":           settings.strategy,
        "max_risk_per_trade": settings.max_risk_per_trade,
        "min_ai_confidence":  settings.min_ai_confidence,
    }


@router.post("/start")
def start_bot(db: Session = Depends(get_db)):
    settings = db.query(BotSettings).first()
    if not settings:
        settings = BotSettings()
        db.add(settings)
    settings.is_running = True
    db.commit()
    return {"message": "Bot started", "is_running": True}


@router.post("/stop")
def stop_bot(db: Session = Depends(get_db)):
    settings = db.query(BotSettings).first()
    if not settings:
        settings = BotSettings()
        db.add(settings)
    settings.is_running = False
    db.commit()
    return {"message": "Bot stopped", "is_running": False}
