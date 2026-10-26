from flask import Flask
import os, requests, threading, time, traceback

app = Flask(__name__)

@app.route("/")
def home():
    try: return "GoldBreak M5 - FibAlgo BREAK+ENTRY - OK"
    except: return "OK", 200

@app.route("/test")
def test():
    try:
        token = os.getenv("TELEGRAM_TOKEN","")
        chat = os.getenv("CHAT_ID","") or os.getenv("TELEGRAM_CHAT_ID","")
        if not token: return "TELEGRAM_TOKEN vide"
        if not chat: return "CHAT_ID vide"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id":chat,"text":"✅ TEST OK - Final Fix marche !"}, timeout=15)
        return f"REPONSE TELEGRAM: {r.text}"
    except Exception as e:
        return f"ERREUR TEST: {e}<br>{traceback.format_exc()}", 500

@app.route("/run")
def run_now():
    try:
        from bot import detect, format_msg, send_telegram
        sig = detect()
        if sig:
            send_telegram(format_msg(sig))
            return f"Signal {sig['signal']} {sig['type']} envoye"
        return "Pas de signal - Bot OK"
    except Exception as e:
        return f"Erreur run: {e}", 200

def loop():
    while True:
        try:
            from bot import detect, format_msg, send_telegram
            sig = detect()
            if sig: send_telegram(format_msg(sig))
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
