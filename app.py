from flask import Flask
import os, requests, threading, time

app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 - FibAlgo BREAK + ENTRY - OK"

@app.route("/test")
def test():
    try:
        token = os.getenv("TELEGRAM_TOKEN", "")
        chat = os.getenv("CHAT_ID", "") or os.getenv("TELEGRAM_CHAT_ID", "")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat, "text": "✅ TEST OK - FibAlgo BREAK+ENTRY marche !"}, timeout=15)
        return f"REPONSE TELEGRAM: {r.text}"
    except Exception as e:
        return f"ERREUR: {e}", 500

@app.route("/run")
def run_now():
    try:
        from bot import detect, format_msg, send_telegram
        sig = detect()
        if sig:
            send_telegram(format_msg(sig))
            return f"Signal {sig['signal']} {sig['type']} envoyé - {sig['price']:.1f}"
        return "Pas de signal pour l instant - Bot OK"
    except Exception as e:
        return f"Erreur: {e}", 500

def loop():
    while True:
        try:
            from bot import detect, format_msg, send_telegram
            sig = detect()
            if sig: send_telegram(format_msg(sig))
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
