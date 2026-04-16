import os
import asyncio
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters

# ==========================================
# CONFIG
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)

telegram_app = Application.builder().token(TOKEN).build()

app = Flask(__name__)

# ==========================================
# WB SEARCH
# ==========================================
def wb_search(query):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
        params = {
            "query": query,
            "resultset": "catalog",
            "limit": 5
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        products = data.get("data", {}).get("products", [])

        result = []

        for item in products[:5]:
            pid = item.get("id")
            name = item.get("name", "Товар")
            price = item.get("salePriceU", 0) // 100

            link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

            result.append(
                f"🛍 {name}\n"
                f"💰 {price} ₽\n"
                f"🔗 {link}"
            )

        return result

    except Exception as e:
        print("WB ERROR:", e)
        return []

# ==========================================
# PHOTO ANALYSIS
# ==========================================
def detect_query():
    # Легкий стабильный вариант без памяти
    return "женская одежда"

# ==========================================
# PHOTO HANDLER
# ==========================================
async def photo_handler(update, context):
    chat_id = update.effective_chat.id

    await bot.send_message(chat_id, "🔍 Анализирую фото...")

    query = detect_query()

    goods = wb_search(query)

    if not goods:
        await bot.send_message(
            chat_id,
            "❌ Ничего не найдено.\nПопробуй другое фото."
        )
        return

    text = "🛒 Похожие товары Wildberries:\n\n"
    text += "\n\n".join(goods)

    await bot.send_message(chat_id, text[:4000])

# ==========================================
# HANDLERS
# ==========================================
telegram_app.add_handler(
    MessageHandler(filters.PHOTO, photo_handler)
)

# ==========================================
# INIT TELEGRAM APP
# ==========================================
asyncio.run(telegram_app.initialize())

# ==========================================
# WEBHOOK
# ==========================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)

        asyncio.run(telegram_app.process_update(update))

        return "ok"

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "error"

@app.route("/")
def home():
    return "bot alive"

# ==========================================
# START
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
