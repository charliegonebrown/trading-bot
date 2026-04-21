# Kraken Pro — Autonomous Hybrid AI Trading Bot

## Project Structure
```
krakenprohackathon/
├── main.py                  # FastAPI app + all endpoints
├── database.py              # SQLite DB connection
├── models.py                # Trade, Portfolio, BotSettings models
├── requirements.txt
├── fix_trades.py            # One-time DB status fix script
├── Migratedb.py             # DB migration script
├── test_diagnostics.py      # Price data diagnostics
│
├── Agent/
│   └── base_agent.py        # HybridTradingAgent (analysis + trade cycle)
│
├── Brokers/
│   ├── Bybit.py             # Bybit crypto broker
│   └── Alphacotrader.py     # Alpaca stock broker
│
├── Strategies/
│   ├── rsi_strategies.py    # RSI + MACD + BB + Slope indicators
│   ├── ai_strategy.py       # Monte Carlo + Gemini AI signal
│   └── mont_carlo.py        # Monte Carlo simulation
│
├── Routers/
│   ├── traders.py           # /api/trades endpoints
│   ├── portfolio.py         # /api/portfolio endpoints
│   └── setting.py           # /api/settings endpoints
│
└── frontend/
    └── src/
        ├── App.tsx
        └── LiveChart.jsx
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```
BYBIT_API_KEY=your_key
BYBIT_SECRET_KEY=your_secret
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
GOOGLE_API_KEY=your_key
```

3. Run the server:
```bash
uvicorn main:app --reload
```

4. Open: http://127.0.0.1:8000
