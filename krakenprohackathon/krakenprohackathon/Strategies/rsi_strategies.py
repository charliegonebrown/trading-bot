import pandas as pd
import numpy as np
from typing import List, Dict


def calculate_indicators(prices: List[float]) -> Dict:
    df = pd.Series(prices, dtype=float)

    # 1. RSI (14-period)
    delta = df.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=14, min_periods=14).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=14, min_periods=14).mean()

    # FIX: When loss == 0 (pure uptrend), RSI should be 100, not NaN.
    # Use np.where to clamp instead of replacing 0 with NaN.
    rs  = gain / loss.where(loss != 0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # Any remaining NaN at positions where loss=0 means pure uptrend → RSI = 100
    rsi = rsi.fillna(100)

    # 2. MACD (12/26/9)
    ema12       = df.ewm(span=12, adjust=False).mean()
    ema26       = df.ewm(span=26, adjust=False).mean()
    macd_line   = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist   = macd_line - signal_line

    # 3. Slope over last 10 periods
    y     = np.array(prices[-10:], dtype=float)
    x     = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0] if len(y) >= 2 else 0.0

    # 4. Bollinger Bands (20-period)
    rolling_mean = df.rolling(window=20, min_periods=20).mean()
    rolling_std  = df.rolling(window=20, min_periods=20).std()
    upper_band   = rolling_mean + (2 * rolling_std)
    lower_band   = rolling_mean - (2 * rolling_std)

    # FIX: Extract scalar values explicitly to avoid pandas ambiguity issues
    upper_val  = float(upper_band.iloc[-1])
    lower_val  = float(lower_band.iloc[-1])
    band_width = upper_val - lower_val
    current    = float(prices[-1])

    if band_width > 0 and not np.isnan(band_width) and not np.isnan(lower_val):
        bb_position = (current - lower_val) / band_width
    else:
        bb_position = np.nan

    rsi_val      = float(rsi.iloc[-1])
    macd_val     = float(macd_hist.iloc[-1])

    # DEBUG LINE — remove once confirmed working
    print(f"[DEBUG] candles={len(prices)} | RSI={rsi_val:.2f} | MACD_hist={macd_val:.5f} | BB_pos={bb_position} | slope={slope:.6f}")

    return {
        "rsi":           rsi_val,
        "macd_hist":     macd_val,
        "slope":         slope,
        "bb_position":   bb_position,
        "current_price": current,
        "candle_count":  len(prices),
    }


def get_triple_confirmation_signal(prices: List[float]) -> Dict:
    """
    SCORING SYSTEM — 2-of-N indicators must agree to generate a signal.

    Each available indicator votes: +1 bull, -1 bear, 0 neutral.
    NaN indicators are SKIPPED (not counted as neutral) so a lack of data
    never unfairly blocks a signal.

    Score >= +2  → BUY
    Score <= -2  → SELL
    Otherwise    → HOLD
    """
    if len(prices) < 30:
        return {
            "action":     "hold",
            "reason":     f"Insufficient data — got {len(prices)} candles, need 30+",
            "confidence": 0.0,
            "score":      0,
            "indicators": {},
        }

    ind          = calculate_indicators(prices)
    score        = 0
    votes        = {}
    max_possible = 0

    # ── INDICATOR 1: RSI ─────────────────────────────────────────────────────
    rsi = ind["rsi"]
    if not np.isnan(rsi):
        max_possible += 1
        if rsi < 45:
            score += 1
            votes["RSI"] = f"Bull {rsi:.1f} (oversold)"
        elif rsi > 55:
            score -= 1
            votes["RSI"] = f"Bear {rsi:.1f} (overbought)"
        else:
            votes["RSI"] = f"Neutral {rsi:.1f}"
    else:
        votes["RSI"] = f"No data (only {ind['candle_count']} candles)"

    # ── INDICATOR 2: MACD Histogram ──────────────────────────────────────────
    macd_hist = ind["macd_hist"]
    if not np.isnan(macd_hist):
        max_possible += 1
        if macd_hist > 0:
            score += 1
            votes["MACD"] = f"Bull (hist {macd_hist:.5f})"
        elif macd_hist < 0:
            score -= 1
            votes["MACD"] = f"Bear (hist {macd_hist:.5f})"
        else:
            votes["MACD"] = "Neutral"
    else:
        votes["MACD"] = "No data"

    # ── INDICATOR 3: Slope ───────────────────────────────────────────────────
    slope = ind["slope"]
    max_possible += 1
    slope_pct = (slope / ind["current_price"]) * 100 if ind["current_price"] > 0 else 0
    if slope_pct > 0.001:
        score += 1
        votes["Slope"] = f"Bull ({slope_pct:.4f}%/candle)"
    elif slope_pct < -0.001:
        score -= 1
        votes["Slope"] = f"Bear ({slope_pct:.4f}%/candle)"
    else:
        votes["Slope"] = f"Flat ({slope_pct:.4f}%/candle)"

    # ── INDICATOR 4: Bollinger Band Position ─────────────────────────────────
    bb = ind["bb_position"]
    if not np.isnan(bb):
        max_possible += 1
        if bb < 0.35:
            score += 1
            votes["BB"] = f"Bull (pos {bb:.2f} — near lower band)"
        elif bb > 0.65:
            score -= 1
            votes["BB"] = f"Bear (pos {bb:.2f} — near upper band)"
        else:
            votes["BB"] = f"Neutral (pos {bb:.2f})"
    else:
        votes["BB"] = "No data"

    # ── DECISION ─────────────────────────────────────────────────────────────
    summary = " | ".join([f"{k}: {v}" for k, v in votes.items()])

    if score >= 2:
        confidence = round(min(score / max(max_possible, 1), 1.0), 2)
        return {
            "action":     "buy",
            "reason":     f"Score +{score}/{max_possible} — {summary}",
            "confidence": confidence,
            "score":      score,
            "indicators": votes,
        }
    elif score <= -2:
        confidence = round(min(abs(score) / max(max_possible, 1), 1.0), 2)
        return {
            "action":     "sell",
            "reason":     f"Score {score}/{max_possible} — {summary}",
            "confidence": confidence,
            "score":      score,
            "indicators": votes,
        }
    else:
        return {
            "action":     "hold",
            "reason":     f"Score {score}/{max_possible} — mixed signals. {summary}",
            "confidence": 0.0,
            "score":      score,
            "indicators": votes,
        }