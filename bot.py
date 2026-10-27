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
    try:
        r = requests.get("https://api.gold-api.com/price/XAU", timeout=5, headers={"User-Agent":"Mozilla/5.0"})
        p = float(r.json().get("price",0))
        if p > 1000: return p
    except: pass
    try:
        r = requests.get("https://api.metals.live/v1/spot", timeout=5, headers={"User-Agent":"Mozilla/5.0"})
        for it in r.json():
            if it.get("metal")=="XAU":
                return float(it.get("price",0))
    except: pass
    return None

def get_candles():
    for sym in ["XAUUSD=X", "GC=F"]:
        try:
            df = yf.download(sym, period="2d", interval="5m", auto_adjust=True, progress=False, threads=False)
            if df is None or df.empty or len(df) < 10: continue
            df = df.reset_index()
            return [{"open":float(r["Open"]), "high":float(r["High"]), "low":float(r["Low"]), "close":float(r["Close"])} for _, r in df.iterrows()]
        except: continue
    real = get_real_spot()
    if real:
        return [{"open":real, "high":real+1, "low":real-1, "close":real} for _ in range(20)]
    return []

def find_swings(c):
    h,l=[],[] 
    try:
        for i in range(1,len(c)-1):
            if c[i]["high"]>c[i-1]["high"] and c[i]["high"]>c[i+1]["high"]: h.append((i,c[i]["high"]))
            if c[i]["low"]<c[i-1]["low"] and c[i]["low"]<c[i+1]["low"]: l.append((i,c[i]["low"]))
    except: pass
    return h,l

def detect():
    try:
        candles=get_candles()
        if len(candles)<10: return None
        highs,lows=find_swings(candles)
        if not highs or not lows: return None
        real=get_real_spot()
        price=real if real else candles[-1]["close"]
        prev=candles[-2]
        recent_lows=[x for x in lows if x[0]>=len(candles)-5]
        recent_highs=[x for x in highs if x[0]>=len(candles)-5]
        if not recent_lows or not recent_highs: return None
        sw_low=min([x[1] for x in recent_lows])
        sw_high=max([candles[x[0]]["high"] for x in recent_highs])
        diff=sw_high-sw_low
        if diff<=0: return None
        zb_sell=sw_low+diff*0.618
        zt_sell=sw_low+diff*0.786
        zb_buy=sw_high-diff*0.786
        zt_buy=sw_high-diff*0.618
        # SELL d'abord comme ton 4007 à 08:23
        if zb_sell<=price<=zt_sell:
            e=price; sl=zt_sell+1.0; tp1=e-(sl-e); tp2=e-(sl-e)*4
            return {"type":"SELL","signal":"ENTRY","price":price,"zb":zb_sell,"zt":zt_sell,"e":e,"sl":sl,"tp1":tp1,"tp2":tp2}
        if price<sw_low:
            e=(zt_sell+zb_sell)/2; sl=zt_sell+1.0; tp1=e-(sl-e); tp2=e-(sl-e)*4
            return {"type":"SELL","signal":"BREAK","price":price,"zb":zb_sell,"zt":zt_sell,"e":e,"sl":sl,"tp1":tp1,"tp2":tp2}
        if zb_buy<=price<=zt_buy:
            e=price; sl=zb_buy-1.0; tp1=e+(e-sl); tp2=e+(e-sl)*4
            return {"type":"BUY","signal":"ENTRY","price":price,"zb":zb_buy,"zt":zt_buy,"e":e,"sl":sl,"tp1":tp1,"tp2":tp2}
        if price>sw_high:
            e=(zt_buy+zb_buy)/2; sl=zb_buy-1.0; tp1=e+(e-sl); tp2=e+(e-sl)*4
            return {"type":"BUY","signal":"BREAK","price":price,"zb":zb_buy,"zt":zt_buy,"e":e,"sl":sl,"tp1":tp1,"tp2":tp2}
    except: return None
    return None

def format_msg(s):
    exp=(datetime.now()+timedelta(minutes=30)).strftime("%H:%M")
    lim="SELL LIMIT" if s["type"]=="SELL" else "BUY LIMIT"
    emo="🔴" if s["type"]=="SELL" else "🟢"
    if s["signal"]=="BREAK":
        return f"""{emo} *GOLD {s['type']} - {s['signal']} - {lim}*

*Break (Vrai Spot):* {s['price']:.2f}
*Zone:* {s['zb']:.2f} - {s['zt']:.2f}
*Entry ({lim}):* {s['e']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {exp}"""
    else:
        return f"""🎯 *ENTRY - GOLD {s['type']} - {lim}*

*Prix Réel Spot:* {s['price']:.2f}
*Zone:* {s['zb']:.2f} - {s['zt']:.2f}
*Entry:* {s['e']:.2f}
*SL:* {s['sl']:.2f}
*TP1:* {s['tp1']:.2f}
*TP2:* {s['tp2']:.2f}
*Valide:* {exp}"""
