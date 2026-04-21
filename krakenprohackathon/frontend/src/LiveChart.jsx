import { useEffect, useRef, useState, useCallback } from "react";
import { createChart, CandlestickSeries, ColorType, CrosshairMode } from "lightweight-charts";

const API_BASE = "http://127.0.0.1:8000";

const CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];
const STOCK_SYMBOLS  = [
  "AAPL","MSFT","GOOGL","GOOG","AMZN","META","NVDA","TSLA","NFLX","AMD",
  "INTC","QCOM","AVGO","MU","AMAT","LRCX","KLAC","MRVL","TXN","ADI",
  "JPM","BAC","GS","MS","WFC","C","BLK","AXP","V","MA",
  "JNJ","PFE","MRNA","ABBV","LLY","UNH","CVS","MDT","ISRG","GILD",
  "WMT","TGT","COST","NKE","SBUX","MCD","KO","PEP","DIS",
  "XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","OXY",
  "SPY","QQQ","IWM","DIA","VTI","VOO","GLD","SLV","TLT","HYG",
  "PLTR","SNOW","CRWD","ZS","NET","DDOG","MDB","BILL","HUBS","SHOP",
  "RIVN","LCID","NIO","LI","XPEV","ENPH","SEDG","FSLR","PLUG","BE",
];
const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"];

// Detect if a symbol is a stock (no USDT suffix, in stock list or not a crypto)
const isStock = (symbol) => STOCK_SYMBOLS.includes(symbol?.toUpperCase()) ||
  (!symbol?.toUpperCase().endsWith("USDT") && !symbol?.toUpperCase().endsWith("BTC"));

const COLORS = {
  bg: "#0d0f14", surface: "#13161e", border: "#1e2330",
  text: "#c9d1e0", muted: "#4a5168", up: "#26a69a", down: "#ef5350",
};

const CHART_HEIGHT = 350;
const INTERVAL_MAP = { "1m":"1","5m":"5","15m":"15","1h":"60","4h":"240","1d":"D" };

async function fetchHistoricalKlines(symbol, timeframe, limit = 100) {
  // Route stocks to Alpaca backend, crypto to Bybit
  if (isStock(symbol)) {
    const res = await fetch(`${API_BASE}/api/stock/candles?symbol=${symbol.toUpperCase()}&interval=${timeframe}&limit=${limit}`);
    if (!res.ok) throw new Error(`Stock candles HTTP ${res.status}`);
    return await res.json();  // already [{time, open, high, low, close}]
  }

  // Crypto — Bybit via corsproxy
  const bybitInterval = INTERVAL_MAP[timeframe] || "1";
  const API_BASE = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
  const proxyUrl = `${API_BASE}/api/candles?symbol=${symbol.toUpperCase()}&interval=${bybitInterval}&limit=${limit}`;
  const res  = await fetch(proxyUrl);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  return json.result.list.reverse().map((item) => ({
    time:  parseInt(item[0]) / 1000,
    open:  parseFloat(item[1]),
    high:  parseFloat(item[2]),
    low:   parseFloat(item[3]),
    close: parseFloat(item[4]),
  }));
}

