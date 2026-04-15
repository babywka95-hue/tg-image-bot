import os
import requests
from flask import Flask, request

from telegram import Update, Bot
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise Exception("No TELEGRAM_TOKEN")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# =====================
def wb_search(query):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}&page=1&limit=30"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return []
    return r.json().get("data", {}).get("products", [])

# =====================
def analyze(products):
    if not products:
        return None

    total = len(products)
    strong = sum(1 for p in products if (p.get("feedbacks", 0) or 0) > 300)
    ultra = sum(1 for p in products if (p.get("feedbacks", 0) or 0) > 1000)

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
    }

# =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or "product"

    await update.message.reply_text("🔍 ищу данные WB...")

    products = wb_search(text)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("❌ нет данных WB API")
        return

    await update.message.reply_text(
        f"📊 WB\n"
        f"📦 товаров: {stats['total']}\n"
        f"💪 сильные: {stats['strong']}\n"
        f"🔥 монстры: {stats['ultra']}"
    )

# =====================
application = Application.builder().token(TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT, handle_message))

# =====================
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    application.update_queue.put_nowait(update)
    return "ok"

# =====================
@app.route("/", methods=["GET"])
def home():
    return "OK"

# =====================
def set_webhook():
    url = f"{WEBHOOK_URL}/webhook"
    bot.delete_webhook()
    bot.set_webhook(url=url)
    print("Webhook:", url)

# =====================
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
