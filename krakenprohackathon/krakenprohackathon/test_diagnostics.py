"""
Run this from your project root:
    python test_diagnosis.py

It will tell you exactly what's wrong with your price data and indicators.
"""

import os
import sys
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ─── 1. FETCH PRICE DATA ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 1: FETCHING PRICE DATA FROM BYBIT")
print("="*60)

try:
    from pybit.unified_trading import HTTP

    session = HTTP(
        testnet=True,
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_SECRET_KEY"),
        domain="bytick"
    )

    SYMBOL   = "BTCUSDT"
    INTERVAL = "1"
    LIMIT    = 200

    response = session.get_kline(
        category="linear",
        symbol=SYMBOL,
        interval=INTERVAL,
        limit=LIMIT
    )

    raw_candles = response['result']['list']
    print(f"✅ Raw candles returned   : {len(raw_candles)}")
    print(f"   First raw candle       : {raw_candles[0]}")
    print(f"   Last  raw candle       : {raw_candles[-1]}")

    # Bybit returns newest-first → reverse to chronological
    candles = raw_candles[::-1]
    prices  = [float(x[4]) for x in candles]   # index 4 = close price

    print(f"\n   Total prices extracted : {len(prices)}")
    print(f"   First 5 prices         : {prices[:5]}")
    print(f"   Last  5 prices         : {prices[-5:]}")
    print(f"   Last 20 prices         : {prices[-20:]}")

except Exception as e:
    print(f"❌ FAILED to fetch from Bybit: {e}")
    print("   Check your BYBIT_API_KEY / BYBIT_SECRET_KEY in .env")
    sys.exit(1)


# ─── 2. DATA QUALITY CHECKS ──────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2: DATA QUALITY CHECKS")
print("="*60)

unique_all  = len(set(prices))
unique_last20 = len(set(prices[-20:]))
unique_last14 = len(set(prices[-14:]))

print(f"   Unique prices (all 200) : {unique_all}")
print(f"   Unique prices (last 20) : {unique_last20}  ← BB window")
print(f"   Unique prices (last 14) : {unique_last14}  ← RSI window")

if unique_last14 < 5:
    print("   ❌ PROBLEM: Less than 5 unique prices in RSI window.")
    print("      This means testnet is returning stale/cached candles.")
    print("      RSI will be 100 (no losing candles) and BB/MC will break.")
elif unique_last14 < 10:
    print("   ⚠️  WARNING: Low price variety in last 14 candles. Data may be stale.")
else:
    print("   ✅ Price variety looks healthy.")

price_range = max(prices[-20:]) - min(prices[-20:])
price_pct_range = (price_range / prices[-1]) * 100
print(f"\n   Last-20 price range     : ${price_range:.4f}  ({price_pct_range:.4f}%)")

if price_pct_range < 0.01:
    print("   ❌ PROBLEM: Price range < 0.01% — data is essentially flat.")
    print("      Monte Carlo sigma will be ~0, giving near-0% probability.")
else:
    print("   ✅ Price range is healthy for indicator calculations.")


# ─── 3. INDICATOR DEEP DIVE ──────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 3: INDICATOR CALCULATIONS")
print("="*60)

df      = pd.Series(prices, dtype=float)
delta   = df.diff()
gain    = delta.where(delta > 0, 0.0).rolling(window=14, min_periods=14).mean()
loss    = (-delta.where(delta < 0, 0.0)).rolling(window=14, min_periods=14).mean()
rs      = gain / loss.where(loss != 0, np.nan)
rsi     = (100 - (100 / (1 + rs))).fillna(100)
rsi_val = float(rsi.iloc[-1])

loss_val = float(loss.iloc[-1])
gain_val = float(gain.iloc[-1])
print(f"   RSI gain (avg)          : {gain_val:.6f}")
print(f"   RSI loss (avg)          : {loss_val:.6f}  ← if 0.0 → RSI forced to 100")
print(f"   RSI value               : {rsi_val:.2f}")

