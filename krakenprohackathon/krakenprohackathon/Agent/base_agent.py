import logging
from datetime import datetime, timezone
from typing import List, Dict

from Strategies.rsi_strategies import get_triple_confirmation_signal
from Strategies.ai_strategy import get_hybrid_ai_signal
from models import Trade, Portfolio, BotSettings, MarketType, TradeStatus

logger = logging.getLogger(__name__)


class HybridTradingAgent:
    def __init__(self, broker, market_type: MarketType):
        self.broker = broker
        self.market_type = market_type
        self.min_confidence     = 0.50   # FIX: score 2/4 = 0.50, was 0.65 which secretly required score≥3
        self.min_mc_probability = 45.0   # FIX: lowered from 60.0 to match the gate in ai_strategy (45%)

    async def analyze_and_decide(self, symbol: str) -> Dict:
        prices = self.broker.get_price_history(symbol, interval="60")
        if not prices or len(prices) < 30:
            return {"action": "hold", "reason": "Insufficient history or Network Error"}

        math_signal    = get_triple_confirmation_signal(prices)
        final_decision = await get_hybrid_ai_signal(
            symbol=symbol,
            prices=prices,
            market_type=self.market_type.value,
            triple_conf=math_signal,
            interval="60"
        )
        return final_decision

    def calculate_position_size(self, balance: float, price: float, risk_pct: float) -> float:
        return round(balance * (risk_pct / 100), 2)

    # ─── TRADE MONITOR ────────────────────────────────────────────────────────
    def monitor_open_trades(self, db_session):
        """
        Called every 10 seconds. Fetches prices for all open symbols
        in one batch then checks TP/SL — minimises API calls and lag.
        """
        open_trades = db_session.query(Trade).filter(
            Trade.status == TradeStatus.OPEN
        ).all()

        if not open_trades:
            return

        portfolio = db_session.query(Portfolio).first()

        # ── Batch: one price call per unique symbol ───────────────────────────
        symbols   = list(set(t.symbol for t in open_trades))
        price_map = {}
        for symbol in symbols:
            try:
                p = self.broker.get_current_price(symbol)
                if p and p > 0:
                    price_map[symbol] = p
            except Exception as e:
                logger.warning(f"[Monitor] Price fetch failed {symbol}: {e}")

        if not price_map:
            logger.warning("[Monitor] No prices fetched — skipping")
            return

        logger.debug(f"[Monitor] Prices: { {s: f'${p:,.2f}' for s, p in price_map.items()} }")

        for trade in open_trades:
            try:
                if not trade.take_profit and not trade.stop_loss:
                    continue

                live_price = price_map.get(trade.symbol)
                if not live_price:
                    continue

                entry = trade.entry_price or 0
                qty   = trade.quantity    or 0
                try:
                    notional = trade.notional if trade.notional else round(entry * qty, 2)
                except AttributeError:
                    notional = round(entry * qty, 2)

                tp_hit = trade.take_profit and (
                    (trade.side == 'buy'  and live_price >= trade.take_profit) or
                    (trade.side == 'sell' and live_price <= trade.take_profit)
                )
                sl_hit = trade.stop_loss and (
                    (trade.side == 'buy'  and live_price <= trade.stop_loss) or
                    (trade.side == 'sell' and live_price >= trade.stop_loss)
                )

                if tp_hit or sl_hit:
                    close_price = trade.take_profit if tp_hit else trade.stop_loss
                    pnl = (close_price - entry) * qty if trade.side == 'buy' else (entry - close_price) * qty
                    pnl = round(pnl, 2)

                    trade.status     = getattr(TradeStatus, 'CLOSED_TP' if tp_hit else 'CLOSED_SL', TradeStatus.CLOSED)
                    trade.exit_price = close_price
                    trade.pnl        = pnl
                    trade.closed_at  = datetime.now(timezone.utc)

                    if portfolio:
                        portfolio.balance      = round(portfolio.balance + notional + pnl, 2)
                        portfolio.total_pnl    = round((portfolio.total_pnl or 0) + pnl, 2)
                        portfolio.total_trades = (portfolio.total_trades or 0) + 1
                        if tp_hit:
                            portfolio.winning_trades = (portfolio.winning_trades or 0) + 1

                    db_session.commit()
                    logger.info(
                        f"[Monitor] {'✅ TP' if tp_hit else '❌ SL'} TX-{trade.id} "
                        f"{trade.symbol} {trade.side.upper()} "
                        f"${entry:,.2f} → ${close_price:,.2f} | "
                        f"PnL=${pnl:+.2f} | bal=${portfolio.balance:,.2f}"
                    )
                else:
                    unreal = (live_price - entry) * qty if trade.side == 'buy' else (entry - live_price) * qty
                    logger.debug(f"[Monitor] TX-{trade.id} {trade.symbol} live=${live_price:,.2f} unreal=${unreal:+.2f}")

            except Exception as e:
                db_session.rollback()
                logger.error(f"[Monitor] Error TX-{trade.id}: {e}")

    # ─── MAIN TRADING CYCLE ───────────────────────────────────────────────────
    async def run_cycle(self, symbols: List[str], db_session):
        settings  = db_session.query(BotSettings).first()
        portfolio = db_session.query(Portfolio).first()

        if not settings or not settings.is_running:
            logger.info("Agent dormant: Bot is toggled OFF in settings.")
            return

        for symbol in symbols:
            try:
                try:
                    _ = self.broker.get_current_price(symbol)
                except Exception as e:
                    logger.error(f"DNS/Connection Failure for {symbol}: {e}. Skipping...")
                    continue

                logger.info(f"--- Deep Analysis for {symbol} ---")
                decision = await self.analyze_and_decide(symbol)

                if decision["action"] == "hold":
                    continue
                if decision["confidence"] < self.min_confidence:
                    logger.info(f"Skipping {symbol}: Confidence too low ({decision['confidence']})")
                    continue
                if decision.get("mc_probability", 0) < self.min_mc_probability:
                    logger.info(f"Skipping {symbol}: Stats fail ({decision['mc_probability']}% prob)")
                    continue

                existing_trade = db_session.query(Trade).filter(
                    Trade.symbol == symbol,
                    Trade.status == TradeStatus.OPEN
                ).first()

                if existing_trade and decision["action"] == "buy":
                    logger.info(f"Already holding {symbol}. Skipping new buy.")
                    continue

                if decision["action"] == "buy":
                    current_price = self.broker.get_current_price(symbol)
                    notional      = self.calculate_position_size(portfolio.balance, current_price, settings.max_risk_per_trade)
                    tp_val        = decision.get("suggested_tp_pct", 2.0)
                    sl_val        = decision.get("suggested_sl_pct", 1.0)

                    order_result = self.broker.place_bracket_order(
                        symbol=symbol, side="buy",
                        notional=notional, tp_pct=tp_val, sl_pct=sl_val
                    )

                    if "error" not in order_result:
                        tp_price = current_price * (1 + tp_val / 100)
                        sl_price = current_price * (1 - sl_val / 100)
                        new_trade = Trade(
                            symbol      = symbol,
                            market_type = self.market_type.value,
                            side        = "buy",
                            quantity    = notional / current_price,
                            entry_price = current_price,
                            notional    = notional,
                            stop_loss   = round(sl_price, 2),
                            take_profit = round(tp_price, 2),
                            strategy    = "Hybrid_AI_MC",
                            reason      = decision["reason"],
                            status      = TradeStatus.OPEN
                        )
                        db_session.add(new_trade)
                        portfolio.balance -= notional
                        db_session.commit()
                        logger.info(f"SUCCESS: Bought {symbol} for ${notional} (TP: {tp_val}%, SL: {sl_val}%)")

            except Exception as e:
                db_session.rollback()
                logger.error(f"Critical Cycle Error on {symbol}: {e}")