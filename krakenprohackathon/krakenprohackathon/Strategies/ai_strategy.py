import json
import os
import time
import re
import numpy as np
import pandas as pd
from typing import List, Dict

# ─── CONFIG ──────────────────────────────────────────────────────────────────
USE_GEMINI = False


# --- STEP 1: THE STATISTICAL ENGINE ---
def run_monte_carlo(prices: List[float], tp_pct: float, sl_pct: float, steps: int = None, sims: int = 1000) -> float:
    """
    Calculates probability of hitting TP before SL using Geometric Brownian Motion.

    KEY DESIGN DECISIONS:

    1. mu = dampened real drift: we use the actual historical mean return, dampened
       by 50% to avoid over-fitting short-term momentum. This allows MC to exceed
       50% when the market has genuine upward/downward momentum, making the gate
       passable. Clamped to ±3× sigma so extreme outlier candles don't dominate.

    2. AUTO-SCALED steps: steps are calculated from sigma so the simulation
       horizon always covers enough candles for price to realistically reach TP.
       Formula: steps = (tp_pct/100 / sigma)^2 * 3
       This means "3x the candles needed for a 1-sigma move to cover TP distance."
       Clamped between 200 (min) and 2000 (max) to stay sane.

    3. AUTO-SCALED TP/SL: if sigma is tiny (quiet market), TP/SL are shrunk to
       match what's actually reachable. This stops MC returning 0% just because
       the market is calm — it still measures relative reachability correctly.
    """
    df      = pd.Series(prices)
    returns = df.pct_change().dropna()
    sigma   = returns.std()
    # FIX: use real (dampened) drift instead of forcing mu=0.
    # mu=0 makes P(TP first) ≤ 33% for a 2:1 TP/SL ratio — the gate was unreachable.
    # Dampening by 0.5 prevents short-term noise from dominating; clamp to ±3σ for safety.
    raw_mu = returns.mean()
    mu     = float(np.clip(raw_mu * 0.5, -3 * sigma, 3 * sigma))

    if sigma == 0 or np.isnan(sigma):
        print("[MC WARNING] Sigma=0 — price data is flat. Returning 0% probability.")
        return 0.0

    # AUTO-SCALE TP/SL to sigma so targets are always proportional to volatility.
    # Rule: TP = 3× per-candle sigma, SL = 1.5× per-candle sigma (2:1 R:R preserved)
    # This means in a quiet market we trade smaller targets; in volatile markets, larger.
    sigma_pct  = sigma * 100
    tp_pct_adj = max(tp_pct, round(sigma_pct * 3,  2))
    sl_pct_adj = max(sl_pct, round(sigma_pct * 1.5, 2))

    # AUTO-SCALE steps: enough candles for price to plausibly reach TP
    # steps = 3 × (tp distance / per-candle sigma)^2, clamped 200–2000
    if steps is None:
        steps = int(((tp_pct_adj / 100) / sigma) ** 2 * 3)
        steps = max(200, min(steps, 2000))

    current_price = prices[-1]
    tp_price      = current_price * (1 + tp_pct_adj / 100)
    sl_price      = current_price * (1 - sl_pct_adj / 100)

    success_count = 0
    for _ in range(sims):
        z            = np.random.standard_normal(steps)
        path_returns = np.exp((mu - 0.5 * sigma**2) + sigma * z)  # FIX: real mu, not 0
        path         = current_price * path_returns.cumprod()

        for price in path:
            if price >= tp_price:
                success_count += 1
                break
            if price <= sl_price:
                break

    probability = (success_count / sims) * 100
    print(f"[MC] raw_mu={raw_mu:.6f} dampened_mu={mu:.6f} sigma={sigma:.6f} ({sigma_pct:.4f}%/candle) | "
          f"TP={tp_pct_adj:.2f}% SL={sl_pct_adj:.2f}% | "
          f"steps={steps} sims={sims} → prob={probability:.1f}%")
    return probability


# --- STEP 2: MATH-ONLY SIGNAL (no AI needed) ---------------------------------

# Base TP/SL targets per timeframe — sized to what each interval can realistically move.
# TP:SL ratio is always 2:1 to maintain positive expected value.
INTERVAL_TP_SL = {
    "1":   (0.4,  0.2),   # 1-min  scalp:  tiny targets, high frequency
    "3":   (0.6,  0.3),
    "5":   (0.8,  0.4),
    "15":  (1.0,  0.5),   # 15-min short:  moderate targets
    "30":  (1.5,  0.75),
    "60":  (2.5,  1.25),  # 1-hour swing:  standard targets  ← recommended
    "120": (3.0,  1.5),
    "240": (4.0,  2.0),   # 4-hour trend:  wider targets
    "360": (5.0,  2.5),
    "720": (6.0,  3.0),
    "D":   (8.0,  4.0),   # Daily macro:   largest targets
    "W":   (12.0, 6.0),
    "M":   (18.0, 9.0),
}

