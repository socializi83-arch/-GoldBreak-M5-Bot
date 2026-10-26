from flask import Flask
from bot import detect, format_msg, send_telegram
import threading, time

app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 Bot - Break/Strong Break - OK"

@app.route("/run")
def run_now():
    sig = detect()
    if sig:
        send_telegram(format_msg(sig))
        return f"{sig['break_type']} {sig['type']} envoyé"
    return "Pas de BREAK"

def loop():
    while True:
        try:
            sig = detect()
            if sig:
                send_telegram(format_msg(sig))
        except Exception as e:
            print(e)
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
