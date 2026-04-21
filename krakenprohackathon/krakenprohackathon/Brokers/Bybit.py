import os
import logging
import requests
from pybit.unified_trading import HTTP
from pybit.exceptions import FailedRequestError
import httpx

logger = logging.getLogger("BybitBroker")


class BybitBroker:
    def __init__(self):
        # Candle history — Bybit mainnet (kline endpoint works from US IPs)
        self.market_session = HTTP(
            testnet=False,
            domain="bybit"
        )
        # Order execution — Bybit testnet (paper trading)
        self.trade_session = HTTP(
            testnet=True,
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_SECRET_KEY"),
            domain="bybit"
        )

    def get_current_price(self, symbol: str) -> float:
        """Uses KuCoin public API — no geo-restrictions anywhere."""
        try:
            # Convert BTCUSDT → BTC-USDT for KuCoin format
            base = symbol.upper().replace("USDT", "")
            kucoin_symbol = f"{base}-USDT"
            url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}"
            response = requests.get(url, timeout=10)
            data = response.json()
            price = float(data["data"]["price"])
            logger.info(f"✅ KuCoin {symbol} = ${price:,.2f}")
            return price
        except Exception as e:
            logger.error(f"KuCoin price fetch failed for {symbol}: {e}")
            return 0.0
    def get_price_history(self, symbol: str, interval: str = "1", limit: int = 200):
        """Uses KuCoin for candle history — no geo-restrictions."""
        INTERVAL_MAP = {
            "1":"1min","3":"3min","5":"5min","15":"15min","30":"30min",
            "60":"1hour","120":"2hour","240":"4hour","360":"6hour",
            "720":"8hour","D":"1day","W":"1week",
        }
        kc_interval = INTERVAL_MAP.get(interval, "1min")
        base      = symbol.upper().replace("USDT", "")
        kc_symbol = f"{base}-USDT"
        try:
            url = f"https://api.kucoin.com/api/v1/market/candles?type={kc_interval}&symbol={kc_symbol}"
            response = requests.get(url, timeout=10)
            data     = response.json()
            candles  = data["data"][::-1]  # newest first → reverse to chronological
            prices   = [float(c[2]) for c in candles]  # index 2 = close price

            if len(prices) < 30:
                logger.error(f"Not enough candles for {symbol}: got {len(prices)}")
                return []

            logger.info(f"✅ KuCoin {symbol}: {len(prices)} candles, latest=${prices[-1]:,.2f}")
            return prices
        except Exception as e:
            logger.error(f"KuCoin history failed for {symbol}: {e}")
            return []

    def place_bracket_order(
        self, symbol: str, side: str,
        notional: float, tp_pct: float, sl_pct: float
    ):
        """Uses Bybit testnet for safe paper order execution."""
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
        """Async price via KuCoin."""
        try:
            base = symbol.upper().replace("USDT", "")
            kucoin_symbol = f"{base}-USDT"
            url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                data = response.json()
                return float(data["data"]["price"])
        except Exception as e:
            logger.error(f"KuCoin async price failed for {symbol}: {e}")
            return 0.0