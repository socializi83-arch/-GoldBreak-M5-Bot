import yfinance as yf, os, requests
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "") or os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram(msg):
    try:
        if not TELEGRAM_TOKEN or not CHAT_ID: return
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_candles_yfinance():
    for symbol in ["XAUUSD=X", "GC=F"]:
        try:
            df = yf.download(symbol, period="2d", interval="5m", auto_adjust=True, progress=False, threads=False)
            if df is None or df.empty or len(df) < 20: continue
            df = df.reset_index()
            return [{"open":float(r["Open"]), "high":float(r["High"]), "low":float(r["Low"]), "close":float(r["Close"])} for _, r in df.iterrows()]
        except: continue
    return []

def get_candles_binance():
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=100"
        r = requests.get(url, timeout=10)
        data = r.json()
        if not isinstance(data, list) or len(data) < 20: return []
        candles = []
        for k in data:
            candles.append({"open":float(k[1]), "high":float(k[2]), "low":float(k[3]), "close":float(k[4])})
        return candles
    except: return []

def get_candles():
    c = get_candles_yfinance()
    if len(c) >= 20: return c
    c = get_candles_binance()
    if len(c) >= 20: return c
    return []

def find_swings(candles):
    highs, lows = [], []
    try:
        for i in range(2, len(candles)-2):
            h = candles[i]["high"]
            l = candles[i]["low"]
            if all(h >= candles[j]["high"] for j in range(i-2, i)) and all(h >= candles[j]["high"] for j in range(i+1, i+3)):
                highs.append((i, h))
            if all(l <= candles[j]["low"] for j in range(i-2, i)) and all(l <= candles[j]["low"] for j in range(i+1, i+3)):
                lows.append((i, l))
    except: pass
    return highs, lows

def detect():
    try:
        candles = get_candles()
        if len(candles) < 20: return None
        highs, lows = find_swings(candles)
        if not highs or not lows: return None
        last_high_idx, last_high = highs[-1]
        last_low_idx, last_low = lows[-1]
        last = candles[-1]
        prev = candles[-2]

        if last_high_idx > last_low_idx:
            swing_high = last_high
            swing_low = candles[last_low_idx]["low"]
            diff = swing_high - swing_low
            if diff <= 0: return None
            zone_bottom = swing_low + diff*0.618
            zone_top = swing_low + diff*0.786
            if last["close"] < swing_low:
                entry = (zone_top+zone_bottom)/2
                sl = zone_top + 1.0
                tp1 = entry - (sl - entry)
                tp2 = entry - (sl - entry)*4
                return {"type":"SELL","signal":"BREAK","price":last["close"],"zone_bottom":zone_bottom,"zone_top":zone_top,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
            if zone_bottom <= last["close"] <= zone_top and not (zone_bottom <= prev["close"] <= zone_top):
                entry = last["close"]
                sl = zone_top + 1.0
                tp1 = entry - (sl - entry)
                tp2 = entry - (sl - entry)*4
                return {"type":"SELL","signal":"ENTRY","price":last["close"],"zone_bottom":zone_bottom,"zone_top":zone_top,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        else:
            swing_low = last_low
            swing_high = candles[last_high_idx]["high"]
            diff = swing_high - swing_low
            if diff <= 0: return None
            zone_bottom = swing_high - diff*0.786
            zone_top = swing_high - diff*0.618
            if last["close"] > swing_high:
                entry = (zone_top+zone_bottom)/2
                sl = zone_bottom - 1.0
                tp1 = entry + (entry - sl)
                tp2 = entry + (entry - sl)*4
                return {"type":"BUY","signal":"BREAK","price":last["close"],"zone_bottom":zone_bottom,"zone_top":zone_top,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
            if zone_bottom <= last["close"] <= zone_top and not (zone_bottom <= prev["close"] <= zone_top):
                entry = last["close"]
                sl = zone_bottom - 1.0
                tp1 = entry + (entry - sl)
                tp2 = entry + (entry - sl)*4
                return {"type":"BUY","signal":"ENTRY","price":last["close"],"zone_bottom":zone_bottom,"zone_top":zone_top,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
    except: return None
