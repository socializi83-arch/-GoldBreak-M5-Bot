from flask import Flask
import os, requests, threading, time, traceback

app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 - FibAlgo Vrai Spot - OK"

@app.route("/test")
def test():
    try:
        token = os.getenv("TELEGRAM_TOKEN","")
        chat = os.getenv("CHAT_ID","") or os.getenv("TELEGRAM_CHAT_ID","")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id":chat,"text":"✅ TEST Vrai Spot OK"}, timeout=15)
        return f"TELEGRAM: {r.text}"
    except Exception as e:
        return f"ERREUR: {e}", 500

@app.route("/debug")
def debug():
    try:
        import bot
        # Essaie tous les noms possibles
        candles = []
        if hasattr(bot, 'get_candles'):
            candles = bot.get_candles()
        elif hasattr(bot, 'get_candles_binance'):
            candles = bot.get_candles_binance()
            if not candles and hasattr(bot, 'get_candles_yf'):
                candles = bot.get_candles_yf()
        elif hasattr(bot, 'get_candles_yfinance'):
            candles = bot.get_candles_yfinance()
        
        if not candles:
            return "DEBUG: get_candles() vide - yfinance + binance vides"
        
        highs, lows = bot.find_swings(candles) if hasattr(bot, 'find_swings') else ([],[])
        last = candles[-1]
        real = bot.get_real_spot() if hasattr(bot, 'get_real_spot') else None
        real_txt = f" real_spot={real:.2f}" if real else ""
        return f"DEBUG: candles={len(candles)} last={last['close']:.2f}{real_txt} highs={len(highs)} lows={len(lows)}"
    except Exception as e:
        return f"DEBUG ERREUR: {e}<br>{traceback.format_exc()}", 500

@app.route("/run")
def run_now():
    try:
        import bot
        sig = bot.detect()
        if sig:
            bot.send_telegram(bot.format_msg(sig))
            return f"SIGNAL {sig['signal']} {sig['type']} {sig['price']:.2f} ENVOYE"
        return "Pas de signal - voir /debug"
    except Exception as e:
        return f"Erreur run: {e} {traceback.format_exc()}", 500

def loop():
    while True:
        try:
            import bot
            sig = bot.detect()
            if sig: bot.send_telegram(bot.format_msg(sig))
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
