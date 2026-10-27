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
        # 1 bougie = comme FibAlgo temps réel, plus de décalage 14$ comme à 07:46
        for i in range(1, len(candles)-1):
            h = candles[i]["high"]
            l = candles[i]["low"]
            if h > candles[i-1]["high"] and h > candles[i+1]["high"]:
                highs.append((i, h))
            if l < candles[i-1]["low"] and l < candles[i+1]["low"]:
                lows.append((i, l))
    except: pass
    return highs, lows

def detect():
    try:
        candles = get_candles()
        if len(candles) < 20: return None
        highs, lows = find_swings(candles)
        if not highs or not lows: return None
        
        last = candles[-1]
        prev = candles[-2]
        
        # On check les 2 côtés en même temps comme FibAlgo qui montre Sell Zone 4010 et Buy Zone 4002 à 07:46
        # 1. SELL
        last_high_idx, last_high = highs[-1]
        last_low_idx, last_low = lows[-1]
        swing_high = last_high
        swing_low = candles[last_low_idx]["low"]
        diff = swing_high - swing_low
        if diff > 0:
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
        
        # 2. BUY - ton Buy Zone 4002 à 07:46 avec prix 4000.030
        recent_lows = [l for l in lows if l[0] >= len(candles)-20]
        recent_highs = [h for h in highs if h[0] >= len(candles)-20]
        if recent_lows and recent_highs:
            swing_low2 = min([l[1] for l in recent_lows])
            swing_high2 = max([candles[h[0]]["high"] for h in recent_highs])
            diff2 = swing_high2 - swing_low2
            if diff2 > 0:
                zone_bottom2 = swing_high2 - diff2*0.786
                zone_top2 = swing_high2 - diff2*0.618
                if last["close"] > swing_high2:
                    entry = (zone_top2+zone_bottom2)/2
                    sl = zone_bottom2 - 1.0
                    tp1 = entry + (entry - sl)
                    tp2 = entry + (entry - sl)*4
                    return {"type":"BUY","signal":"BREAK","price":last["close"],"zone_bottom":zone_bottom2,"zone_top":zone_top2,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
                if zone_bottom2 <= last["close"] <= zone_top2 and not (zone_bottom2 <= prev["close"] <= zone_top2):
                    entry = last["close"]
                    sl = zone_bottom2 - 1.0
                    tp1 = entry + (entry - sl)
                    tp2 = entry + (entry - sl)*4
                    return {"type":"BUY","signal":"ENTRY","price":last["close"],"zone_bottom":zone_bottom2,"zone_top":zone_top2,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
                
    except: return None
    return None

def format_msg(s):
    expire = (datetime.now() + timedelta(minutes=30)).strftime("%H:%M")
    limit_type = "SELL LIMIT" if s["type"]=="SELL" else "BUY LIMIT"
    emoji="🔴" if s["type"]=="SELL" else "🟢"
    if s["signal"]=="BREAK":
        return f"""{emoji} *GOLD {s['type']} - {s['signal']} - {limit_type}*

*Break:* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry ({limit_type}):* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1 (1:1):* {s['tp1']:.2f}
*TP2 (1:4):* {s['tp2']:.2f}
*Valide:* {expire}"""
    else:
        return f"""🎯 *ENTRY - GOLD {s['type']} - {limit_type}*

*Prix:* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {expire}"""
