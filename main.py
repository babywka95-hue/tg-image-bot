import os
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
telegram_app = Application.builder().token(TOKEN).build()

app = Flask(__name__)

# ==========================
# Фото
# ==========================
async def photo_handler(update, context):
    chat_id = update.effective_chat.id

    await bot.send_message(chat_id, "🔍 Ищу похожие товары...")

    text = """🛍 Нашёл варианты:

https://www.wildberries.ru/catalog/1/detail.aspx

https://www.wildberries.ru/catalog/2/detail.aspx

https://www.wildberries.ru/catalog/3/detail.aspx
"""
    await bot.send_message(chat_id, text)

telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

# ==========================
# WEBHOOK
# ==========================
import asyncio

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)

    asyncio.run(telegram_app.process_update(update))

    return "ok"

@app.route("/")
def home():
    return "bot alive"

# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
