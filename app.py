from flask import Flask
import os, requests

app = Flask(__name__)

@app.route("/")
def home(): return "GoldBreak M5 - FibAlgo Golden Zone - OK"

@app.route("/test")
def test():
    token = os.getenv("TELEGRAM_TOKEN","")
    chat = os.getenv("CHAT_ID","")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id":chat,"text":"✅ TEST OK - FibAlgo Clone marche !"}, timeout=10)
    return f"REPONSE TELEGRAM: {r.text}"

@app.route("/run")
def run_now():
    from bot import detect, format_msg, send_telegram
    sig = detect()
    if sig:
        send_telegram(format_msg(sig))
        return f"Signal {sig['type']} envoyé"
    return "Pas de BREAK - Bot OK"

def loop():
    import time
    while True:
        try:
            from bot import detect, format_msg, send_telegram
            sig = detect()
            if sig: send_telegram(format_msg(sig))
        except: pass
        time.sleep(60)

import threading
threading.Thread(target=loop, daemon=True).start()
