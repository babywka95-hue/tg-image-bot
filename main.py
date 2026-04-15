import os
import requests

from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing")

app = Flask(__name__)

# Telegram App
tg_app = Application.builder().token(BOT_TOKEN).build()


# -----------------------
# SIMPLE WB SEARCH
# -----------------------
def wb_search(query):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}&page=1&limit=20"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        return data.get("data", {}).get("products", [])
    except:
        return []


def analyze(products):
    if not products:
        return None

    total = len(products)
    strong = sum(1 for p in products if (p.get("feedbacks", 0) or 0) > 300)
    ultra = sum(1 for p in products if (p.get("feedbacks", 0) or 0) > 1000)

    avg = sum(p.get("feedbacks", 0) or 0 for p in products) / total

    return total, strong, ultra, avg


# -----------------------
# HANDLERS
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Бот работает! Отправь фото товара")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Анализирую товар...")

    # Упрощённый запрос (без CLIP)
    query = "product"

    products = wb_search(query)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("❌ Нет данных WB")
        return

    total, strong, ultra, avg = stats

    msg = (
        f"📊 АНАЛИЗ WB\n\n"
        f"📦 Товаров: {total}\n"
        f"💪 >300 отзывов: {strong}\n"
        f"🔥 >1000 отзывов: {ultra}\n"
        f"📈 Средние отзывы: {int(avg)}\n\n"
    )

    if ultra > 5:
        msg += "🚫 СЛОЖНАЯ НИША"
    elif strong > 10:
        msg += "🟡 СРЕДНЯЯ КОНКУРЕНЦИЯ"
    else:
        msg += "🟢 МОЖНО ЗАХОДИТЬ"

    await update.message.reply_text(msg)


tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))


# -----------------------
# WEBHOOK
# -----------------------
@app.route("/")
def home():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)

    await tg_app.process_update(update)
    return "ok"


# -----------------------
# START SERVER
# -----------------------
if __name__ == "__main__":
    import asyncio

    async def setup():
        await tg_app.initialize()
        await tg_app.bot.delete_webhook()
        await tg_app.bot.set_webhook(f"{PUBLIC_URL}/webhook")

        print("Webhook set:", f"{PUBLIC_URL}/webhook")

    asyncio.run(setup())

    app.run(host="0.0.0.0", port=10000)
