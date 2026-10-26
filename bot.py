import yfinance as yf
import os, requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Tailles vues sur tes 4 captures
ZONE_NORMAL = 1.5  # Break normal - images 11:45 / 11:57 / 12:09
ZONE_STRONG = 2.5 # Strong Break - image 13:30 à 4022.350

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def get_candles():
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
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

def get_break_type(c):
    body = abs(c["close"] - c["open"])
    wick = c["high"] - c["low"]
    if wick == 0: return None
    ratio = body / wick
    # Logique de tes images
    if ratio > 0.85 and body > 2.0:  # Grosse bougie comme ton Strong Break 13:30
        return "STRONG"
    if ratio > 0.65: # Break normal comme tes 3 autres images
        return "NORMAL"
    return None

def detect():
    candles = get_candles()
    if len(candles) < 60: return None
    
    last = candles[-1]
    prev = candles[-2]
    last_high = max(c["high"] for c in candles[-60:-5])
    last_low = min(c["low"] for c in candles[-60:-5])
    
    break_type = get_break_type(prev)
    if not break_type:
        return None

    zone_size = ZONE_STRONG if break_type == "STRONG" else ZONE_NORMAL
    signal = None

    if last["close"] > last_high:
        signal = {
            "type": "BUY",
            "break_type": break_type,
            "break_price": last["close"],
            "zone_bottom": prev["low"],
            "zone_top": prev["low"] + zone_size
        }
    elif last["close"] < last_low:
        signal = {
            "type": "SELL",
            "break_type": break_type,
            "break_price": last["close"],
            "zone_bottom": prev["high"] - zone_size,
            "zone_top": prev["high"]
        }
    
    if not signal: return None

    entry = (signal["zone_top"] + signal["zone_bottom"]) / 2
    buffer = 1.0 if break_type == "STRONG" else 0.6
    
    if signal["type"] == "BUY":
        sl = signal["zone_bottom"] - buffer
        tp1 = entry + (entry - sl)
        tp2 = entry + (entry - sl) * 2
    else:
        sl = signal["zone_top"] + buffer
        tp1 = entry - (sl - entry)
        tp2 = entry - (sl - entry) * 2

    signal.update({
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2,
        "price": last["close"], "zone_size": zone_size
    })
    return signal

def format_msg(s):
    emoji = "🟢" if s["type"] == "BUY" else "🔴"
    label = "STRONG BREAK" if s["break_type"] == "STRONG" else "BREAK"
    return f"""{emoji} *GOLD {s['type']} - M5 | {label}*

*Break:* {s['break_price']:.2f} ({s['break_type']})
*Prix:* {s['price']:.2f}

*Zone ({s['zone_size']:.1f}$):* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1 (1:1):* {s['tp1']:.2f}
*TP2 (1:2):* {s['tp2']:.2f}

_Calqué sur tes 4 images FibAlgo_"""
