// @ts-nocheck
import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import LiveChart from "./LiveChart";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// ─── Full Market Data ─────────────────────────────────────────────────────────
const MARKET_DATA = {
  Crypto: [
    // Large Cap
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","TRXUSDT","AVAXUSDT","TONUSDT",
    // Mid Cap
    "DOTUSDT","POLUSDT","LINKUSDT","LTCUSDT","BCHUSDT","ATOMUSDT","UNIUSDT","XLMUSDT","ETCUSDT","APTUSDT",
    // DeFi
    "AAVEUSDT","MKRUSDT","SNXUSDT","CRVUSDT","COMPUSDT","LDOUSDT","1INCHUSDT","BALUSDT","YFIUSDT","SUSHIUSDT",
    // Layer 2 / Scaling
    "ARBUSDT","OPUSDT","STRKUSDT","ZKUSDT","MANTAUSDT","SCROLLUSDT","METISUSDT","IMXUSDT","LOOMUSDT","POLYUSDT",
    // AI / Data
    "FETUSDT","RENDERUSDT","WLDUSDT","OCEANUSDT","AGIXUSDT","NMRUSDT","GRTUSDT","CTXCUSDT","RAIUSDT","PHAUSDT",
    // Gaming / NFT / Metaverse
    "AXSUSDT","SANDUSDT","MANAUSDT","GALAUSDT","APEUSDT","ENJUSDT","FLOWUSDT","IMXUSDT","GMTUSDT","GMTUSDT",
    // Emerging / Trending
    "SUIUSDT","SEIUSDT","TONUSDT","INJUSDT","TIAUSUT","NEARUSDT","FTMUSDT","ALGOUSDT","ICPUSDT","HBARUSDT",
    "RUNEUSDT","FILUSDT","BLURUSDT","WLDUSDT","JUPUSDT","DYMUSDT","STXUSDT","MINAUSDT","CFXUSDT","CKBUSDT",
    // Infra / Interop
    "QNTUSDT","VETUSDT","HNTUSDT","IOTAUSDT","XDCUSDT","ZILUSDT","ONTUSDT","WAVESUSDT","KAVAUSDT","BANDUSDT",
  ],
  Forex: [
    // Majors
    "EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD","NZDUSD",
    // Crosses
    "EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD",
    "GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD",
    "AUDJPY","AUDCHF","AUDCAD","AUDNZD",
    "CADJPY","CADCHF","NZDJPY","NZDCHF","CHFJPY",
    // Exotics
    "USDZAR","USDMXN","USDBRL","USDSGD","USDHKD","USDTRY","USDNOK","USDSEK","USDDKK","USDPLN",
  ],
  Stocks: [
    // Big Tech
    "AAPL","MSFT","GOOGL","GOOG","AMZN","META","NVDA","TSLA","NFLX","AMD",
    // Semiconductors
    "INTC","QCOM","AVGO","MU","AMAT","LRCX","KLAC","MRVL","TXN","ADI",
    // Finance
    "JPM","BAC","GS","MS","WFC","C","BLK","AXP","V","MA",
    // Healthcare
    "JNJ","PFE","MRNA","ABBV","LLY","UNH","CVS","MDT","ISRG","GILD",
    // Consumer
    "AMZN","WMT","TGT","COST","NKE","SBUX","MCD","KO","PEP","DIS",
    // Energy
    "XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","OXY",
    // ETFs & Index
    "SPY","QQQ","IWM","DIA","VTI","VOO","GLD","SLV","TLT","HYG",
    // Growth / Momentum
    "PLTR","SNOW","CRWD","ZS","NET","DDOG","MDB","BILL","HUBS","SHOP",
    // EV / Clean Energy
    "RIVN","LCID","NIO","LI","XPEV","ENPH","SEDG","FSLR","PLUG","BE",
  ]
};

// ─── Interval Config ──────────────────────────────────────────────────────────
const INTERVALS = [
  { label: "1m",  value: "1"   },
  { label: "15m", value: "15"  },
  { label: "1h",  value: "60"  },
  { label: "4h",  value: "240" },
  { label: "1D",  value: "D"   },
];
const INTERVAL_HINTS = {
  "1":   "⚠️ 1m: noisy — MC may be low",
  "15":  "Short-term, moderate noise",
  "60":  "✅ Recommended — best quality",
  "240": "4h trend, fewer signals",
  "D":   "Daily macro view",
};

