from flask import Flask
import os, requests, threading, time, traceback

app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 - FibAlgo BREAK+ENTRY - OK"

@app.route("/test")
def test():
    try:
        token = os.getenv("TELEGRAM_TOKEN","")
        chat = os.getenv("CHAT_ID","") or os.getenv("TELEGRAM_CHAT_ID","")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id":chat,"text":"✅ TEST OK - Final 1 bougie marche !"}, timeout=15)
        return f"TELEGRAM: {r.text}"
    except Exception as e:
        return f"ERREUR: {e}", 500

@app.route("/debug")
def debug():
    try:
        from bot import get_candles, find_swings
        candles = get_candles()
        if not candles:
            return "DEBUG: get_candles() vide"
        highs, lows = find_swings(candles)
        last = candles[-1]
        return f"DEBUG: candles={len(candles)} last={last['close']:.2f} highs={len(highs)} lows={len(lows)} last_high_idx={highs[-1][0] if highs else 'none'} last_low_idx={lows[-1][0] if lows else 'none'}"
    except Exception as e:
        return f"DEBUG ERREUR: {e} {traceback.format_exc()}", 500

@app.route("/run")
def run_now():
    try:
        from bot import detect, format_msg, send_telegram
        sig = detect()
        if sig:
            send_telegram(format_msg(sig))
            return f"SIGNAL {sig['signal']} {sig['type']} {sig['price']:.2f} ENVOYE"
        return "Pas de signal - voir /debug"
    except Exception as e:
        return f"Erreur run: {e} {traceback.format_exc()}", 500

def loop():
    while True:
        try:
            from bot import detect, format_msg, send_telegram
            sig = detect()
            if sig: send_telegram(format_msg(sig))
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
