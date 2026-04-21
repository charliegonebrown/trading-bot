"""
Run once from project root:
    python fix_trades.py

Fixes two things:
1. Corrects "TradeStatus.OPEN" → "open" in the DB (enum string mismatch)
2. Immediately closes any trades where TP/SL has already been hit
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_bot.db")

if not os.path.exists(DB_PATH):
    print(f"❌ Not found: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# ── 1. Show current raw status values ────────────────────────────────────────
cur.execute("SELECT id, symbol, side, status, entry_price, take_profit, stop_loss, quantity, notional FROM trades")
rows = cur.fetchall()
print(f"Found {len(rows)} trades:")
for r in rows:
    print(f"  TX-{r[0]} {r[1]} {r[2]} status='{r[3]}' entry={r[4]} TP={r[5]} SL={r[6]}")

# ── 2. Fix broken enum strings ────────────────────────────────────────────────
fixes = {
    "TradeStatus.OPEN":      "open",
    "TradeStatus.CLOSED":    "closed",
    "TradeStatus.CLOSED_TP": "closed_tp",
    "TradeStatus.CLOSED_SL": "closed_sl",
}

for bad, good in fixes.items():
    cur.execute("UPDATE trades SET status = ? WHERE status = ?", (good, bad))
    if cur.rowcount > 0:
        print(f"  ✅ Fixed {cur.rowcount} rows: '{bad}' → '{good}'")

conn.commit()

# ── 3. Verify fix ─────────────────────────────────────────────────────────────
cur.execute("SELECT id, status FROM trades")
print("\nAfter fix:")
for r in cur.fetchall():
    print(f"  TX-{r[0]} status='{r[1]}'")

conn.close()
print("\n✅ Done — restart your FastAPI server.")
print("   The monitor will now find and close trades correctly.")