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

def get_real_price():
    try:
        # Vrai prix temps réel Binance, pas photo
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT", timeout=5)
        return float(r.json()["price"])
    except: return None

def get_candles_binance():
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=100"
        r = requests.get(url, timeout=10)
        data = r.json()
        if not isinstance(data, list): return []
        return [{"open":float(k[1]), "high":float(k[2]), "low":float(k[3]), "close":float(k[4])} for k in data]
    except: return []

def get_candles_yfinance():
    for symbol in ["XAUUSD=X", "GC=F"]:
        try:
            df = yf.download(symbol, period="2d", interval="5m", auto_adjust=True, progress=False, threads=False)
            if df is None or df.empty or len(df) < 10: continue
            df = df.reset_index()
            return [{"open":float(r["Open"]), "high":float(r["High"]), "low":float(r["Low"]), "close":float(r["Close"])} for _, r in df.iterrows()]
        except: continue
    return []

def get_candles():
    # Priorité Binance temps réel
    c = get_candles_binance()
    if len(c) >= 10: return c
    c = get_candles_yfinance()
    return c

def find_swings(candles):
    highs, lows = [], []
    try:
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
        if len(candles) < 10: return None
        highs, lows = find_swings(candles)
        if not highs or not lows: return None
        
        last = candles[-1]
        prev = candles[-2]
        real_price = get_real_price() or last["close"]

        # Check sur 10 dernières bougies = temps réel, pas 20
        recent_lows = [l for l in lows if l[0] >= len(candles)-10]
        recent_highs = [h for h in highs if h[0] >= len(candles)-10]
        if not recent_lows or not recent_highs: return None

        swing_low = min([l[1] for l in recent_lows])
        swing_high = max([candles[h[0]]["high"] for h in recent_highs])
        diff = swing_high - swing_low
        if diff <= 0: return None

        # Zone calculée sur vrai prix live
        zone_bottom_sell = swing_low + diff*0.618
        zone_top_sell = swing_low + diff*0.786
        zone_bottom_buy = swing_high - diff*0.786
        zone_top_buy = swing_high - diff*0.618

        # SELL BREAK avec vrai prix
        if real_price < swing_low:
            entry = (zone_top_sell+zone_bottom_sell)/2
            sl = zone_top_sell + 1.0
            tp1 = entry - (sl - entry)
            tp2 = entry - (sl - entry)*4
            return {"type":"SELL","signal":"BREAK","price":real_price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        if zone_bottom_sell <= real_price <= zone_top_sell and not (zone_bottom_sell <= prev["close"] <= zone_top_sell):
            entry = real_price
            sl = zone_top_sell + 1.0
            tp1 = entry - (sl - entry)
            tp2 = entry - (sl - entry)*4
            return {"type":"SELL","signal":"ENTRY","price":real_price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}

        # BUY BREAK avec vrai prix - comme ton 4000.030 à 07:46
        if real_price > swing_high:
            entry = (zone_top_buy+zone_bottom_buy)/2
            sl = zone_bottom_buy - 1.0
            tp1 = entry + (entry - sl)
            tp2 = entry + (entry - sl)*4
            return {"type":"BUY","signal":"BREAK","price":real_price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        if zone_bottom_buy <= real_price <= zone_top_buy and not (zone_bottom_buy <= prev["close"] <= zone_top_buy):
            entry = real_price
            sl = zone_bottom_buy - 1.0
            tp1 = entry + (entry - sl)
            tp2 = entry + (entry - sl)*4
            return {"type":"BUY","signal":"ENTRY","price":real_price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
                
    except: return None
    return None

def format_msg(s):
    expire = (datetime.now() + timedelta(minutes=30)).strftime("%H:%M")
    limit_type = "SELL LIMIT" if s["type"]=="SELL" else "BUY LIMIT"
    emoji="🔴" if s["type"]=="SELL" else "🟢"
    if s["signal"]=="BREAK":
        return f"""{emoji} *GOLD {s['type']} - {s['signal']} - {limit_type}*

*Break (Prix Réel):* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry ({limit_type}):* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {expire}"""
    else:
        return f"""🎯 *ENTRY - GOLD {s['type']} - {limit_type}*

*Prix Réel:* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {expire}"""
