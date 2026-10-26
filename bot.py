import yfinance as yf, os, requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "") or os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram(msg):
    try:
        if not TELEGRAM_TOKEN or not CHAT_ID: return
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_candles():
    try:
        df = yf.download("XAUUSD=X", period="5d", interval="5m", auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty or len(df) < 30: return []
        df = df.reset_index()
        return [{"open":float(r["Open"]), "high":float(r["High"]), "low":float(r["Low"]), "close":float(r["Close"])} for _, r in df.iterrows()]
    except: return []

def find_swings(candles):
    highs, lows = [], []
    try:
        for i in range(3, len(candles)-3):
            h = candles[i]["high"]
            l = candles[i]["low"]
            if all(h > candles[j]["high"] for j in range(i-3, i)) and all(h > candles[j]["high"] for j in range(i+1, i+4)):
                highs.append((i, h))
            if all(l < candles[j]["low"] for j in range(i-3, i)) and all(l < candles[j]["low"] for j in range(i+1, i+4)):
                lows.append((i, l))
    except: pass
    return highs, lows

def detect():
    try:
        candles = get_candles()
        if len(candles) < 30: return None
        highs, lows = find_swings(candles)
        if not highs or not lows: return None
        last_high_idx, last_high = highs[-1]
        last_low_idx, last_low = lows[-1]
        last = candles[-1]
        prev = candles[-2] if len(candles)>=2 else last

        if last_high_idx > last_low_idx:
            swing_high = last_high
            swing_low = candles[last_low_idx]["low"]
            diff = swing_high - swing_low
            if diff <= 0: return None
            zone_bottom = swing_low + diff * 0.618
            zone_top = swing_low + diff * 0.786
            if last["close"] < swing_low:
                entry = (zone_top+zone_bottom)/2
                sl = zone_top+0.8
                tp1 = entry-(sl-entry)
                tp2 = entry-(sl-entry)*4
                return {"type":"SELL","signal":"BREAK","price":last["close"],"zone_bottom":zone_bottom,"zone_top":zone_top,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
            if zone_bottom <= last["close"] <= zone_top and not (zone_bottom <= prev["close"] <= zone_top):
                entry = last["close"]
                sl = zone_top+0.8
                tp1 = entry-(sl-entry)
                tp2 = entry-(sl-entry)*4
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
                sl = zone_bottom-0.8
                tp1 = entry+(entry-sl)
                tp2 = entry+(entry-sl)*4
                return {"type":"BUY","signal":"BREAK","price":last["close"],"zone_bottom":zone_bottom,"zone_top":zone_top,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
            if zone_bottom <= last["close"] <= zone_top and not (zone_bottom <= prev["close"] <= zone_top):
                entry = last["close"]
                sl = zone_bottom-0.8
                tp1 = entry+(entry-sl)
                tp2 = entry+(entry-sl)*4
                return {"type":"BUY","signal":"ENTRY","price":last["close"],"zone_bottom":zone_bottom,"zone_top":zone_top,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
    except: return None
    return None

def format_msg(s):
    if s["signal"]=="BREAK":
        emoji="🔴" if s["type"]=="SELL" else "🟢"
        return f"""{emoji} *GOLD {s['type']} - M5 | {s['signal']}*

*Break:* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}"""
    else:
        return f"""🎯 *ENTRY - GOLD {s['type']}*

*Prix:* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}"""
