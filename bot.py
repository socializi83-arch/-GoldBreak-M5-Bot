import yfinance as yf, os, requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

def send_telegram(msg):
    try:
        if not TELEGRAM_TOKEN or not CHAT_ID: return
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_candles():
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True, progress=False)
    if df.empty: return []
    df = df.reset_index()
    return [{"open":float(r["Open"]), "high":float(r["High"]), "low":float(r["Low"]), "close":float(r["Close"])} for _, r in df.iterrows()]

def find_swings(candles):
    # Logique pivot comme FibAlgo : swing high = plus haut que 5 bougies avant/après
    highs, lows = [], []
    for i in range(5, len(candles)-5):
        h = candles[i]["high"]
        l = candles[i]["low"]
        if all(h > candles[j]["high"] for j in range(i-5, i)) and all(h > candles[j]["high"] for j in range(i+1, i+6)):
            highs.append((i, h))
        if all(l < candles[j]["low"] for j in range(i-5, i)) and all(l < candles[j]["low"] for j in range(i+1, i+6)):
            lows.append((i, l))
    return highs, lows

def detect():
    candles = get_candles()
    if len(candles) < 70: return None
    highs, lows = find_swings(candles)
    if not highs or not lows: return None

    # Dernier swing haut / bas
    last_high_idx, last_high = highs[-1]
    last_low_idx, last_low = lows[-1]

    # On prend le couple le plus récent
    if last_high_idx > last_low_idx:
        # Tendance baissière, on a fait un haut puis un bas
        swing_high = last_high
        swing_low = candles[last_low_idx]["low"]
        # Golden Zone 0.618-0.786
        diff = swing_high - swing_low
        zone_top = swing_low + diff * 0.786
        zone_bottom = swing_low + diff * 0.618
        # Break = clôture sous le swing low
        last = candles[-1]
        if last["close"] < swing_low:
            entry = (zone_top + zone_bottom)/2
            sl = zone_top + 1.0
            return {"type":"BUY", "break_type":"BREAK", "price":last["close"], "zone_bottom":zone_bottom, "zone_top":zone_top, "entry":entry, "sl":sl, "tp1":entry+(entry-sl)*-1, "tp2":entry+(entry-sl)*-2}
    else:
        swing_low = last_low
        swing_high = candles[last_high_idx]["high"]
        diff = swing_high - swing_low
        zone_top = swing_high - diff * 0.618
        zone_bottom = swing_high - diff * 0.786
        last = candles[-1]
        if last["close"] > swing_high:
            entry = (zone_top + zone_bottom)/2
            sl = zone_bottom - 1.0
            return {"type":"SELL", "break_type":"BREAK", "price":last["close"], "zone_bottom":zone_bottom, "zone_top":zone_top, "entry":entry, "sl":sl, "tp1":entry-(sl-entry), "tp2":entry-(sl-entry)*2}
    return None

def format_msg(s):
    emoji = "🟢" if s["type"]=="BUY" else "🔴"
    return f"""{emoji} *GOLD {s['type']} - M5 | {s['break_type']} - FIBALGO CLONE*

*Break:* {s['price']:.2f}
*Golden Zone 0.618-0.786:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1 (1:1):* {s['tp1']:.2f}
*TP2 (1:2):* {s['tp2']:.2f}

_Identique FibAlgo - Zigzag + Fibonacci_"""
