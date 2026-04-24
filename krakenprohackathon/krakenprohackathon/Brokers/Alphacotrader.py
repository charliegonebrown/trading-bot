import os
import logging
from typing import List, Dict
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlpacaBroker")

class AlpacaBroker:
    def __init__(self):
        self.api = None
        try:
            base_url = (os.getenv("ALPACA_BASE_URL",  "") or "").strip().split()[0]
            api_key  = (os.getenv("ALPACA_API_KEY",   "") or "").strip().split()[0]
            secret   = (os.getenv("ALPACA_SECRET_KEY","") or "").strip().split()[0]

            if not all([base_url, api_key, secret]):
                logger.warning("Alpaca credentials missing in .env")
                return

            import alpaca_trade_api as tradeapi
            self.api = tradeapi.REST(
                key_id=api_key,
                secret_key=secret,
                base_url=base_url
            )
            self.api.get_account()
            logger.info(f"✅ Alpaca connected — {base_url}")

        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            self.api = None

    def _check(self):
        if not self.api:
            raise RuntimeError(
                "Alpaca not connected — check ALPACA_API_KEY, ALPACA_SECRET_KEY, "
                "ALPACA_BASE_URL in .env (no inline comments after values)"
            )

    def get_price_history(self, symbol: str, limit: int = 200, timeframe: str = "1Hour") -> List[float]:
        self._check()
        try:
            import alpaca_trade_api as tradeapi

            TF_MAP = {
                "1Min":  tradeapi.TimeFrame.Minute,
                "5Min":  tradeapi.TimeFrameUnit.Minute,
                "15Min": tradeapi.TimeFrameUnit.Minute,
                "1Hour": tradeapi.TimeFrame.Hour,
                "4Hour": tradeapi.TimeFrameUnit.Hour,
                "1Day":  tradeapi.TimeFrame.Day,
            }

            end       = datetime.utcnow()
            days_back = max(limit * 2, 60) if timeframe in ("1Hour", "4Hour") else limit + 30
            start     = end - timedelta(days=days_back)

            bars = self.api.get_bars(
                symbol,
                timeframe,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                limit=limit,
                feed="iex"
            ).df

            if bars.empty:
                bars = self.api.get_bars(
                    symbol, timeframe,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    limit=limit
                ).df

            prices = [float(x) for x in bars["close"].tolist()]
            logger.info(f"✅ {symbol} bars: {len(prices)} candles at {timeframe}")
            return prices

        except Exception as e:
            logger.error(f"Price history failed for {symbol} @ {timeframe}: {e}")
            return []

    def get_current_price(self, symbol: str) -> float:
        """Alias for get_latest_price — used by base_agent.py"""
        return self.get_latest_price(symbol)

    def get_latest_price(self, symbol: str) -> float:
        self._check()
        try:
            return float(self.api.get_latest_trade(symbol).price)
        except Exception as e:
            logger.error(f"Latest price failed for {symbol}: {e}")
            return 0.0

    def place_bracket_order(self, symbol: str, side: str, notional: float, tp_pct: float, sl_pct: float) -> Dict:
        self._check()
        try:
            current_price     = float(self.api.get_latest_trade(symbol).price)
            take_profit_price = round(current_price * (1 + tp_pct/100), 2) if side == "buy" else round(current_price * (1 - tp_pct/100), 2)
            stop_loss_price   = round(current_price * (1 - sl_pct/100), 2) if side == "buy" else round(current_price * (1 + sl_pct/100), 2)

            order = self.api.submit_order(
                symbol=symbol, notional=notional, side=side,
                type="market", time_in_force="gtc", order_class="bracket",
                take_profit={"limit_price": take_profit_price},
                stop_loss={"stop_price": stop_loss_price}
            )
            logger.info(f"Bracket order: {side} {symbol} @ ${current_price}")
            return {"order_id": order.id, "status": order.status}
        except Exception as e:
            logger.error(f"Order failed for {symbol}: {e}")
            return {"error": str(e), "status": "failed"}

    def get_account_vitals(self) -> Dict:
        self._check()
        try:
            acc       = self.api.get_account()
            positions = self.api.list_positions()
            return {
                "cash":            float(acc.cash),
                "portfolio_value": float(acc.portfolio_value),
                "open_positions":  len(positions)
            }
        except Exception as e:
            logger.error(f"Account fetch failed: {e}")
            return {}