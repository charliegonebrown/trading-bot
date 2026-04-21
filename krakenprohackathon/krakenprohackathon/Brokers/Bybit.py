import os
import logging
from pybit.unified_trading import HTTP
from pybit.exceptions import FailedRequestError
import httpx

logger = logging.getLogger("BybitBroker")

class BybitBroker:
    def __init__(self):
        # FIX: Two separate sessions:
        # - market_session: mainnet (testnet=False) → real, live candle data
        # - trade_session:  testnet (testnet=True)  → safe paper trading
        # Testnet 1-minute candles are stale/cached and will break all indicators.
        self.market_session = HTTP(
            testnet=False,
            domain="bybit"  # bybit domain for Nigerian ISP connectivity
        )
        self.trade_session = HTTP(
            testnet=True,
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_SECRET_KEY"),
            domain="bybit"
        )

    def get_current_price(self, symbol: str) -> float:
        """Uses mainnet market session — always real price"""
        try:
            response = self.market_session.get_tickers(category="linear", symbol=symbol)
            return float(response['result']['list'][0]['lastPrice'])
        except Exception as e:
            logger.error(f"Bybit Price Fetch Failed: {e}")
            return 0.0

    def get_price_history(self, symbol: str, interval: str = "1", limit: int = 200):
        """
        Uses mainnet market session for real candle data.
        Testnet candles are stale and will break RSI/BB/Monte Carlo.
        Also validates data quality before returning.
        """
        try:
            response = self.market_session.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            # Bybit returns newest-first → reverse to chronological order
            candles = response['result']['list'][::-1]
            prices  = [float(x[4]) for x in candles]  # index 4 = close price

            # DATA QUALITY GUARD: Catch stale/flat data before it poisons indicators
            unique_count = len(set(prices[-20:]))
            if unique_count < 5:
                logger.error(
                    f"❌ Data quality fail for {symbol}: only {unique_count} unique prices "
                    f"in last 20 candles. Refusing to trade on stale data."
                )
                return []

            logger.info(f"✅ {symbol} price history: {len(prices)} candles, "
                        f"{unique_count} unique in last 20, latest=${prices[-1]:,.2f}")
            return prices

        except Exception as e:
            logger.error(f"Bybit History Fetch Failed: {e}")
            return []

    def place_bracket_order(self, symbol: str, side: str, notional: float, tp_pct: float, sl_pct: float):
        """
        Uses trade_session (testnet) for safe paper order execution.
        Calculates TP/SL prices from the strategy-suggested percentages.
        """
        try:
            price = self.get_current_price(symbol)
            if price == 0:
                return {"error": "Could not fetch current price"}

            qty      = round(notional / price, 3)
            tp_price = round(price * (1 + tp_pct / 100), 2)
            sl_price = round(price * (1 - sl_pct / 100), 2)

            return self.trade_session.place_order(
                category="linear",
                symbol=symbol,
                side=side.capitalize(),
                orderType="Market",
                qty=str(qty),
                takeProfit=str(tp_price),
                stopLoss=str(sl_price),
                tpTriggerBy="LastPrice",
                slTriggerBy="LastPrice",
                tpslMode="Full"
            )

        except FailedRequestError as e:
            logger.error(f"Bybit Order Failed: {e.message}")
            return {"error": e.message}
        except Exception as e:
            logger.error(f"Unexpected Broker Error: {e}")
            return {"error": str(e)}

    async def get_last_price(self, symbol: str) -> float:
        """Async real-time price fetch via mainnet REST (no auth needed)"""
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        try:
            async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
                response = await client.get(url)
                data     = response.json()
                return float(data['result']['list'][0]['lastPrice'])
        except Exception as e:
            logger.error(f"Failed to fetch async price for {symbol}: {e}")
            return 0.0