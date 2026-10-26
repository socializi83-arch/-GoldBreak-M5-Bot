from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 Bot - Break/Strong Break - OK"

@app.route("/run")
def run_now():
    try:
        from bot import detect, format_msg, send_telegram
        sig = detect()
        if sig:
            send_telegram(format_msg(sig))
            return f"{sig['break_type']} {sig['type']} envoye"
        return "Pas de BREAK pour l instant - Bot OK"
    except Exception as e:
        return f"Erreur: {e}", 500

# La boucle tourne seulement si on n'est pas en train de builder
if os.getenv("RENDER") != "1":
    import threading, time
    def loop():
        while True:
            try:
                from bot import detect, format_msg, send_telegram
                sig = detect()
                if sig: send_telegram(format_msg(sig))
            except: pass
            time.sleep(60)
    threading.Thread(target=loop, daemon=True).start()
