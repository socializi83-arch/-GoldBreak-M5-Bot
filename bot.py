import os, requests
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
    return 4000.0

def get_candles():
    real = get_real_spot()
    return [{"open":real, "high":real+1.5, "low":real-1.5, "close":real} for _ in range(20)]

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
        if not highs:
            max_c = max(candles, key=lambda x: x["high"])
            highs.append((candles.index(max_c), max_c["high"]))
        if not lows:
            min_c = min(candles, key=lambda x: x["low"])
            lows.append((candles.index(min_c), min_c["low"]))
    except: pass
    return highs, lows

def detect():
    try:
        candles = get_candles()
        highs, lows = find_swings(candles)
        price = get_real_spot()
        swing_low = min([l[1] for l in lows])
        swing_high = max([h[1] for h in highs])
        diff = swing_high - swing_low
        if diff < 2: diff = 3
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
        return {"type":"BUY","signal":"BREAK","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":(zone_bottom_buy+zone_top_buy)/2,"sl":zone_bottom_buy-1.0,"tp1":price+2,"tp2":price+8}
    except: return None

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
