from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 - Vrai Spot - OK"

@app.route("/debug")
def debug():
    try:
        import requests, os, traceback, sys
        # Test 1: Vrai Spot direct sans passer par bot.py
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=5, headers={"User-Agent":"Mozilla/5.0"})
            price = r.json().get("price", 0)
        except Exception as e1:
            price = f"gold-api error {e1}"

        # Test 2: Essaie d'importer bot.py
        try:
            import bot
            candles = bot.get_candles()
            real = bot.get_real_spot()
            highs, lows = bot.find_swings(candles)
            info_bot = f"bot.py OK candles={len(candles)} real={real} highs={len(highs)} lows={len(lows)}"
        except Exception as e2:
            import traceback
            info_bot = f"bot.py CRASH: {e2}<br><pre>{traceback.format_exc()}</pre>"

        return f"DEBUG LIVE: price_direct={price}<br>{info_bot}", 200
    except Exception as e:
        import traceback
        return f"CRASH GLOBAL: {e}<br><pre>{traceback.format_exc()}</pre>", 200

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
        return "Pas de signal mais BOT OK - prix hors zone comme 4004.990", 200
    except Exception as e:
        import traceback
        return f"RUN CRASH: {e}<br>{traceback.format_exc()}", 200

# Plus de thread au démarrage - c'est le thread qui te faisait Internal Server Error à 12:21 et 12:31
