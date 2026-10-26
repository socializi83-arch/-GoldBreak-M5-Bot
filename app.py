from flask import Flask
import os, requests

app = Flask(__name__)

@app.route("/")
def home():
    return "GoldBreak M5 Bot - OK"

@app.route("/test")
def test():
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat = os.getenv("CHAT_ID", "")
    if not token:
        return "ERREUR: TELEGRAM_TOKEN vide sur Render - Va dans Environment"
    if not chat:
        return "ERREUR: CHAT_ID vide sur Render - Va dans Environment"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat, "text": "✅ TEST OK - Ton bot marche !"}, timeout=15)
    return f"REPONSE TELEGRAM: {r.text}<br><br>TOKEN debut: {token[:12]}...<br>CHAT_ID: {chat}"

@app.route("/debug")
def debug():
    return f"TOKEN existe: {bool(os.getenv('TELEGRAM_TOKEN'))} | CHAT_ID valeur: {os.getenv('CHAT_ID')}"

@app.route("/run")
def run_now():
    return "Pas de BREAK pour l instant - Bot OK"