// ─── Component: Real-time Price Sidebar ───────────────────────────────────────
function PriceSidebar() {
  const [prices, setPrices] = useState({});

  useEffect(() => {
    const fetchPrices = async () => {
      const symbols = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"];
      const results = {};
      await Promise.allSettled(symbols.map(async (s) => {
        try {
          const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(`https://api.bytick.com/v5/market/tickers?category=linear&symbol=${s}`)}`);
          const d = await res.json();
          const item = d?.result?.list?.[0];
          if (item) {
            results[s] = {
              price: parseFloat(item.lastPrice),
              change: parseFloat(item.price24hPcnt) * 100,
            };
          }
        } catch {}
      }));
      setPrices(results);
    };
    fetchPrices();
    const id = setInterval(fetchPrices, 10000);
    return () => clearInterval(id);
  }, []);

  const forexFeed = [
    { s: "EUR/USD", p: "1.0842", c: "+0.1%" },
    { s: "GBP/JPY", p: "191.20", c: "+0.5%" },
    { s: "USD/JPY", p: "149.80", c: "-0.2%" },
  ];
  const [stockPrices, setStockPrices] = useState({});
  useEffect(() => {
    const fetchStocks = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/stock/prices`, {
          params: { symbols: "NVDA,TSLA,AAPL,AMZN,MSFT,META,GOOGL,NFLX" }
        });
        setStockPrices(res.data || {});
      } catch {}
    };
    fetchStocks();
    const id = setInterval(fetchStocks, 30000);
    return () => clearInterval(id);
  }, []);
  const stockSymbols = ["NVDA","TSLA","AAPL","AMZN","MSFT","META","GOOGL","NFLX"];

  return (
    <div className="hidden xl:flex flex-col w-64 bg-gray-950/80 border-l border-gray-800 h-screen sticky top-0 overflow-y-auto p-5 backdrop-blur-md">
      <h3 className="text-[10px] font-black text-emerald-500 uppercase tracking-[0.2em] mb-8">Live Feed</h3>
      <div className="space-y-8">
        <div>
          <p className="text-[9px] font-black text-gray-600 uppercase mb-4 tracking-widest">Crypto</p>
          <div className="space-y-4">
            {["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"].map(s => {
              const d = prices[s];
              const isPos = d ? d.change >= 0 : false;
              return (
                <div key={s} className="flex justify-between items-center group cursor-pointer">
                  <div>
                    <p className="text-xs font-black group-hover:text-emerald-400 transition-colors">{s.replace("USDT","")}</p>
                    <p className="text-[10px] font-mono text-gray-500">
                      {d ? (d.price >= 1000 ? `$${d.price.toLocaleString(undefined,{minimumFractionDigits:2})}` : `$${d.price.toFixed(4)}`) : "—"}
                    </p>
                  </div>
                  <span className={`text-[10px] font-bold ${isPos ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {d ? `${isPos?'+':''}${d.change.toFixed(2)}%` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
        <div>
          <p className="text-[9px] font-black text-gray-600 uppercase mb-4 tracking-widest">Forex</p>
          <div className="space-y-4">
            {forexFeed.map(i => (
              <div key={i.s} className="flex justify-between items-center group cursor-pointer">
                <div>
                  <p className="text-xs font-black group-hover:text-emerald-400 transition-colors">{i.s}</p>
                  <p className="text-[10px] font-mono text-gray-500">{i.p}</p>
                </div>
                <span className={`text-[10px] font-bold ${i.c.includes('+') ? 'text-emerald-500' : 'text-rose-500'}`}>{i.c}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="text-[9px] font-black text-gray-600 uppercase mb-4 tracking-widest">Stocks</p>
          <div className="space-y-4">
            {stockSymbols.map(s => {
              const d = stockPrices[s];
              const isPos = d ? d.change_pct >= 0 : false;
              return (
                <div key={s} className="flex justify-between items-center group cursor-pointer">
                  <div>
                    <p className="text-xs font-black group-hover:text-emerald-400 transition-colors">{s}</p>
                    <p className="text-[10px] font-mono text-gray-500">
                      {d && d.price > 0 ? `$${d.price.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}` : "—"}
                    </p>
                  </div>
                  <span className={`text-[10px] font-bold ${isPos ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {d && d.price > 0 ? `${isPos?'+':''}${d.change_pct.toFixed(2)}%` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Component: Bottom Data Panel ─────────────────────────────────────────────
function BottomDataPanel({ trades, instruments, onCloseTrade }) {
  const [activeTab, setActiveTab] = useState("logs");
  const [closingId, setClosingId] = useState(null);

  const handleClose = async (tradeId) => {
    if (!window.confirm(`Close trade TX-${tradeId} at live price?`)) return;
    setClosingId(tradeId);
    try {
      const res = await axios.delete(`${API_BASE}/api/trades/${tradeId}`);
      const d   = res.data;
      const pnl = d.pnl || 0;
      alert(
        `${pnl >= 0 ? '✅ Profit' : '❌ Loss'} — TX-${tradeId} Closed\n\n` +
        `${d.symbol} ${d.side?.toUpperCase()}\n` +
        `Entry:  $${(d.entry  || 0).toLocaleString('en-US', {minimumFractionDigits:2})}\n` +
        `Exit:   $${(d.exit   || 0).toLocaleString('en-US', {minimumFractionDigits:2})}\n` +
        `PnL:    ${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString('en-US', {minimumFractionDigits:2})}\n` +
        `${d.message || ''}\n\n` +
        `New Balance: $${(d.new_balance || 0).toLocaleString('en-US', {minimumFractionDigits:2})}`
      );
      if (onCloseTrade) onCloseTrade();
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message;
      alert(`❌ Failed to close TX-${tradeId}: ${msg}`);
    } finally {
      setClosingId(null);
    }
  };

  const priceMap = {};
  instruments.forEach(inst => {
    const sym = inst.pair?.replace('/', '') || inst.symbol;
    if (sym) priceMap[sym] = parseFloat(inst.price?.replace(',', '') || "0");
  });

  return (
    <div className="bg-gray-800/20 border border-gray-700/50 rounded-[2rem] overflow-hidden mt-10">
      <div className="px-8 pt-6 border-b border-gray-800 bg-gray-900/30 flex justify-between items-end">
        <div className="flex gap-8">
          <button onClick={() => setActiveTab('logs')} className={`text-[10px] font-black uppercase tracking-widest pb-4 border-b-2 transition-all ${activeTab === 'logs' ? 'border-emerald-500 text-white' : 'border-transparent text-gray-500 hover:text-gray-400'}`}>
            Global Log Hub
          </button>
          <button onClick={() => setActiveTab('instruments')} className={`text-[10px] font-black uppercase tracking-widest pb-4 border-b-2 transition-all ${activeTab === 'instruments' ? 'border-emerald-500 text-white' : 'border-transparent text-gray-500 hover:text-gray-400'}`}>
            Live Instruments
          </button>
        </div>
        <span className="text-[9px] text-gray-600 font-mono pb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span> Sync: Stable
        </span>
      </div>
      <div className="overflow-x-auto min-h-[250px] max-h-[350px]">
        {activeTab === "logs" ? (
          <table className="w-full text-left text-[11px]">
            <thead>
              <tr className="text-gray-600 uppercase font-black tracking-widest border-b border-gray-800/50">
                <th className="px-6 py-4">Order ID</th><th className="px-4 py-4">Asset</th>
                <th className="px-4 py-4">Side</th><th className="px-4 py-4">Entry</th>
                <th className="px-4 py-4">Current</th><th className="px-4 py-4">TP</th>
                <th className="px-4 py-4">SL</th><th className="px-4 py-4">Qty</th>
                <th className="px-4 py-4 text-right">Unreal. P&L</th>
                <th className="px-6 py-4 text-right">Status</th>
                <th className="px-4 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {trades.length === 0 ? (
                <tr><td colSpan="10" className="text-center py-8 text-gray-600 font-mono italic">No trades executed yet.</td></tr>
              ) : trades.map(tx => {
                const livePrice = priceMap[tx.symbol] || 0;
                const entryPrice = tx.entry_price || 0;
                const qty = tx.quantity || 0;
                let unrealisedPnl = 0;
                if (livePrice > 0 && entryPrice > 0 && tx.status === 'open') {
                  unrealisedPnl = tx.side === 'buy'
                    ? (livePrice - entryPrice) * qty
                    : (entryPrice - livePrice) * qty;
                }
                const pnlPct = entryPrice > 0 ? ((unrealisedPnl / (entryPrice * qty)) * 100) : 0;
                const s = (tx.status?.value || tx.status || '').toLowerCase();
                return (
                  <tr key={tx.id} className="hover:bg-gray-700/10 transition-colors">
                    <td className="px-6 py-4 text-gray-500 font-mono">TX-{tx.id}</td>
                    <td className="px-4 py-4 font-black">{tx.symbol}</td>
                    <td className={`px-4 py-4 font-black uppercase ${tx.side === 'buy' ? 'text-emerald-400' : 'text-rose-400'}`}>{tx.side}</td>
                    <td className="px-4 py-4 font-mono">${entryPrice?.toFixed(2)}</td>
                    <td className="px-4 py-4 font-mono text-blue-400">{livePrice > 0 ? `$${livePrice.toLocaleString('en-US', {minimumFractionDigits:2})}` : '—'}</td>
                    <td className="px-4 py-4 font-mono text-emerald-400">{tx.take_profit ? `$${tx.take_profit.toFixed(2)}` : '—'}</td>
                    <td className="px-4 py-4 font-mono text-rose-400">{tx.stop_loss ? `$${tx.stop_loss.toFixed(2)}` : '—'}</td>
                    <td className="px-4 py-4 font-mono">{qty}</td>
                    <td className="px-4 py-4 text-right">
                      {(s === 'closed_tp' || s === 'closed_sl' || s === 'closed') && tx.pnl != null ? (
                        <div>
                          <p className={`font-black font-mono ${(tx.pnl||0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {(tx.pnl||0) >= 0 ? '+' : ''}${(tx.pnl||0).toFixed(2)}
                          </p>
                          <p className={`text-[9px] font-mono ${s === 'closed_tp' ? 'text-emerald-600' : s === 'closed_sl' ? 'text-rose-600' : 'text-gray-500'}`}>
                            {s === 'closed_tp' ? '✓ TP hit' : s === 'closed_sl' ? '✗ SL hit' : 'manual'}
                          </p>
                        </div>
                      ) : s === 'open' && livePrice > 0 ? (
                        <div>
                          <p className={`font-black font-mono ${unrealisedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{unrealisedPnl >= 0 ? '+' : ''}${unrealisedPnl.toFixed(2)}</p>
                          <p className={`text-[9px] font-mono ${unrealisedPnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>{unrealisedPnl >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%</p>
                        </div>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {s === 'open'      && <span className="px-3 py-1 rounded-full text-[9px] font-black uppercase bg-amber-500/10 text-amber-500">● Open</span>}
                      {s === 'closed_tp' && <span className="px-3 py-1 rounded-full text-[9px] font-black uppercase bg-emerald-500/10 text-emerald-400">✓ TP Hit</span>}
                      {s === 'closed_sl' && <span className="px-3 py-1 rounded-full text-[9px] font-black uppercase bg-rose-500/10 text-rose-400">✗ SL Hit</span>}
                      {s === 'closed'    && <span className="px-3 py-1 rounded-full text-[9px] font-black uppercase bg-gray-600/20 text-gray-400">✕ Closed</span>}
                      {s !== 'open' && s !== 'closed_tp' && s !== 'closed_sl' && s !== 'closed' && <span className="px-3 py-1 rounded-full text-[9px] font-black uppercase bg-gray-700 text-gray-400">{s}</span>}
                    </td>
                    <td className="px-4 py-4 text-right">
                      {s === 'open' ? (
                        <button
                          onClick={() => handleClose(tx.id)}
                          disabled={closingId === tx.id}
                          className="px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-wider transition-all border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {closingId === tx.id ? '...' : '✕ Close'}
                        </button>
                      ) : (
                        <span className="text-gray-700 text-[9px]">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-left text-[11px]">
            <thead>
              <tr className="text-gray-600 uppercase font-black tracking-widest border-b border-gray-800/50">
                <th className="px-8 py-4">Market Pair</th><th className="px-4 py-4">Last Price</th>
                <th className="px-4 py-4">24h Change</th><th className="px-4 py-4">Volume</th>
                <th className="px-8 py-4 text-right">Engine Momentum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {instruments.length === 0 ? (
                <tr><td colSpan="5" className="text-center py-8 text-gray-600 font-mono italic">Loading market data...</td></tr>
              ) : instruments.map((inst, i) => {
                const isPositive = String(inst.change).startsWith('+');
                return (
                  <tr key={i} className="hover:bg-gray-700/10 transition-colors cursor-pointer group">
                    <td className="px-8 py-4 font-black group-hover:text-emerald-400 transition-colors">{inst.pair || inst.symbol}</td>
                    <td className="px-4 py-4 font-mono">${inst.price}</td>
                    <td className={`px-4 py-4 font-black ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>{inst.change}</td>
                    <td className="px-4 py-4 text-gray-400 font-mono">{inst.vol || inst.volume}</td>
                    <td className="px-8 py-4 text-right">
                      <span className={`px-3 py-1 rounded border text-[9px] font-black ${isPositive ? 'border-emerald-500/20 text-emerald-400 bg-emerald-500/5' : 'border-rose-500/20 text-rose-400 bg-rose-500/5'}`}>
                        {inst.momentum || 'Neutral'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Component: Analysis Preview Card ─────────────────────────────────────────
function AnalysisCard({ analysis, onConfirm, onDismiss, isExecuting }) {
  if (!analysis) return null;
  const actionColor = analysis.action === 'buy' ? 'text-emerald-400' : analysis.action === 'sell' ? 'text-rose-400' : 'text-amber-400';
  const confidencePct = Math.round((analysis.confidence || 0) * 100);
  return (
    <div className="mt-4 bg-gray-900/80 border border-blue-500/30 rounded-2xl p-5 space-y-4 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-black text-blue-400 uppercase tracking-widest">AI Analysis Ready</span>
        <button onClick={onDismiss} className="text-gray-600 hover:text-gray-400 text-xs font-black">✕</button>
      </div>
      <div className="flex items-center gap-3">
        <span className={`text-2xl font-black uppercase ${actionColor}`}>{analysis.action}</span>
        <div className="flex-1 bg-gray-800 rounded-full h-1.5">
          <div className={`h-1.5 rounded-full transition-all ${analysis.action === 'buy' ? 'bg-emerald-500' : analysis.action === 'sell' ? 'bg-rose-500' : 'bg-amber-500'}`} style={{ width: `${confidencePct}%` }} />
        </div>
        <span className="text-[10px] font-mono text-gray-400">{confidencePct}% conf.</span>
      </div>
      <p className="text-[10px] text-gray-400 leading-relaxed border-l-2 border-blue-500/40 pl-3">{analysis.reason}</p>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-gray-800/60 rounded-xl p-2">
          <p className="text-[8px] text-gray-600 uppercase font-black mb-1">Monte Carlo</p>
          <p className="text-sm font-black text-blue-400">{analysis.mc_probability?.toFixed(1)}%</p>
        </div>
        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-2">
          <p className="text-[8px] text-gray-600 uppercase font-black mb-1">Take Profit</p>
          <p className="text-sm font-black text-emerald-400">+{analysis.suggested_tp_pct?.toFixed(2)}%</p>
        </div>
        <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-2">
          <p className="text-[8px] text-gray-600 uppercase font-black mb-1">Stop Loss</p>
          <p className="text-sm font-black text-rose-400">-{analysis.suggested_sl_pct?.toFixed(2)}%</p>
        </div>
      </div>
      {analysis.action !== 'hold' ? (
        <button onClick={() => onConfirm(analysis.action)} disabled={isExecuting}
          className={`w-full py-3 rounded-xl font-black uppercase text-xs tracking-widest transition-all disabled:opacity-50 disabled:cursor-not-allowed ${analysis.action === 'buy' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'}`}>
          {isExecuting ? 'Executing...' : `Confirm ${analysis.action.toUpperCase()} Order`}
        </button>
      ) : (
        <div className="space-y-2">
          <p className="text-[9px] text-amber-500/80 font-black uppercase text-center tracking-widest">⚠️ AI says HOLD — manual override</p>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => onConfirm('buy')} disabled={isExecuting}
              className="py-3 rounded-xl font-black uppercase text-xs tracking-widest bg-emerald-900/50 hover:bg-emerald-700 border border-emerald-700/50 text-emerald-400 disabled:opacity-50 transition-all">
              {isExecuting ? '...' : '↑ Force BUY'}
            </button>
            <button onClick={() => onConfirm('sell')} disabled={isExecuting}
              className="py-3 rounded-xl font-black uppercase text-xs tracking-widest bg-rose-900/50 hover:bg-rose-700 border border-rose-700/50 text-rose-400 disabled:opacity-50 transition-all">
              {isExecuting ? '...' : '↓ Force SELL'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Live News Panel — fetches via FastAPI backend ────────────────────────────
// Backend calls Anthropic with web_search so the API key never touches the browser.
function LiveNewsPanel() {
  const [news, setNews]           = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  const fetchNews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/api/news`);
      if (Array.isArray(res.data) && res.data.length > 0) {
        setNews(res.data);
        setLastFetch(new Date());
      }
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Could not load news";
      setError(msg);
      console.error("News fetch error:", msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();
    const id = setInterval(fetchNews, 15 * 60 * 1000); // refresh every 15 min
    return () => clearInterval(id);
  }, [fetchNews]);

  const tagColor = (tag) => ({
    Crypto: "text-emerald-400", Stocks: "text-blue-400", Forex: "text-yellow-400",
    Macro: "text-amber-400", DeFi: "text-purple-400", Regulation: "text-rose-400",
    Tech: "text-cyan-400", Business: "text-indigo-400"
  })[tag] || "text-gray-400";

  const sentColor = (s) =>
    s === 'bullish' ? 'text-emerald-500' : s === 'bearish' ? 'text-rose-500' : 'text-amber-500';

  return (
    <div className="bg-gray-900/40 border border-gray-800 rounded-[2rem] p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
          Live Market News
        </h3>
        <div className="flex items-center gap-2">
          {lastFetch && <span className="text-[8px] text-gray-600 font-mono">{lastFetch.toLocaleTimeString()}</span>}
          <button onClick={fetchNews} disabled={loading}
            className="text-[9px] text-gray-600 hover:text-white font-black transition-colors disabled:opacity-40"
            title="Refresh news">
            {loading ? '⟳' : '↺'}
          </button>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && news.length === 0 && (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="animate-pulse space-y-2">
              <div className="h-2 bg-gray-800 rounded w-1/4" />
              <div className="h-3 bg-gray-800 rounded w-full" />
              <div className="h-2 bg-gray-800 rounded w-3/4" />
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && news.length === 0 && (
        <div className="space-y-3">
          <p className="text-[9px] text-rose-400 font-mono border border-rose-500/20 bg-rose-500/5 rounded-xl p-3">
            ❌ {error}
          </p>
          <p className="text-[9px] text-gray-600 leading-relaxed">
            Make sure your FastAPI backend is running at <span className="text-gray-400 font-mono">localhost:8000</span> and has internet access to reach RSS feeds.
          </p>
          <button onClick={fetchNews}
            className="w-full py-2 rounded-xl text-[9px] font-black uppercase tracking-widest bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* News list */}
      {news.length > 0 && (
        <div className="space-y-4">
          {news.map((item, i) => (
            <div key={i} className="border-b border-gray-800/50 pb-4 last:border-0 last:pb-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded bg-gray-800 ${tagColor(item.tag)}`}>{item.tag}</span>
                <span className="text-[8px] text-gray-600 font-mono">{item.time}</span>
                {item.sentiment && (
                  <span className={`text-[8px] font-black ml-auto ${sentColor(item.sentiment)}`}>● {item.sentiment}</span>
                )}
              </div>
              <p className="text-[10px] text-gray-300 leading-relaxed font-medium">{item.title}</p>
              {item.summary && <p className="text-[9px] text-gray-600 mt-1 leading-relaxed">{item.summary}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Component: AI Hub ────────────────────────────────────────────────────────
function AiHubView({ symbols, candleInterval, portfolio, onExecute, isExecuting, onSetAnalysis, onSetTpPrice, onSetSlPrice, onSetSelectedSymbol, onSetTradeSide, onSetView }) {
  const [scans, setScans]           = useState({});
  const [scanning, setScanning]     = useState(false);
  const [lastScan, setLastScan]     = useState(null);
  const [nextScanIn, setNextScanIn] = useState(60);
  const [activeCategory, setActiveCategory] = useState("Crypto");
  const [scanCategory, setScanCategory]     = useState("Crypto");
  const scanningRef = useRef(false);

  // Use a subset for scanning based on category (scan top 12 crypto, all others)
  const scanSymbols = useCallback(() => {
    if (scanCategory === "Crypto") return symbols.slice(0, 12);
    if (scanCategory === "Forex")  return MARKET_DATA.Forex.slice(0, 8);
    // Top 15 most liquid stocks for scanning
    return ["AAPL","MSFT","NVDA","TSLA","AMZN","META","GOOGL","AMD","JPM","NFLX","V","SPY","QQQ","PLTR","CRWD"];
  }, [symbols, scanCategory]);

  const STOCK_LIST = [
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

  const runScan = useCallback(async () => {
    if (scanningRef.current) return;
    scanningRef.current = true;
    setScanning(true);
    setNextScanIn(60);
    const toScan = scanSymbols();
    const isStockScan = scanCategory === "Stocks";

    await Promise.allSettled(toScan.map(async (symbol) => {
      setScans(prev => ({ ...prev, [symbol]: { ...prev[symbol], loading: true } }));
      try {
        let price = 0;
        let signal = {};

        if (isStockScan) {
          // Stocks → Alpaca endpoints
          const [priceRes, analyseRes] = await Promise.all([
            axios.get(`${API_BASE}/api/stock/price`, { params: { symbol } }),
            axios.get(`${API_BASE}/api/stock/analyse`, { params: { symbol, interval: candleInterval } })
          ]);
          price  = priceRes.data?.price || 0;
          signal = analyseRes.data;
        } else {
          // Crypto → Bybit endpoints
          const [priceRes, analyseRes] = await Promise.all([
            axios.get(`${API_BASE}/api/price`, { params: { symbol } }),
            axios.get(`${API_BASE}/api/analyse`, { params: { symbol, interval: candleInterval } })
          ]);
          price  = priceRes.data?.price || 0;
          signal = analyseRes.data;
        }

        const tp = price > 0 && signal.suggested_tp_pct ? price * (1 + signal.suggested_tp_pct / 100) : 0;
        const sl = price > 0 && signal.suggested_sl_pct ? price * (1 - signal.suggested_sl_pct / 100) : 0;
        setScans(prev => ({ ...prev, [symbol]: { ...signal, price, tp, sl, loading: false, scannedAt: new Date() } }));
      } catch (e) {
        setScans(prev => ({ ...prev, [symbol]: { action: 'error', reason: String(e), loading: false, price: 0 } }));
      }
    }));

    setLastScan(new Date());
    setScanning(false);
    scanningRef.current = false;
  }, [scanSymbols, candleInterval, scanCategory]);

  useEffect(() => {
    setScans({});
    runScan();
  }, [scanCategory]);

  useEffect(() => {
    const scanId = setInterval(runScan, 60000);
    const tickId = setInterval(() => setNextScanIn(prev => prev <= 1 ? 60 : prev - 1), 1000);
    return () => { clearInterval(scanId); clearInterval(tickId); };
  }, [runScan]);

  const handleExecuteFromHub = (symbol, signal) => {
    onSetSelectedSymbol(symbol);
    onSetAnalysis({ ...signal, current_price: signal.price || signal.current_price });
    if (signal.tp) onSetTpPrice(signal.tp.toFixed(2));
    if (signal.sl) onSetSlPrice(signal.sl.toFixed(2));
    if (signal.action === 'buy' || signal.action === 'sell') onSetTradeSide(signal.action);
    onSetView('dashboard');
  };

  const ac  = (a) => a === 'buy' ? 'text-emerald-400' : a === 'sell' ? 'text-rose-400' : 'text-amber-400';
  const ab  = (a) => a === 'buy' ? 'border-emerald-500/30 bg-emerald-500/5' : a === 'sell' ? 'border-rose-500/30 bg-rose-500/5' : 'border-gray-700/50 bg-gray-800/10';
  const abg = (a) => a === 'buy' ? 'bg-emerald-500/20 text-emerald-400' : a === 'sell' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/10 text-amber-500';

  const toScan    = scanSymbols();
  const opps      = Object.entries(scans).filter(([s, d]) => (d.action === 'buy' || d.action === 'sell') && toScan.includes(s));
  const holds     = Object.entries(scans).filter(([s, d]) => d.action === 'hold' && toScan.includes(s));

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 animate-in fade-in duration-500">
      <div className="xl:col-span-9 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-2xl font-black uppercase tracking-tighter">AI Opportunity Scanner</h2>
            <p className="text-[10px] text-gray-500 mt-1">
              Scanning {toScan.length} pairs · {candleInterval === "60" ? "1h" : candleInterval === "240" ? "4h" : candleInterval + "m"} candles ·{" "}
              {lastScan ? `Last: ${lastScan.toLocaleTimeString()}` : "Starting..."}
              {!scanning && <span className="text-gray-600"> · next in {nextScanIn}s</span>}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Category selector */}
            <div className="flex bg-gray-900 rounded-xl p-1 gap-1">
              {["Crypto","Forex","Stocks"].map(cat => (
                <button key={cat} onClick={() => setScanCategory(cat)}
                  className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${scanCategory === cat ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}>
                  {cat}
                </button>
              ))}
            </div>
            <button onClick={runScan} disabled={scanning}
              className="px-6 py-3 rounded-2xl font-black uppercase text-xs tracking-widest transition-all bg-blue-600 hover:bg-blue-500 disabled:opacity-50 flex items-center gap-2">
              {scanning ? <><span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />Scanning...</> : "↺ Scan Now"}
            </button>
          </div>
        </div>

        {/* Opportunities */}
        {opps.length > 0 && (
          <div>
            <p className="text-[9px] font-black text-emerald-500 uppercase tracking-widest mb-4">
              ● {opps.length} Opportunit{opps.length === 1 ? 'y' : 'ies'} Found
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {opps.map(([symbol, signal]) => (
                <div key={symbol} className={`border rounded-[2rem] p-6 space-y-4 transition-all hover:scale-[1.01] ${ab(signal.action)}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="text-xl font-black tracking-tighter">
                          {symbol.replace('USDT','')}<span className="text-gray-600">{symbol.includes('USDT') ? '/USDT' : ''}</span>
                        </h3>
                        <span className={`px-2 py-0.5 rounded-lg text-[10px] font-black uppercase ${abg(signal.action)}`}>{signal.action}</span>
                      </div>
                      <p className="text-[10px] text-gray-500 font-mono mt-1">
                        ${signal.price > 0 ? signal.price.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '—'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[9px] text-gray-600 uppercase font-black">Confidence</p>
                      <p className={`text-2xl font-black ${ac(signal.action)}`}>{Math.round((signal.confidence || 0) * 100)}%</p>
                    </div>
                  </div>
                  <p className="text-[10px] text-gray-400 leading-relaxed border-l-2 border-blue-500/30 pl-3">{signal.reason}</p>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-gray-900/60 rounded-xl p-2">
                      <p className="text-[8px] text-gray-600 uppercase font-black mb-1">MC Prob</p>
                      <p className="text-sm font-black text-blue-400">{signal.mc_probability?.toFixed(1)}%</p>
                    </div>
                    <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-2">
                      <p className="text-[8px] text-gray-600 uppercase font-black mb-1">TP</p>
                      <p className="text-sm font-black text-emerald-400">+{signal.suggested_tp_pct?.toFixed(2)}%</p>
                    </div>
                    <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-2">
                      <p className="text-[8px] text-gray-600 uppercase font-black mb-1">SL</p>
                      <p className="text-sm font-black text-rose-400">-{signal.suggested_sl_pct?.toFixed(2)}%</p>
                    </div>
                  </div>
                  <button onClick={() => handleExecuteFromHub(symbol, signal)} disabled={isExecuting}
                    className={`w-full py-3 rounded-xl font-black uppercase text-xs tracking-widest transition-all disabled:opacity-50 ${signal.action === 'buy' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'}`}>
                    {signal.action === 'buy' ? '↑ Execute BUY' : '↓ Execute SELL'} {symbol.replace('USDT','')}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scanning skeleton */}
        {scanning && Object.keys(scans).length === 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {toScan.slice(0,6).map(s => (
              <div key={s} className="border border-gray-800 rounded-[2rem] p-6 animate-pulse space-y-3">
                <div className="h-5 bg-gray-800 rounded w-1/3" />
                <div className="h-3 bg-gray-800 rounded w-2/3" />
                <div className="grid grid-cols-3 gap-2">{[0,1,2].map(i => <div key={i} className="h-12 bg-gray-800 rounded-xl" />)}</div>
              </div>
            ))}
          </div>
        )}

        {/* Hold signals */}
        {holds.length > 0 && (
          <div>
            <p className="text-[9px] font-black text-gray-600 uppercase tracking-widest mb-3">Monitoring — {holds.length} pairs holding</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {holds.map(([symbol, signal]) => (
                <div key={symbol} className="border border-gray-800 rounded-2xl p-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-black">{symbol.replace('USDT','')}</p>
                    <p className="text-[9px] text-gray-600 font-mono">${signal.price > 0 ? signal.price.toLocaleString('en-US', { minimumFractionDigits: 0 }) : '—'}</p>
                  </div>
                  <div className="text-right">
                    <span className="px-2 py-0.5 rounded text-[9px] font-black uppercase bg-amber-500/10 text-amber-500">Hold</span>
                    <p className="text-[8px] text-gray-600 font-mono mt-1">MC {signal.mc_probability?.toFixed(0)}%</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!scanning && Object.keys(scans).length === 0 && (
          <div className="text-center py-20 text-gray-600">
            <p className="text-4xl mb-4">🔍</p>
            <p className="font-black uppercase text-sm">No scan results yet</p>
            <p className="text-xs mt-2">Click "Scan Now" to analyse all pairs</p>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <div className="xl:col-span-3 space-y-4">
        {/* LIVE AI news */}
        <LiveNewsPanel />

        {/* Portfolio summary */}
        <div className="bg-gray-900/40 border border-gray-800 rounded-[2rem] p-6 space-y-4">
          <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Portfolio</h3>
          <div className="space-y-3">
            {[
              ["Balance", `$${portfolio.current_balance?.toLocaleString('en-US', { minimumFractionDigits: 2 })}`, "text-emerald-400"],
              ["Total PnL", `${(portfolio.total_pnl||0) >= 0 ? '+' : ''}$${(portfolio.total_pnl||0).toLocaleString('en-US',{minimumFractionDigits:2})}`, (portfolio.total_pnl||0) >= 0 ? "text-emerald-400" : "text-rose-400"],
              ["ROI", `${(portfolio.roi_pct||0) >= 0 ? '+' : ''}${portfolio.roi_pct||0}%`, (portfolio.roi_pct||0) >= 0 ? "text-emerald-400" : "text-rose-400"],
              ["Win Rate", `${portfolio.win_rate||0}%`, "text-blue-400"],
              ["Total Trades", portfolio.total_trades||0, "text-gray-300"],
            ].map(([label, val, color]) => (
              <div key={label} className="flex justify-between">
                <span className="text-[10px] text-gray-500">{label}</span>
                <span className={`text-[10px] font-black font-mono ${color}`}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [view, setView]                       = useState("dashboard");
  const [tradeSide, setTradeSide]             = useState("buy");
  const [orderType, setOrderType]             = useState("market");
  const [selectedSymbol, setSelectedSymbol]   = useState("BTCUSDT");
  const [quantityStr, setQuantityStr]         = useState("1.0");
  const [isMarketOpen, setIsMarketOpen]       = useState(false);
  const [candleInterval, setCandleInterval]   = useState("60");
  const [marketCategory, setMarketCategory]   = useState("Crypto");

  const [portfolio, setPortfolio] = useState({
    current_balance: 100000.0, initial_balance: 100000.0,
    total_pnl: 0, roi_pct: 0, win_rate: 0, total_trades: 0, status: "profitable"
  });
  const [trades, setTrades]             = useState([]);
  const [liveInstruments, setLiveInstruments] = useState([]);
  const [analysis, setAnalysis]         = useState(null);
  const [isAnalysing, setIsAnalysing]   = useState(false);
  const [isExecuting, setIsExecuting]   = useState(false);
  const [tpPrice, setTpPrice]           = useState("");
  const [slPrice, setSlPrice]           = useState("");
  const [livePrice, setLivePrice]       = useState(0);

  useEffect(() => {
    const STOCK_SYMS = [
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
    const fetchPrice = async () => {
      // Stocks → Alpaca endpoint
      if (STOCK_SYMS.includes(selectedSymbol.toUpperCase())) {
        try {
          const res = await axios.get(`${API_BASE}/api/stock/price`, { params: { symbol: selectedSymbol } });
          if (res.data?.price) setLivePrice(res.data.price);
        } catch (_) {}
        return;
      }
      // Crypto → check live instruments first, then /api/price
      const fromFeed = liveInstruments.find(i =>
        (i.pair?.replace('/', '') === selectedSymbol) || (i.symbol === selectedSymbol)
      );
      if (fromFeed) {
        const p = parseFloat(fromFeed.price?.replace(/,/g, '') || "0");
        if (p > 0) { setLivePrice(p); return; }
      }
      try {
        const res = await axios.get(`${API_BASE}/api/price`, { params: { symbol: selectedSymbol } });
        if (res.data?.price) setLivePrice(res.data.price);
      } catch (_) {}
    };
    fetchPrice();
  }, [selectedSymbol, liveInstruments]);

  const fetchData = async () => {
    try {
      const portRes = await axios.get(`${API_BASE}/api/portfolio/`);
      if (portRes.data) {
        const data = Array.isArray(portRes.data) ? portRes.data[0] : portRes.data;
        if (data) {
          if (data.current_balance !== undefined) setPortfolio(data);
          else if (data.balance !== undefined) setPortfolio({ ...data, current_balance: data.balance });
        }
      }
      const tradeRes = await axios.get(`${API_BASE}/api/trades/`);
      if (tradeRes.data) setTrades(tradeRes.data);
      const instRes = await axios.get(`${API_BASE}/api/instruments`);
      if (instRes.data) setLiveInstruments(instRes.data);
    } catch (err) { console.error("Backend offline", err); }
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    setAnalysis(null); setTpPrice(""); setSlPrice("");
  }, [selectedSymbol, candleInterval]);

  const activeInstrument = liveInstruments.find(i =>
    (i.pair?.replace('/', '') === selectedSymbol) || (i.symbol === selectedSymbol)
  );

  const handleAnalyse = async () => {
    setIsAnalysing(true); setAnalysis(null);
    try {
      const res = await axios.get(`${API_BASE}/api/analyse`, {
        params: { symbol: selectedSymbol, interval: candleInterval }
      });
      const sig = res.data;
      setAnalysis(sig);
      if (sig.current_price > 0) {
        if (sig.suggested_tp_pct) setTpPrice((sig.current_price * (1 + sig.suggested_tp_pct / 100)).toFixed(2));
        if (sig.suggested_sl_pct) setSlPrice((sig.current_price * (1 - sig.suggested_sl_pct / 100)).toFixed(2));
      }
    } catch (e) {
      alert("❌ Analysis failed. Check your backend is running.");
    } finally {
      setIsAnalysing(false);
    }
  };

  const handleExecuteTrade = async (side) => {
    setIsExecuting(true);

    // Always use the freshest available price as entry
    const currentPrice = livePrice > 0 ? livePrice : (analysis?.current_price || 0);
    const qty          = parseFloat(quantityStr) || 1.0;
    const notional     = parseFloat((currentPrice * qty).toFixed(2));

    if (currentPrice <= 0) {
      alert("❌ Cannot execute: live price not available yet. Wait a moment and retry.");
      setIsExecuting(false); return;
    }
    if (notional > portfolio.current_balance) {
      alert(`❌ Insufficient balance.\nOrder: $${notional.toLocaleString('en-US',{minimumFractionDigits:2})}\nAvailable: $${portfolio.current_balance.toLocaleString('en-US',{minimumFractionDigits:2})}`);
      setIsExecuting(false); return;
    }

    // TP/SL logic:
    // 1. If user has typed their own value → use it as-is (respect manual input)
    // 2. If field is empty (user cleared it or no analysis) → calculate from analysis % against live price
    // 3. Final sanity clamp — if the resulting value would fail backend validation, nudge it to be valid
    const userTypedTp = tpPrice !== "" && !isNaN(parseFloat(tpPrice));
    const userTypedSl = slPrice !== "" && !isNaN(parseFloat(slPrice));

    let finalTp = userTypedTp ? parseFloat(tpPrice) : null;
    let finalSl = userTypedSl ? parseFloat(slPrice) : null;

    // Auto-calculate only if the field is empty and analysis has percentages
    if (!userTypedTp && analysis?.suggested_tp_pct && currentPrice > 0) {
      finalTp = parseFloat((
        side === 'buy'
          ? currentPrice * (1 + analysis.suggested_tp_pct / 100)
          : currentPrice * (1 - analysis.suggested_tp_pct / 100)
      ).toFixed(2));
    }
    if (!userTypedSl && analysis?.suggested_sl_pct && currentPrice > 0) {
      finalSl = parseFloat((
        side === 'buy'
          ? currentPrice * (1 - analysis.suggested_sl_pct / 100)
          : currentPrice * (1 + analysis.suggested_sl_pct / 100)
      ).toFixed(2));
    }

    // Sanity clamp — catch stale values that would fail backend TP/SL validation
    if (finalTp && side === 'buy'  && finalTp <= currentPrice) finalTp = parseFloat((currentPrice * 1.02).toFixed(2));
    if (finalSl && side === 'buy'  && finalSl >= currentPrice) finalSl = parseFloat((currentPrice * 0.99).toFixed(2));
    if (finalTp && side === 'sell' && finalTp >= currentPrice) finalTp = parseFloat((currentPrice * 0.98).toFixed(2));
    if (finalSl && side === 'sell' && finalSl <= currentPrice) finalSl = parseFloat((currentPrice * 1.01).toFixed(2));

    try {
      const res = await axios.post(`${API_BASE}/api/trades/`, {
        symbol:         selectedSymbol,
        side,
        quantity:       qty,
        entry_price:    currentPrice,
        take_profit:    finalTp,
        stop_loss:      finalSl,
        notional,
        strategy:       "Hybrid_AI_MC",
        reason:         analysis?.reason        || "Manual order",
        ai_confidence:  analysis?.confidence    || null,
        mc_probability: analysis?.mc_probability || null,
      });

      if (notional > 0) {
        const newBalance = parseFloat((portfolio.current_balance - notional).toFixed(2));
        const patchRes   = await axios.patch(`${API_BASE}/api/portfolio/`, { balance: newBalance });
        if (patchRes.data) setPortfolio(patchRes.data);
      }

      // Update displayed TP/SL to the recalculated values
      if (finalTp) setTpPrice(finalTp.toFixed(2));
      if (finalSl) setSlPrice(finalSl.toFixed(2));

      alert(
        `✅ ${side.toUpperCase()} ${selectedSymbol}\n` +
        `Entry: $${currentPrice.toLocaleString('en-US',{minimumFractionDigits:2})} × ${qty} units\n` +
        `Notional: $${notional.toLocaleString('en-US',{minimumFractionDigits:2})}\n` +
        `TP: $${finalTp?.toLocaleString() || '—'}  |  SL: $${finalSl?.toLocaleString() || '—'}\n` +
        `TX-${res.data?.id}`
      );

      setAnalysis(null); setTpPrice(""); setSlPrice("");
      fetchData();

    } catch (err) {
      // Show the actual backend error message so we know exactly what failed
      const backendMsg = err?.response?.data?.detail || err?.message || "Unknown error";
      alert(`❌ Trade Failed\n\nReason: ${backendMsg}\n\nEntry: $${currentPrice} | TP: $${finalTp} | SL: $${finalSl}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const aiSentiment = analysis
    ? { pct: Math.round(analysis.confidence * 100), label: analysis.action === 'buy' ? 'BULLISH' : analysis.action === 'sell' ? 'BEARISH' : 'NEUTRAL' }
    : { pct: 0, label: 'NO SCAN' };

  // Full symbol list for market modal, searchable
  const [marketSearch, setMarketSearch] = useState("");
  const filteredMarket = MARKET_DATA[marketCategory]?.filter(s =>
    s.toLowerCase().includes(marketSearch.toLowerCase())
  ) || [];

  return (
    <div className="flex min-h-screen bg-[#0b0e14] text-white font-sans">
      <div className="flex-1 p-4 md:p-8 overflow-x-hidden">
        <div className="max-w-[1400px] mx-auto">

          {/* ── Header ── */}
          <header className="flex justify-between items-center mb-10">
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-black italic tracking-tighter uppercase text-emerald-500">AutoTrader<span className="text-white">Dash</span></h1>
              <nav className="hidden md:flex gap-8 text-[11px] font-black uppercase tracking-widest text-gray-500">
                <button onClick={() => setView('dashboard')} className={view === 'dashboard' ? 'text-emerald-400 border-b-2 border-emerald-500 pb-1' : 'hover:text-white transition-colors'}>Dashboard</button>
                <button onClick={() => setView('ai')} className={view === 'ai' ? 'text-blue-400 border-b-2 border-blue-500 pb-1' : 'hover:text-white transition-colors'}>AI Hub</button>
                <button onClick={() => setIsMarketOpen(true)} className="hover:text-white transition-colors">Markets</button>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-[10px] font-black text-gray-500">UNILAG_ADMIN • NET LIQ:</p>
                <p className="text-xs font-bold text-emerald-400">${portfolio.current_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}</p>
                <p className={`text-[9px] font-mono ${portfolio.total_pnl >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                  {portfolio.total_pnl >= 0 ? '+' : ''}${portfolio.total_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })} PnL ({portfolio.roi_pct >= 0 ? '+' : ''}{portfolio.roi_pct}%)
                </p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-blue-600"></div>
            </div>
          </header>

          {view === "dashboard" ? (
            <div className="space-y-8 animate-in fade-in duration-500">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* Chart Panel */}
                <div className="lg:col-span-8 bg-gray-800/20 border border-gray-700/50 rounded-[2.5rem] p-8 relative min-h-[500px]">
                  <div className="flex justify-between items-start mb-8">
                    <div>
                      <div className="flex items-baseline gap-4">
                        <h2 className="text-4xl font-black tracking-tighter uppercase">{selectedSymbol}</h2>
                        <span className="text-2xl font-mono text-white">
                          {livePrice > 0 ? `$${livePrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : "---"}
                        </span>
                      </div>
                      <p className="text-[10px] font-black text-emerald-500 flex items-center gap-2 mt-2">
                        <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
                        {activeInstrument ? `${activeInstrument.change} LAST 24H` : "LIVE PRICE"}
                      </p>
                    </div>
                    <div className="bg-gray-900/80 border border-emerald-500/20 backdrop-blur-xl p-5 rounded-3xl flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-full border-4 flex items-center justify-center ${aiSentiment.label === 'BULLISH' ? 'border-emerald-500' : aiSentiment.label === 'BEARISH' ? 'border-rose-500' : 'border-amber-500'}`}>
                        <span className="text-[10px] font-black">{aiSentiment.pct}%</span>
                      </div>
                      <div>
                        <p className="text-[9px] font-black text-emerald-500 uppercase">AI Sentiment</p>
                        <h4 className={`text-lg font-black leading-none ${aiSentiment.label === 'BULLISH' ? 'text-emerald-400' : aiSentiment.label === 'BEARISH' ? 'text-rose-400' : 'text-amber-400'}`}>{aiSentiment.label}</h4>
                      </div>
                    </div>
                  </div>
                  <div className="h-[350px] w-full bg-gray-900/40 rounded-3xl border border-gray-800 overflow-hidden">
                    <LiveChart key={selectedSymbol} symbol={selectedSymbol} side={tradeSide} />
                  </div>
                </div>

                {/* Order Panel */}
                <div className="lg:col-span-4 bg-gray-800/20 border border-gray-700/50 rounded-[2.5rem] p-8 shadow-2xl flex flex-col">
                  <div className="flex bg-gray-900 rounded-2xl p-1 mb-6">
                    <button onClick={() => setTradeSide('buy')} className={`flex-1 py-3 rounded-xl text-xs font-black transition-all ${tradeSide === 'buy' ? 'bg-emerald-600 text-white' : 'text-gray-500'}`}>BUY</button>
                    <button onClick={() => setTradeSide('sell')} className={`flex-1 py-3 rounded-xl text-xs font-black transition-all ${tradeSide === 'sell' ? 'bg-rose-600 text-white' : 'text-gray-500'}`}>SELL</button>
                  </div>
                  <div className="flex border-b border-gray-800 mb-6">
                    {['market', 'limit', 'stop', 'oco'].map(t => (
                      <button key={t} onClick={() => setOrderType(t)} className={`flex-1 pb-3 text-[10px] font-black uppercase tracking-widest transition-all ${orderType === t ? "text-emerald-400 border-b-2 border-emerald-400" : "text-gray-600"}`}>
                        {t}
                      </button>
                    ))}
                  </div>
                  <div className="space-y-4 flex-1">
                    {/* Symbol selector */}
                    <div>
                      <label className="text-[9px] text-gray-600 font-black uppercase">Instrument</label>
                      <button onClick={() => setIsMarketOpen(true)}
                        className="w-full mt-1 bg-gray-950 border border-gray-800 p-4 rounded-2xl text-sm font-black text-left flex justify-between items-center hover:border-gray-600 transition-colors">
                        <span className="text-emerald-400">{selectedSymbol}</span>
                        <span className="text-gray-600 text-xs">▼</span>
                      </button>
                    </div>
                    {/* Execution price */}
                    <div>
                      <label className="text-[9px] text-gray-600 font-black uppercase">Execution Price</label>
                      <input type="text"
                        value={orderType === 'market' ? (livePrice > 0 ? `$${livePrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'Fetching...') : ''}
                        placeholder={orderType === 'market' ? 'Fetching...' : '0.00'}
                        disabled={orderType === 'market'}
                        readOnly={orderType === 'market'}
                        className="w-full bg-gray-950 border border-gray-800 p-4 rounded-2xl text-sm font-mono mt-1 text-emerald-400" />
                    </div>
                    {/* Quantity */}
                    <div>
                      <label className="text-[9px] text-gray-600 font-black uppercase">Quantity</label>
                      <input type="text" value={quantityStr} onChange={(e) => setQuantityStr(e.target.value)} placeholder="1.0"
                        className="w-full bg-gray-950 border border-gray-800 p-4 rounded-2xl text-sm font-mono mt-1" />
                      {livePrice > 0 && parseFloat(quantityStr) > 0 && (
                        <p className="text-[9px] text-gray-500 font-mono mt-1">
                          ≈ ${(livePrice * (parseFloat(quantityStr) || 0)).toLocaleString('en-US', { minimumFractionDigits: 2 })} notional
                          {' '}· bal: ${portfolio.current_balance.toLocaleString('en-US', { minimumFractionDigits: 0 })}
                        </p>
                      )}
                    </div>
                    {/* TP / SL */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-[9px] text-gray-600 font-black uppercase">TP Price</label>
                        <input type="text" value={tpPrice} onChange={(e) => setTpPrice(e.target.value)} placeholder="Auto from AI"
                          className={`w-full bg-emerald-500/5 border p-4 rounded-2xl text-xs font-mono text-emerald-400 mt-1 ${
                            tpPrice && livePrice > 0 && (
                              (tradeSide === 'buy'  && parseFloat(tpPrice) <= livePrice) ||
                              (tradeSide === 'sell' && parseFloat(tpPrice) >= livePrice)
                            ) ? 'border-rose-500' : 'border-emerald-500/20'
                          }`} />
                      </div>
                      <div>
                        <label className="text-[9px] text-gray-600 font-black uppercase">SL Price</label>
                        <input type="text" value={slPrice} onChange={(e) => setSlPrice(e.target.value)} placeholder="Auto from AI"
                          className={`w-full bg-rose-500/5 border p-4 rounded-2xl text-xs font-mono text-rose-400 mt-1 ${
                            slPrice && livePrice > 0 && (
                              (tradeSide === 'buy'  && parseFloat(slPrice) >= livePrice) ||
                              (tradeSide === 'sell' && parseFloat(slPrice) <= livePrice)
                            ) ? 'border-rose-500 border-2' : 'border-rose-500/20'
                          }`} />
                      </div>
                    </div>
                    {/* Candle interval */}
                    <div>
                      <label className="text-[9px] text-gray-600 font-black uppercase">Candle Interval</label>
                      <div className="flex gap-1 mt-2">
                        {INTERVALS.map(({ label, value }) => (
                          <button key={value} onClick={() => setCandleInterval(value)}
                            className={`flex-1 py-2 rounded-xl text-[10px] font-black transition-all border ${
                              candleInterval === value
                                ? "bg-blue-600 border-blue-500 text-white"
                                : "bg-gray-900 border-gray-800 text-gray-500 hover:text-gray-300 hover:border-gray-600"
                            }`}>
                            {label}
                          </button>
                        ))}
                      </div>
                      <p className="text-[9px] text-gray-600 mt-1">{INTERVAL_HINTS[candleInterval]}</p>
                    </div>
                    {/* Analyse button */}
                    {!analysis && (
                      <button onClick={handleAnalyse} disabled={isAnalysing}
                        className="w-full py-5 rounded-2xl font-black uppercase text-xs tracking-widest transition-all mt-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed">
                        {isAnalysing ? (
                          <span className="flex items-center justify-center gap-2">
                            <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                            Analysing...
                          </span>
                        ) : `🔍 Analyse ${selectedSymbol}`}
                      </button>
                    )}
                    <AnalysisCard
                      analysis={analysis}
                      onConfirm={handleExecuteTrade}
                      onDismiss={() => { setAnalysis(null); setTpPrice(""); setSlPrice(""); }}
                      isExecuting={isExecuting}
                    />
                    {analysis && (
                      <button onClick={handleAnalyse} disabled={isAnalysing}
                        className="w-full py-3 rounded-2xl font-black uppercase text-[10px] tracking-widest transition-all bg-gray-800 hover:bg-gray-700 text-gray-400 disabled:opacity-50">
                        {isAnalysing ? 'Re-analysing...' : '↺ Re-analyse'}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <BottomDataPanel trades={trades} instruments={liveInstruments} onCloseTrade={fetchData} />
            </div>
          ) : (
            <AiHubView
              symbols={MARKET_DATA.Crypto}
              candleInterval={candleInterval}
              portfolio={portfolio}
              onExecute={handleExecuteTrade}
              isExecuting={isExecuting}
              onSetAnalysis={setAnalysis}
              onSetTpPrice={setTpPrice}
              onSetSlPrice={setSlPrice}
              onSetSelectedSymbol={setSelectedSymbol}
              onSetTradeSide={setTradeSide}
              onSetView={setView}
            />
          )}
        </div>
      </div>
      <PriceSidebar />

      {/* Market selector modal — full expanded with search */}
      {isMarketOpen && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-2xl flex items-center justify-center z-50 p-6">
          <div className="bg-gray-900 border border-gray-800 w-full max-w-5xl rounded-[3rem] p-12 relative shadow-2xl max-h-[85vh] flex flex-col">
            <button onClick={() => setIsMarketOpen(false)} className="absolute top-10 right-10 text-gray-500 hover:text-white text-sm font-black">✕ CLOSE</button>
            <h2 className="text-4xl font-black italic tracking-tighter mb-6 text-emerald-500 uppercase">Select Instrument</h2>

            {/* Category tabs */}
            <div className="flex gap-4 mb-6">
              {Object.keys(MARKET_DATA).map(cat => (
                <button key={cat} onClick={() => setMarketCategory(cat)}
                  className={`px-6 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border ${
                    marketCategory === cat ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400' : 'border-gray-800 text-gray-500 hover:text-gray-300'
                  }`}>
                  {cat} <span className="text-gray-600 ml-1">({MARKET_DATA[cat].length})</span>
                </button>
              ))}
            </div>

            {/* Search */}
            <input
              type="text"
              value={marketSearch}
              onChange={e => setMarketSearch(e.target.value)}
              placeholder={`Search ${marketCategory}...`}
              className="w-full bg-gray-950 border border-gray-800 px-5 py-3 rounded-2xl text-sm font-mono mb-6 focus:outline-none focus:border-gray-600"
            />

            {/* Symbol grid */}
            <div className="overflow-y-auto flex-1">
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {filteredMarket.map(symbol => (
                  <button key={symbol}
                    onClick={() => { setSelectedSymbol(symbol); setIsMarketOpen(false); setMarketSearch(""); }}
                    className={`p-3 rounded-xl text-sm font-bold text-left transition-all border ${
                      selectedSymbol === symbol
                        ? 'border-emerald-500/50 bg-emerald-500/5 text-emerald-400'
                        : 'border-gray-800 hover:bg-gray-800 text-gray-400 hover:text-white'
                    }`}>
                    {symbol.replace('USDT', '')}
                    {marketCategory === 'Crypto' && <span className="text-gray-600 text-[10px]">/USDT</span>}
                  </button>
                ))}
              </div>
              {filteredMarket.length === 0 && (
                <p className="text-center text-gray-600 py-10 font-mono">No symbols match "{marketSearch}"</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}