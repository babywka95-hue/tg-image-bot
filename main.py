import os
import io
import requests
from flask import Flask, request

from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # например: https://xxx.onrender.com

bot = Bot(token=TOKEN)
app = Flask(__name__)

# --------------------
def wb_search(query, limit=50):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}&page=1&limit={limit}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return []
    return r.json().get("data", {}).get("products", [])

# --------------------
def analyze(products):
    if not products:
        return None

    total = len(products)
    strong = 0
    ultra = 0
    avg = 0

    for p in products:
        r = p.get("feedbacks", 0) or 0
        avg += r

        if r > 300:
            strong += 1
        if r > 1000:
            ultra += 1

    avg = avg / total if total else 0

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
        "avg": avg
    }

# --------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 Анализ... (без ML версия)")

    # упрощённый запрос (без CLIP)
    query = "product"

    products = wb_search(query)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("Нет данных")
        return

    msg = (
        f"📊 WB АНАЛИЗ\n\n"
        f"📦 товаров: {stats['total']}\n"
        f"💪 сильные: {stats['strong']}\n"
        f"🔥 монстры: {stats['ultra']}\n"
        f"📈 средние отзывы: {int(stats['avg'])}\n\n"
    )

    if stats["ultra"] > 5:
        msg += "🚫 сложно зайти"
    elif stats["strong"] > 10:
        msg += "🟡 средняя конкуренция"
    else:
        msg += "🟢 можно заходить"

    await update.message.reply_text(msg)

# --------------------
async def telegram_webhook(request_data):
    update = Update.de_json(request_data, bot)
    application = Application.builder().token(TOKEN).build()

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    await application.initialize()
    await application.process_update(update)
    await application.shutdown()

# --------------------
@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# --------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    import asyncio
    asyncio.run(telegram_webhook(data))

    return "ok"

# --------------------
import asyncio

def set_webhook():
    if not WEBHOOK_URL:
        raise Exception("WEBHOOK_URL not set")

    url = f"{WEBHOOK_URL}/webhook"

    async def setup():
        await bot.delete_webhook()
        await bot.set_webhook(url=url)

    asyncio.run(setup())

    print("Webhook set:", url)
# --------------------
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
