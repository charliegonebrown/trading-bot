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
        """
        Uses Bybit mainnet for candle/OHLCV history.
        Bybit kline endpoint works from US IPs — only ticker endpoint is blocked.
        """
        try:
            response = self.market_session.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            candles = response['result']['list'][::-1]
            prices  = [float(x[4]) for x in candles]

            unique_count = len(set(prices[-20:]))
            if unique_count < 5:
                logger.error(
                    f"❌ Data quality fail for {symbol}: only {unique_count} unique "
                    f"prices in last 20 candles."
                )
                return []

            logger.info(
                f"✅ {symbol} price history: {len(prices)} candles, "
                f"latest=${prices[-1]:,.2f}"
            )
            return prices

        except Exception as e:
            logger.error(f"Bybit History Fetch Failed: {e}")
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