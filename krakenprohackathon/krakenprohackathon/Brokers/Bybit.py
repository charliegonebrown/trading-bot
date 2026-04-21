import os
import logging
import requests
from pybit.unified_trading import HTTP
from pybit.exceptions import FailedRequestError
import httpx

logger = logging.getLogger("BybitBroker")

# CoinGecko symbol map — no API key, no geo-restrictions
COINGECKO_MAP = {
    "BTCUSDT":    "bitcoin",
    "ETHUSDT":    "ethereum",
    "SOLUSDT":    "solana",
    "BNBUSDT":    "binancecoin",
    "XRPUSDT":    "ripple",
    "ADAUSDT":    "cardano",
    "DOGEUSDT":   "dogecoin",
    "AVAXUSDT":   "avalanche-2",
    "DOTUSDT":    "polkadot",
    "LINKUSDT":   "chainlink",
    "LTCUSDT":    "litecoin",
    "UNIUSDT":    "uniswap",
    "ATOMUSDT":   "cosmos",
    "NEARUSDT":   "near",
    "APTUSDT":    "aptos",
    "ARBUSDT":    "arbitrum",
    "OPUSDT":     "optimism",
    "INJUSDT":    "injective-protocol",
    "SUIUSDT":    "sui",
    "TONUSDT":    "the-open-network",
    "FETUSDT":    "fetch-ai",
    "RENDERUSDT": "render-token",
    "WLDUSDT":    "worldcoin-wld",
    "POLUSDT":    "matic-network",
}


class BybitBroker:
    def __init__(self):
        self.market_session = HTTP(
            testnet=False,
            domain="bybit"
        )
        self.trade_session = HTTP(
            testnet=True,
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_SECRET_KEY"),
            domain="bybit"
        )

    def get_current_price(self, symbol: str) -> float:
        """Uses CoinGecko — no geo-restrictions, no API key needed."""
        coin_id = COINGECKO_MAP.get(symbol.upper(), "")
        if not coin_id:
            logger.error(f"Unknown symbol: {symbol}")
            return 0.0
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            response = requests.get(url, timeout=10)
            data = response.json()
            price = float(data[coin_id]["usd"])
            logger.info(f"✅ CoinGecko {symbol} = ${price:,.2f}")
            return price
        except Exception as e:
            logger.error(f"CoinGecko price fetch failed for {symbol}: {e}")
            return 0.0

    def get_price_history(self, symbol: str, interval: str = "1", limit: int = 200):
        """Uses Bybit mainnet for candle history — still works from Railway."""
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
                    f"❌ Data quality fail for {symbol}: only {unique_count} unique prices "
                    f"in last 20 candles."
                )
                return []

            logger.info(f"✅ {symbol} price history: {len(prices)} candles, "
                        f"latest=${prices[-1]:,.2f}")
            return prices

        except Exception as e:
            logger.error(f"Bybit History Fetch Failed: {e}")
            return []

    def place_bracket_order(self, symbol: str, side: str, notional: float, tp_pct: float, sl_pct: float):
        """Uses trade_session (testnet) for paper order execution."""
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
        """Async price via CoinGecko."""
        coin_id = COINGECKO_MAP.get(symbol.upper(), "")
        if not coin_id:
            return 0.0
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                data     = response.json()
                return float(data[coin_id]["usd"])
        except Exception as e:
            logger.error(f"CoinGecko async price failed for {symbol}: {e}")
            return 0.0