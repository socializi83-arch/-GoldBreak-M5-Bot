import os, requests, time
from datetime import datetime, timedelta
try:
    import yfinance as yf
except:
    yf = None

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "") or os.getenv("TELEGRAM_CHAT_ID", "")

BUY_ONLY = False
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

def intersects(candle, zb, zt):
    return candle["low"] <= zt and candle["high"] >= zb

def touches_level(candle, level):
    return candle["low"] - 0.3 <= level <= candle["high"] + 0.3

def detect():
    global _last_signal_time, _last_zone, _last_type
    try:
        candles = get_candles_real()
        if len(candles) < 25: return None
        highs, lows = find_swings(candles)
        real_spot = get_real_spot()
        if not real_spot: return None
        price = real_spot

        closes = [c["close"] for c in candles[-20:]]
        sma20 = sum(closes)/len(closes)
        closes_prev = [c["close"] for c in candles[-25:-5]]
        sma20_prev = sum(closes_prev)/len(closes_prev)

        swing_low = min([l[1] for l in lows])
        swing_high = max([h[1] for h in highs])
        diff = swing_high - swing_low
        if diff < 3.0: return None

        zone_bottom_sell = swing_low + diff*0.618
        zone_top_sell = swing_low + diff*0.786
        zone_bottom_buy = swing_high - diff*0.786
        zone_top_buy = swing_high - diff*0.618

        last = candles[-1]
        prev = candles[-2]
        now = time.time()

        # STRONG BREAK détection
        strong_break_haussier = last["close"] > swing_high and prev["close"] <= swing_high
        strong_break_baissier = last["close"] < swing_low and prev["close"] >= swing_low
        recent_break_haussier = any(c["close"] > swing_high for c in candles[-3:])
        recent_break_baissier = any(c["close"] < swing_low for c in candles[-3:])

        signal = None

        # ===== STRATÉGIE A : TRAVERSÉE + Strong Break + confirmation (sûre à 90%) =====
        # Comme version 11:56 avec 4031.399902
        if intersects(last, zone_bottom_buy, zone_top_buy) and not intersects(prev, zone_bottom_buy, zone_top_buy):
            if price >= sma20 - 1.0 and last["close"] > last["open"] and sma20 > sma20_prev:
                if not (recent_break_baissier and not recent_break_haussier):
                    signal = {"type":"BUY","signal":"A-TRAVERSÉE","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy}
        if not signal and intersects(last, zone_bottom_sell, zone_top_sell) and not intersects(prev, zone_bottom_sell, zone_top_sell):
            if not BUY_ONLY and price <= sma20 + 1.0 and last["close"] < last["open"] and sma20 < sma20_prev:
                if not (recent_break_haussier and not recent_break_baissier):
                    signal = {"type":"SELL","signal":"A-TRAVERSÉE","price":price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell}
        if not signal and strong_break_haussier and last["close"] > last["open"] and sma20 > sma20_prev and not recent_break_baissier:
            signal = {"type":"BUY","signal":"A-STRONG BREAK HAUSSIER","price":price,"zone_bottom":swing_high-1,"zone_top":swing_high}
        if not signal and strong_break_baissier and last["close"] < last["open"] and sma20 < sma20_prev and not BUY_ONLY and not recent_break_haussier:
            signal = {"type":"SELL","signal":"A-STRONG BREAK BAISSIER","price":price,"zone_bottom":swing_low,"zone_top":swing_low+1}

        # ===== STRATÉGIE B : 2 bougies BAS Sell / HAUT Buy (ta stratégie exacte) - INDÉPENDANTE avec OU =====
        if not signal:
            # BUY au HAUT Buy Zone 4022-4026 sur image 10:51 prix 4026.960
            if touches_level(last, zone_top_buy) and touches_level(prev, zone_top_buy):
                signal = {"type":"BUY","signal":"B-2 BOUGIES HAUT BUY","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy}
            # SELL au BAS Sell Zone 4030-4028 et 4034-4032 sur image 14:18 prix 4027.125
            elif not BUY_ONLY and touches_level(last, zone_bottom_sell) and touches_level(prev, zone_bottom_sell):
                signal = {"type":"SELL","signal":"B-2 BOUGIES BAS SELL","price":price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell}

        if not signal: return None

        # Anti-spam 60 sec / 3 min même zone évite 15 BUY 17:36-17:53 -56.10
        zone_id = f"{signal['zone_bottom']:.0f}-{signal['zone_top']:.0f}"
        if zone_id == _last_zone and signal["type"] == _last_type:
            if now - _last_signal_time < 180:
                return None
        if now - _last_signal_time < 60:
            return None
        _last_signal_time = now
        _last_zone = zone_id
        _last_type = signal["type"]

        # Complète SL/TP
        if signal["type"]=="BUY":
            signal["entry"]=price
            signal["sl"]=signal["zone_bottom"]-3.0
            signal["tp1"]=price+3.0
            signal["tp2"]=price+7.5
        else:
            signal["entry"]=price
            signal["sl"]=signal["zone_top"]+3.0
            signal["tp1"]=price-3.0
            signal["tp2"]=price-7.5
        return signal
    except: return None

def format_msg(s):
    expire = (datetime.now() + timedelta(minutes=20)).strftime("%H:%M")
    real_now = get_real_spot()
    if real_now is None:
        real_now = s["price"]
    
    if s["type"]=="BUY":
        limit_type = "BUY STOP"
        s["entry"] = real_now + 1.50
        s["sl"] = s["entry"] - 3.0
        s["tp1"] = s["entry"] + 3.0
        s["tp2"] = s["entry"] + 7.5
        emoji="🟢"
    else:
        limit_type = "SELL STOP"
        s["entry"] = real_now - 1.50
        s["sl"] = s["entry"] + 3.0
        s["tp1"] = s["entry"] - 3.0
        s["tp2"] = s["entry"] - 7.5
        emoji="🔴"

    return f"""{emoji} *GOLD {s['type']} - {s['signal']} - {limit_type}*

*Prix Réel Spot:* {s['price']:.2f} (actuel {real_now:.2f})
*Zone:* {s['zone_bottom']:.2f} - {s['zone_top']:.2f}
*Entry:* {s['entry']:.2f}
*SL:* {s['sl']:.2f} (large 3.0$ 2 strat OU)
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {expire}"""
