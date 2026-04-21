"""
Run from your project root:
    python migrate_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_bot.db")

if not os.path.exists(DB_PATH):
    print(f"❌ Not found: {DB_PATH}")
    exit(1)

print(f"✅ Found: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# Show all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"   Tables: {tables}")

# Check existing columns in trades
cur.execute("PRAGMA table_info(trades)")
existing_cols = {row[1] for row in cur.fetchall()}
print(f"   Existing columns: {existing_cols}")

# Add missing columns
to_add = {
    "take_profit": "REAL",
    "stop_loss":   "REAL",
    "notional":    "REAL",
    "exit_price":  "REAL",
    "market_type": "VARCHAR",
}

for col, dtype in to_add.items():
    if col not in existing_cols:
        cur.execute(f"ALTER TABLE trades ADD COLUMN {col} {dtype}")
        print(f"  ✅ Added: trades.{col}")
    else:
        print(f"  ⏭  Already exists: trades.{col}")

conn.commit()
conn.close()
print("\n✅ Migration complete — restart your FastAPI server.")