if loss_val == 0.0:
    print("   ❌ PROBLEM: Average loss = 0 over last 14 candles.")
    print("      This means price only went UP or was FLAT for 14 straight minutes.")
    print("      Almost certainly stale testnet data.")
else:
    print("   ✅ RSI calculated from real gain/loss data.")

# MACD
ema12       = df.ewm(span=12, adjust=False).mean()
ema26       = df.ewm(span=26, adjust=False).mean()
macd_line   = ema12 - ema26
signal_line = macd_line.ewm(span=9, adjust=False).mean()
macd_hist   = float((macd_line - signal_line).iloc[-1])
print(f"\n   MACD histogram          : {macd_hist:.6f}")

# Bollinger Bands
rolling_mean = df.rolling(window=20, min_periods=20).mean()
rolling_std  = df.rolling(window=20, min_periods=20).std()
upper_val    = float((rolling_mean + 2 * rolling_std).iloc[-1])
lower_val    = float((rolling_mean - 2 * rolling_std).iloc[-1])
band_width   = upper_val - lower_val
print(f"\n   BB upper                : {upper_val:.4f}")
print(f"   BB lower                : {lower_val:.4f}")
print(f"   BB width                : {band_width:.4f}  ← if 0 → BB = No data")

if band_width == 0:
    print("   ❌ PROBLEM: Band width = 0 — all 20 prices are identical.")
else:
    bb_pos = (prices[-1] - lower_val) / band_width
    print(f"   BB position             : {bb_pos:.4f}")
    print("   ✅ BB calculated successfully.")

# Slope
y         = np.array(prices[-10:], dtype=float)
x         = np.arange(len(y))
slope     = np.polyfit(x, y, 1)[0]
slope_pct = (slope / prices[-1]) * 100
print(f"\n   Slope                   : {slope:.6f}  ({slope_pct:.6f}%/candle)")


# ─── 4. MONTE CARLO CHECK ────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 4: MONTE CARLO INPUTS")
print("="*60)

returns = df.pct_change().dropna()
mu      = returns.mean()
sigma   = returns.std()

print(f"   mu (drift)              : {mu:.8f}")
print(f"   sigma (volatility)      : {sigma:.8f}  ← if ~0 → MC will be near 0%")

if sigma < 1e-6:
    print("   ❌ PROBLEM: Sigma is effectively zero.")
    print("      GBM price paths won't move. MC probability will be ~0%.")
    print("      Root cause: flat/duplicate price data (same as RSI/BB issue).")
else:
    print(f"   ✅ Sigma looks usable.")
    # Quick MC estimate
    steps, sims = 200, 500
    tp_price    = prices[-1] * 1.02
    sl_price    = prices[-1] * 0.99
    hits        = 0
    for _ in range(sims):
        z    = np.random.standard_normal(steps)
        path = prices[-1] * np.exp((mu - 0.5*sigma**2) + sigma*z).cumprod()
        for p in path:
            if p >= tp_price: hits += 1; break
            if p <= sl_price: break
    mc_prob = (hits / sims) * 100
    print(f"   Quick MC estimate       : {mc_prob:.1f}%  (500 sims, 200 steps)")


# ─── 5. VERDICT ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("VERDICT")
print("="*60)

issues = []
if unique_last14 < 5:
    issues.append("Stale testnet data — too few unique prices")
if price_pct_range < 0.01:
    issues.append("Price range < 0.01% — effectively flat data")
if loss_val == 0.0:
    issues.append("RSI loss=0 — no downward moves in 14 candles")
if band_width == 0:
    issues.append("BB width=0 — all 20 candles at same price")
if sigma < 1e-6:
    issues.append("MC sigma~0 — GBM cannot simulate movement")

if issues:
    print("❌ ISSUES FOUND:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    print("\n💡 RECOMMENDED FIX:")
    print("   Switch from testnet=True → testnet=False in Bybit.py")
    print("   OR use interval='60' (hourly) instead of '1' (1-minute) on testnet")
    print("   Testnet often has sparse/stale 1-minute candle data.")
else:
    print("✅ All checks passed — data and indicators look healthy.")

print("="*60 + "\n")