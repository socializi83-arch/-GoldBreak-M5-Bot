import os, requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ZONE_NORMAL = 1.5
ZONE_STRONG = 2.5

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("TELEGRAM non configuré")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(e)

def get_candles():
    try:
        import yfinance as yf
        df = yf.download("GC=F", period="2d", interval="5m", auto_adjust=True, progress=False)
        if df.empty: return []
        df = df.reset_index()
        candles = []
        for _, row in df.iterrows():
            candles.append({
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"])
            })
        return candles
    except Exception as e:
        print(f"Erreur yfinance: {e}")
        return []

def get_break_type(c):
    body = abs(c["close"] - c["open"])
    wick = c["high"] - c["low"]
    if wick == 0: return None
    ratio = body / wick
    if ratio > 0.85 and body > 2.0: return "STRONG"
    if ratio > 0.65: return "NORMAL"
    return None

def detect():
    candles = get_candles()
    if len(candles) < 60: return None
    last = candles[-1]
    prev = candles[-2]
    last_high = max(c["high"] for c in candles[-60:-5])
    last_low = min(c["low"] for c in candles[-60:-5])
    break_type = get_break_type(prev)
    if not break_type: return None
    zone_size = ZONE_STRONG if break_type == "STRONG" else ZONE_NORMAL
    signal = None
    if last["close"] > last_high:
        signal = {"type": "BUY", "break_type": break_type, "break_price": last["close"], "zone_bottom": prev["low"], "zone_top": prev["low"]+zone_size}
    elif last["close"] < last_low:
        signal = {"type": "SELL", "break_type": break_type, "break_price": last["close"], "zone_bottom": prev["high"]-zone_size, "zone_top": prev["high"]}
    if not signal: return None
    entry = (signal["zone_top"] + signal["zone_bottom"])/2
    buffer = 1.0 if break_type == "STRONG" else 0.6
    if signal["type"] == "BUY":
        sl = signal["zone_bottom"] - buffer
        tp1 = entry + (entry - sl)
        tp2 = entry + (entry - sl)*2
    else:
        sl = signal["zone_top"] + buffer
        tp1 = entry - (sl - entry)
        tp2 = entry - (sl - entry)*2
    signal.update({"entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "price": last["close"], "zone_size": zone_size})
    return signal

def format_msg(s):
    emoji = "🟢" if s["type"] == "BUY" else "🔴"
    label = "STRONG BREAK" if s["break_type"] == "STRONG" else "BREAK"
    return f"{emoji} *GOLD {s['type']} - M5 | {label}*\n\nBreak: {s['break_price']:.2f} ({s['break_type']})\nPrix: {s['price']:.2f}\nZone ({s['zone_size']:.1f}$): {s['zone_bottom']:.2f} - {s['zone_top']:.2f}\nEntry: {s['entry']:.2f}\nSL: {s['sl']:.2f}\nTP1: {s['tp1']:.2f}\nTP2: {s['tp2']:.2f}"
