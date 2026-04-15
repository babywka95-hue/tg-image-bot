import os
import io
import requests
from PIL import Image
from flask import Flask, request

from telegram import Bot, Update

# --------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise Exception("No TELEGRAM_TOKEN")

bot = Bot(token=TOKEN)

app = Flask(__name__)

# --------------------
def wb_search(query, limit=100):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
        params = {"query": query, "page": 1, "limit": limit}

        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []

        data = r.json()
        return data.get("data", {}).get("products", [])
    except:
        return []

# --------------------
def analyze(products):
    if not products:
        return None

    total = len(products)
    strong = 0
    ultra = 0
    avg_reviews = 0

    for p in products:
        r = p.get("feedbacks", 0) or 0
        avg_reviews += r

        if r > 300:
            strong += 1
        if r > 1000:
            ultra += 1

    avg_reviews = avg_reviews / total

    return total, strong, ultra, int(avg_reviews)

# --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, bot)

    if update.message and update.message.photo:
        chat_id = update.message.chat.id

        bot.send_message(chat_id, "🔍 Анализируем...")

        # простая логика без CLIP (чтобы не жрал память)
        query = "товар"

        products = wb_search(query)
        stats = analyze(products)

        if not stats:
            bot.send_message(chat_id, "❌ Нет данных")
            return "ok"

        total, strong, ultra, avg = stats

        msg = (
            f"📊 АНАЛИЗ\n\n"
            f"📦 Товаров: {total}\n"
            f"💪 >300 отзывов: {strong}\n"
            f"🔥 >1000 отзывов: {ultra}\n"
            f"📈 Средние: {avg}\n\n"
        )

        if ultra > 5:
            msg += "🚫 Сложно"
        elif strong > 10:
            msg += "🟡 Средне"
        else:
            msg += "🟢 Можно заходить"

        bot.send_message(chat_id, msg)

    return "ok"

# --------------------
@app.route("/")
def home():
    return "Bot is running"

# --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
