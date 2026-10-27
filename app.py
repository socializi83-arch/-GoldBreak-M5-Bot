from flask import Flask
import os, requests, threading, time, traceback
app = Flask(__name__)

@app.route("/")
def home(): return "GoldBreak M5 - Vrai Spot 11:58 Fix - OK"

@app.route("/test")
def test():
    try:
        token=os.getenv("TELEGRAM_TOKEN",""); chat=os.getenv("CHAT_ID","") or os.getenv("TELEGRAM_CHAT_ID","")
        url=f"https://api.telegram.org/bot{token}/sendMessage"
        r=requests.post(url, json={"chat_id":chat,"text":"✅ TEST 11:58 OK"}, timeout=15)
        return f"TELEGRAM: {r.text}"
    except Exception as e: return f"ERREUR: {e}",500

@app.route("/debug")
def debug():
    try:
        import bot
        c=bot.get_candles()
        if not c: return "DEBUG: vide"
        h,l=bot.find_swings(c)
        last=c[-1]; real=bot.get_real_spot()
        return f"DEBUG: candles={len(c)} last={last['close']:.2f} real_spot={real:.2f} highs={len(h)} lows={len(l)} OK" if real else f"DEBUG: candles={len(c)} last={last['close']:.2f} highs={len(h)} lows={len(l)} OK"
    except Exception as e: return f"DEBUG ERREUR: {e}<br>{traceback.format_exc()}",500

@app.route("/run")
def run_now():
    try:
        import bot; s=bot.detect()
        if s: bot.send_telegram(bot.format_msg(s)); return f"SIGNAL {s['signal']} {s['type']} {s['price']:.2f} ENVOYE"
        return "Pas de signal - voir /debug"
    except Exception as e: return f"Erreur run: {e}<br>{traceback.format_exc()}",500

def loop():
    while True:
        try:
            import bot; s=bot.detect()
            if s: bot.send_telegram(bot.format_msg(s))
        except: pass
        time.sleep(60)
threading.Thread(target=loop, daemon=True).start()
