import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")  # например https://your-app.onrender.com

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


# --------------------
def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


# --------------------
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


# --------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data or "message" not in data:
        return "ok", 200

    message = data["message"]
    chat_id = message["chat"]["id"]

    text = message.get("text", "")

    if text:
        send_message(chat_id, f"Ты написал: {text}")

    return "ok", 200


# --------------------
def set_webhook():
    url = f"{TELEGRAM_API}/setWebhook"
    requests.get(url, params={
        "url": f"{PUBLIC_URL}/webhook"
    })


# --------------------
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