def _math_only_signal(triple_conf: Dict, mc_prob: float, interval: str = "60") -> Dict:
    """
    Builds a final signal purely from Triple Confirmation + Monte Carlo.
    Used when USE_GEMINI=False or when Gemini is unavailable.

    TP/SL now scales by TWO factors:
      1. Candle interval — wider timeframe = larger natural price swings = bigger targets
      2. MC probability  — stronger stats confirmation = allow slightly wider TP
    """
    action     = triple_conf.get("action", "hold")
    confidence = triple_conf.get("confidence", 0.0)
    reason     = triple_conf.get("reason", "Triple Confirmation signal")

    # Get base TP/SL for this timeframe (default to 1h if interval not in table)
    base_tp, base_sl = INTERVAL_TP_SL.get(interval, (2.5, 1.25))

    # Monte Carlo safety gate — if stats don't agree, don't trade
    if action != "hold" and mc_prob < 40:
        return {
            "action":           "hold",
            "reason":           f"Triple Confirmation says {action.upper()} but Monte Carlo probability too low ({mc_prob:.1f}% < 45%). Waiting for better setup.",
            "confidence":       0.0,
            "mc_probability":   round(mc_prob, 2),
            "suggested_tp_pct": base_tp,
            "suggested_sl_pct": base_sl,
        }

    # Scale TP/SL UP slightly based on MC strength (reward higher-confidence setups)
    # MC >= 70%: +20% wider targets  |  MC >= 60%: +10% wider  |  else: base
    if mc_prob >= 70:
        tp_pct = round(base_tp * 1.2, 2)
        sl_pct = round(base_sl * 1.2, 2)
    elif mc_prob >= 60:
        tp_pct = round(base_tp * 1.1, 2)
        sl_pct = round(base_sl * 1.1, 2)
    else:
        tp_pct = base_tp
        sl_pct = base_sl

    print(f"[SIGNAL] interval={interval} | base=({base_tp}%/{base_sl}%) | "
          f"mc={mc_prob:.1f}% | final=({tp_pct}%/{sl_pct}%)")

    return {
        "action":           action,
        "reason":           reason,
        "confidence":       round(confidence, 2),
        "mc_probability":   round(mc_prob, 2),
        "suggested_tp_pct": tp_pct,
        "suggested_sl_pct": sl_pct,
    }


# --- STEP 3: AI JUDGE (Google Gemini) ----------------------------------------
async def get_hybrid_ai_signal(
    symbol:      str,
    prices:      List[float],
    market_type: str,
    triple_conf: Dict,
    interval:    str = "60"   # candle interval — passed from main.py and base_agent
) -> Dict:
    """
    Main entry point called by /api/analyse and base_agent.
    If USE_GEMINI=True  → Triple Confirmation + Monte Carlo + Gemini AI
    If USE_GEMINI=False → Triple Confirmation + Monte Carlo only (math signal)
    interval is forwarded to _math_only_signal so TP/SL scales with timeframe.
    """
    mc_prob = run_monte_carlo(prices, tp_pct=2.0, sl_pct=1.0)

    # ── MATH-ONLY MODE ────────────────────────────────────────────────────────
    if not USE_GEMINI:
        return _math_only_signal(triple_conf, mc_prob, interval=interval)

    # ── GEMINI MODE ───────────────────────────────────────────────────────────
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️  USE_GEMINI=True but GOOGLE_API_KEY not set — falling back to math signal")
        return _math_only_signal(triple_conf, mc_prob, interval=interval)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    except ImportError:
        print("⚠️  google-generativeai not installed — falling back to math signal")
        return _math_only_signal(triple_conf, mc_prob)

    recent_prices = prices[-20:]
    price_change  = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100

    prompt = f"""You are the Senior Risk Officer for a Quant Hedge Fund.
Analyse the following data for {symbol} ({market_type}).

--- TECHNICAL INDICATORS ---
Signal: {triple_conf['action'].upper()}
Reasoning: {triple_conf['reason']}
Confidence: {triple_conf['confidence']}

--- MONTE CARLO SIMULATION ---
1,000 simulated paths | Target: 2% TP / 1% SL | Horizon: 200 candles
Probability of hitting TP first: {mc_prob:.2f}%

--- PRICE ACTION ---
Current Price: {recent_prices[-1]}
20-period trend: {recent_prices}
Total change: {price_change:.2f}%

--- YOUR JOB ---
If the technical signal and Monte Carlo probability align with price action, confirm the trade.
If they conflict, respond with hold.

Respond ONLY with a valid JSON object and nothing else:
{{
    "action": "buy" or "sell" or "hold",
    "reason": "one sentence synthesising all three signals",
    "confidence": 0.0 to 1.0,
    "mc_probability": {mc_prob:.2f},
    "suggested_tp_pct": a float like 2.0,
    "suggested_sl_pct": a float like 1.0
}}"""

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json",
        )
    )

    for attempt in range(2):
        try:
            response = model.generate_content(prompt)
            result   = json.loads(response.text)

            result.setdefault("suggested_tp_pct", 2.0)
            result.setdefault("suggested_sl_pct", 1.0)
            result.setdefault("mc_probability",   round(mc_prob, 2))
            result.setdefault("confidence",        0.0)
            result.setdefault("action",            "hold")
            return result

        except Exception as e:
            err_str = str(e)

            if "429" in err_str:
                if attempt == 0:
                    delay_match = re.search(r"retry_delay \{ seconds: (\d+)", err_str)
                    wait = min(int(delay_match.group(1)) if delay_match else 15, 20)
                    print(f"⚠️  Gemini 429 quota hit — waiting {wait}s then retrying...")
                    time.sleep(wait)
                    continue
                else:
                    print("⚠️  Gemini quota exhausted — switching to math-only signal")
                    result = _math_only_signal(triple_conf, mc_prob, interval=interval)
                    result["reason"] += " [Gemini quota exhausted — using math signal]"
                    return result

            print(f"⚠️  Gemini error: {err_str[:120]}")
            return _math_only_signal(triple_conf, mc_prob, interval=interval)