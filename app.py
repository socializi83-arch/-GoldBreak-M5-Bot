from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 - Vrai Spot - OK"

@app.route("/debug")
def debug():
    try:
        import requests
        import bot
        price_direct = 0
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=5, headers={"User-Agent":"Mozilla/5.0"})
            price_direct = r.json().get("price", 0)
        except: price_direct = 0
        candles = bot.get_candles()
        real = bot.get_real_spot()
        highs, lows = bot.find_swings(candles)
        return f"DEBUG LIVE: price_direct={price_direct} bot.py OK candles={len(candles)} real={real} highs={len(highs)} lows={len(lows)}", 200
    except Exception as e:
        import traceback
        return f"DEBUG CRASH: {e}<br><pre>{traceback.format_exc()}</pre>", 200

@app.route("/test")
def test():
    try:
        import requests, os
        token = os.getenv("TELEGRAM_TOKEN","")
        chat = os.getenv("CHAT_ID","") or os.getenv("TELEGRAM_CHAT_ID","")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id":chat,"text":"✅ TEST Vrai Spot OK"}, timeout=15)
        return f"TELEGRAM: {r.text}", 200
    except Exception as e:
        import traceback
        return f"TEST CRASH: {e}<br>{traceback.format_exc()}", 200

@app.route("/run")
def run_now():
    try:
        import bot
        sig = bot.detect()
        if sig:
            bot.send_telegram(bot.format_msg(sig))
            return f"SIGNAL {sig['type']} {sig['price']:.2f} ENVOYE", 200
        return "Pas de signal mais BOT OK", 200
    except Exception as e:
        import traceback
        return f"RUN CRASH: {e}<br>{traceback.format_exc()}", 200

def loop():
    while True:
        try:
            import bot, time
            sig = bot.detect()
            if sig: bot.send_telegram(bot.format_msg(sig))
            time.sleep(60)
        except:
            import time
            time.sleep(60)

import threading
threading.Timer(10.0, lambda: threading.Thread(target=loop, daemon=True).start()).start()