export default function LiveChart({ symbol: propSymbol }) {
  const chartContainerRef = useRef(null);
  const chartRef          = useRef(null);
  const candleSeriesRef   = useRef(null);
  const wsRef             = useRef(null);
  const roRef             = useRef(null);

  // FIX 1: initialise directly from propSymbol — no race on first render
  const [activeSymbol, setActiveSymbol] = useState(
    propSymbol ? propSymbol.toUpperCase() : "BTCUSDT"
  );
  const [timeframe,  setTimeframe]  = useState("1m");
  const [price,      setPrice]      = useState(null);
  const [priceColor, setPriceColor] = useState(COLORS.text);
  const [change,     setChange]     = useState(null);
  const [connStatus, setConnStatus] = useState("connecting");

  // FIX 2: sync prop → state only when it actually differs
  useEffect(() => {
    if (propSymbol && propSymbol.toUpperCase() !== activeSymbol) {
      setActiveSymbol(propSymbol.toUpperCase());
    }
  }, [propSymbol]);

  // Chart init — runs once only
  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.offsetWidth,
      height: CHART_HEIGHT,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: COLORS.muted, fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
      },
      grid: {
        vertLines: { color: COLORS.border },
        horzLines: { color: COLORS.border },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: COLORS.muted, labelBackgroundColor: COLORS.surface },
        horzLine: { color: COLORS.muted, labelBackgroundColor: COLORS.surface },
      },
      rightPriceScale: {
        borderColor: COLORS.border, textColor: COLORS.muted,
        scaleMargins: { top: 0.1, bottom: 0.3 },
      },
      timeScale: { borderColor: COLORS.border, timeVisible: true, rightOffset: 20 },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: COLORS.up, downColor: COLORS.down,
      borderUpColor: COLORS.up, borderDownColor: COLORS.down,
      wickUpColor: COLORS.up, wickDownColor: COLORS.down,
    });

    chartRef.current        = chart;
    candleSeriesRef.current = candleSeries;

    const ro = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      if (width > 0 && chartRef.current) chartRef.current.applyOptions({ width });
    });
    ro.observe(container);
    roRef.current = ro;

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current        = null;
      candleSeriesRef.current = null;
    };
  }, []);

  const connect = useCallback(async () => {
    if (!candleSeriesRef.current) return;

    // FIX 3: kill old WS and null its onmessage BEFORE anything else
    // so stale messages from the old symbol can never update state
    if (wsRef.current) {
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    // FIX 4: clear old candle data so old symbol's price scale is gone
    candleSeriesRef.current.setData([]);
    setPrice(null);
    setChange(null);
    setConnStatus("connecting");

    // Fetch fresh history for the new symbol
    let history;
    try {
      history = await fetchHistoricalKlines(activeSymbol, timeframe);
    } catch (err) {
      console.error("Fetch failed:", err);
      setConnStatus("error");
      return;
    }

    // Guard: component unmounted or symbol changed again while fetching
    if (!candleSeriesRef.current) return;

    candleSeriesRef.current.setData(history);
    chartRef.current?.timeScale().fitContent();

    if (history.length) {
      const last = history[history.length - 1];
      const first = history[0];
      setPrice(last.close);
      setChange(((last.close - first.open) / first.open) * 100);
      setPriceColor(last.close >= last.open ? COLORS.up : COLORS.down);
    }

    // Stocks: no WebSocket — poll price every 15s via Alpaca backend
    if (isStock(activeSymbol)) {
      setConnStatus("live");
      const pollStock = async () => {
        try {
          const r = await fetch(`${API_BASE}/api/stock/price?symbol=${activeSymbol}`);
          const d = await r.json();
          if (d.price && candleSeriesRef.current) {
            setPrice(d.price);
          }
        } catch {}
      };
      pollStock();
      const pollId = setInterval(pollStock, 15000);
      wsRef.current = { close: () => clearInterval(pollId), onmessage: null };
      return;
    }

    // Crypto: Bybit WebSocket
    const ws = new WebSocket("wss://stream.bybit.com/v5/public/linear");
    const bybitInterval = INTERVAL_MAP[timeframe] || "1";

    ws.onopen = () => {
      setConnStatus("live");
      ws.send(JSON.stringify({
        op: "subscribe",
        args: [`kline.${bybitInterval}.${activeSymbol}`]
      }));
    };

    ws.onmessage = (e) => {
      const resp = JSON.parse(e.data);
      if (resp.topic?.startsWith("kline")) {
        const k = resp.data[0];
        if (!candleSeriesRef.current) return;
        candleSeriesRef.current.update({
          time:  parseInt(k.start) / 1000,
          open:  parseFloat(k.open),
          high:  parseFloat(k.high),
          low:   parseFloat(k.low),
          close: parseFloat(k.close),
        });
        const cp = parseFloat(k.close);
        setPrice(cp);
        setPriceColor(cp >= parseFloat(k.open) ? COLORS.up : COLORS.down);
      }
    };

    ws.onerror = () => setConnStatus("error");
    ws.onclose = () => { if (wsRef.current === ws) setConnStatus("disconnected"); };
    wsRef.current = ws;

  }, [activeSymbol, timeframe]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.onmessage = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const statusDot = ({
    live:         { color: COLORS.up,    label: "LIVE" },
    connecting:   { color: "#f0a500",    label: "CONNECTING" },
    error:        { color: COLORS.down,  label: "ERROR" },
    disconnected: { color: COLORS.muted, label: "DISCONNECTED" },
  })[connStatus] || { color: COLORS.muted, label: "—" };

  const formatPrice = (p) => {
    if (p == null) return "—";
    return p >= 1000 ? p.toLocaleString(undefined, { minimumFractionDigits: 2 }) : p.toFixed(4);
  };

  const btnStyle = (active) => ({
    background: active ? COLORS.border : "transparent",
    border: `1px solid ${active ? COLORS.muted : "transparent"}`,
    borderRadius: 6, color: active ? COLORS.text : COLORS.muted,
    fontSize: 11, padding: "4px 10px", cursor: "pointer",
    fontFamily: "inherit", transition: "0.15s",
  });

  return (
    <div style={{
      background: COLORS.bg, borderRadius: 12,
      border: `1px solid ${COLORS.border}`, overflow: "hidden",
      fontFamily: "'IBM Plex Mono', monospace",
      display: "flex", flexDirection: "column",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />

      {/* Symbol + interval toolbar */}
      <div style={{ background: COLORS.surface, borderBottom: `1px solid ${COLORS.border}`, padding: "10px 14px", display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ display: "flex", gap: 4 }}>
          {CRYPTO_SYMBOLS.map((s) => (
            <button key={s} onClick={() => setActiveSymbol(s)} style={btnStyle(activeSymbol === s)}>
              {s.replace("USDT", "")}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
          {INTERVALS.map((iv) => (
            <button key={iv} onClick={() => setTimeframe(iv)} style={btnStyle(timeframe === iv)}>
              {iv}
            </button>
          ))}
        </div>
      </div>

      {/* Price bar */}
      <div style={{ padding: "8px 14px", borderBottom: `1px solid ${COLORS.border}`, display: "flex", alignItems: "baseline", gap: 10 }}>
        <span style={{ fontSize: 20, fontWeight: 500, color: priceColor }}>
          {formatPrice(price)}
        </span>
        {change != null && (
          <span style={{ fontSize: 12, color: change >= 0 ? COLORS.up : COLORS.down }}>
            {change >= 0 ? "+" : ""}{change.toFixed(2)}%
          </span>
        )}
        <span style={{ marginLeft: "auto", fontSize: 10, display: "flex", alignItems: "center", gap: 5, color: COLORS.muted }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: statusDot.color }} />
          {statusDot.label}
        </span>
      </div>

      {/* Chart canvas */}
      <div ref={chartContainerRef} style={{
        width: "100%", height: `${CHART_HEIGHT}px`,
        padding: "10px 10px 25px 10px", boxSizing: "border-box",
      }} />
    </div>
  );
}