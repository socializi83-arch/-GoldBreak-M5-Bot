from flask import Flask
import os, requests, threading, time, traceback

app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 - OK - 09:09 Fix"

@app.route("/test")
def test():
    try:
        token = os.getenv("TELEGRAM_TOKEN","")
        chat = os.getenv("CHAT_ID","") or os.getenv("TELEGRAM_CHAT_ID","")
        if not token or not chat:
            return "TOKEN ou CHAT_ID vide"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id":chat,"text":"TEST OK 09:09"}, timeout=15)
        return f"TELEGRAM: {r.text}"
    except Exception as e:
        return f"ERREUR TEST: {e} {traceback.format_exc()}", 200

@app.route("/debug")
def debug():
    try:
        import bot
        candles = bot.get_candles() if hasattr(bot, 'get_candles') else []
        real = bot.get_real_spot() if hasattr(bot, 'get_real_spot') else None
        last_txt = f"{candles[-1]['close']:.2f}" if candles else "vide"
        real_txt = f" real={real:.2f}" if real else ""
        return f"DEBUG: candles={len(candles)} last={last_txt}{real_txt} OK"
    except Exception as e:
        return f"DEBUG ERREUR: {e}<br>{traceback.format_exc()}", 200

@app.route("/run")
def run_now():
    try:
        import bot
        sig = bot.detect()
        if sig:
            bot.send_telegram(bot.format_msg(sig))
            return f"SIGNAL {sig['type']} {sig['price']:.2f} ENVOYE"
        return "Pas de signal - OK"
    except Exception as e:
        return f"Erreur run: {e}<br>{traceback.format_exc()}", 200

def loop():
    while True:
        try:
            import bot
            sig = bot.detect()
            if sig:
                bot.send_telegram(bot.format_msg(sig))
        except:
            pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
