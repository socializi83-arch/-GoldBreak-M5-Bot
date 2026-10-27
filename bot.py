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

def get_real_spot():
    for u in ["https://api.gold-api.com/price/XAU", "https://api.metals.live/v1/spot"]:
        try:
            r = requests.get(u, timeout=5, headers={"User-Agent":"Mozilla/5.0"})
            d = r.json()
            if isinstance(d, dict) and "price" in d:
                p = float(d["price"])
                if p > 1000: return p
            if isinstance(d, list):
                for item in d:
                    if item.get("metal")=="XAU":
                        return float(item.get("price",0))
        except: continue
    return None

def get_candles_yf():
    for sym in ["XAUUSD=X", "GC=F"]:
        try:
            df = yf.download(sym, period="2d", interval="5m", auto_adjust=True, progress=False, threads=False)
            if df is None or df.empty or len(df) < 10: continue
            df = df.reset_index()
            return [{"open":float(r["Open"]), "high":float(r["High"]), "low":float(r["Low"]), "close":float(r["Close"])} for _, r in df.iterrows()]
        except: continue
    return []

def get_candles():
    c = get_candles_yf()
    if len(c) >= 10: return c
    real = get_real_spot()
    if real:
        return [{"open":real, "high":real+1, "low":real-1, "close":real} for _ in range(20)]
    return []

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
        if not highs or not lows:
            min_c = min(candles, key=lambda x: x["low"])
            max_c = max(candles, key=lambda x: x["high"])
            min_idx = candles.index(min_c)
            max_idx = candles.index(max_c)
            if not highs:
                highs.append((max_idx, max_c["high"]))
            if not lows:
                lows.append((min_idx, min_c["low"]))
    except: pass
    return highs, lows

def detect():
    try:
        candles = get_candles()
        if len(candles) < 10: return None
        highs, lows = find_swings(candles)
        if not highs or not lows: return None
        real_spot = get_real_spot()
        last = candles[-1]
        price = real_spot if real_spot else last["close"]
        prev = candles[-2]
        recent_lows = [l for l in lows if l[0] >= len(candles)-5]
        recent_highs = [h for h in highs if h[0] >= len(candles)-5]
        if not recent_lows or not recent_highs: return None
        swing_low = min([l[1] for l in recent_lows])
        swing_high = max([candles[h[0]]["high"] for h in recent_highs])
        diff = swing_high - swing_low
        if diff <= 0: return None
        zone_bottom_sell = swing_low + diff*0.618
        zone_top_sell = swing_low + diff*0.786
        zone_bottom_buy = swing_high - diff*0.786
        zone_top_buy = swing_high - diff*0.618
        if zone_bottom_sell <= price <= zone_top_sell:
            entry = price
            sl = zone_top_sell + 1.0
            tp1 = entry - (sl - entry)
            tp2 = entry - (sl - entry)*4
            return {"type":"SELL","signal":"ENTRY","price":price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        if price < swing_low:
            entry = (zone_top_sell+zone_bottom_sell)/2
            sl = zone_top_sell + 1.0
            tp1 = entry - (sl - entry)
            tp2 = entry - (sl - entry)*4
            return {"type":"SELL","signal":"BREAK","price":price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        if zone_bottom_buy <= price <= zone_top_buy:
            entry = price
            sl = zone_bottom_buy - 1.0
            tp1 = entry + (entry - sl)
            tp2 = entry + (entry - sl)*4
            return {"type":"BUY","signal":"ENTRY","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        if price > swing_high:
            entry = (zone_top_buy+zone_bottom_buy)/2
            sl = zone_bottom_buy - 1.0
            tp1 = entry + (entry - sl)
            tp2 = entry + (entry - sl)*4
            return {"type":"BUY","signal":"BREAK","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
    except: return None
    return None

def format_msg(s):
    expire = (datetime.now() + timedelta(minutes=30)).strftime("%H:%M")
    limit_type = "SELL LIMIT" if s["type"]=="SELL" else "BUY LIMIT"
    emoji="🔴" if s["type"]=="SELL" else "🟢"
    if s["signal"]=="BREAK":
        return f"""{emoji} *GOLD {s['type']} - {s['signal']} - {limit_type}*

*Break (Vrai Spot):* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry ({limit_type}):* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {expire}"""
    else:
        return f"""🎯 *ENTRY - GOLD {s['type']} - {limit_type}*

*Prix Réel Spot:* {s['price']:.2f}
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {expire}"""
