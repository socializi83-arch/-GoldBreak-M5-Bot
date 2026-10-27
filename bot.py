import os, requests, time
from datetime import datetime, timedelta
try:
    import yfinance as yf
except:
    yf = None

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "") or os.getenv("TELEGRAM_CHAT_ID", "")

_last_signal_time = 0
_last_zone = ""
_last_type = ""
_cached_candles = []
_cached_time = 0

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

def get_candles_real():
    global _cached_candles, _cached_time
    now = time.time()
    if _cached_candles and now - _cached_time < 300:
        return _cached_candles
    if yf:
        for sym in ["XAUUSD=X", "GC=F"]:
            try:
                df = yf.download(sym, period="2d", interval="5m", auto_adjust=True, progress=False, threads=False)
                if df is None or df.empty or len(df) < 20: continue
                df = df.reset_index()
                candles = [{"open":float(r["Open"]), "high":float(r["High"]), "low":float(r["Low"]), "close":float(r["Close"])} for _, r in df.iterrows()]
                if len(candles) >= 20:
                    _cached_candles = candles
                    _cached_time = now
                    return candles
            except: continue
    real = get_real_spot()
    if real:
        candles = [{"open":real, "high":real+1.5, "low":real-1.5, "close":real} for _ in range(20)]
        _cached_candles = candles
        _cached_time = now
        return candles
    return _cached_candles if _cached_candles else []

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
    global _last_signal_time, _last_zone, _last_type
    try:
        candles = get_candles_real()
        if len(candles) < 10: return None
        highs, lows = find_swings(candles)
        real_spot = get_real_spot()
        if not real_spot: return None
        price = real_spot
        swing_low = min([l[1] for l in lows])
        swing_high = max([h[1] for h in highs])
        diff = swing_high - swing_low
        if diff < 3: return None
        zone_bottom_sell = swing_low + diff*0.618
        zone_top_sell = swing_low + diff*0.786
        zone_bottom_buy = swing_high - diff*0.786
        zone_top_buy = swing_high - diff*0.618

        now = time.time()
        signal = None
        if zone_bottom_sell <= price <= zone_top_sell:
            entry = price
            sl = zone_top_sell + 1.8
            tp1 = entry - (sl - entry)
            tp2 = entry - (sl - entry)*2.5
            signal = {"type":"SELL","signal":"ENTRY","price":price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        elif zone_bottom_buy <= price <= zone_top_buy:
            entry = price
            sl = zone_bottom_buy - 1.8
            tp1 = entry + (entry - sl)
            tp2 = entry + (entry - sl)*2.5
            signal = {"type":"BUY","signal":"ENTRY","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        else:
            return None

        if not signal: return None
        zone_id = f"{signal['zone_bottom']:.0f}-{signal['zone_top']:.0f}"
        if zone_id == _last_zone and signal["type"] == _last_type:
            if now - _last_signal_time < 180:
                return None
        if now - _last_signal_time < 45:
            return None
        _last_signal_time = now
        _last_zone = zone_id
        _last_type = signal["type"]
        return signal
    except: return None

def format_msg(s):
    expire = (datetime.now() + timedelta(minutes=15)).strftime("%H:%M")
    real_now = get_real_spot()
    if real_now is None:
        real_now = s["price"]
    
    # FIX FINAL 21:44: 1.50$ distance garantie plaçable pour tous les prochains
    if s["type"]=="BUY":
        limit_type = "BUY STOP"
        s["entry"] = real_now + 1.50
        s["sl"] = s["entry"] - 1.8
        s["tp1"] = s["entry"] + 1.8
        s["tp2"] = s["entry"] + 4.5
    else:
        limit_type = "SELL STOP"
        s["entry"] = real_now - 1.50
        s["sl"] = s["entry"] + 1.8
        s["tp1"] = s["entry"] - 1.8
        s["tp2"] = s["entry"] - 4.5

    emoji="🔴" if s["type"]=="SELL" else "🟢"
    return f"""{emoji} *GOLD {s['type']} - {s['signal']} - {limit_type}*

*Prix Réel Spot:* {s['price']:.2f} (actuel {real_now:.2f})
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {expire}"""
