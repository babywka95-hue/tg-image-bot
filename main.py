import os
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(TOKEN)

app = Flask(__name__)

# ==========================
# WB SEARCH
# ==========================
def wb_search(query):
    try:
        url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}"
        r = requests.get(url, timeout=10)
        data = r.json()

        result = []
        for item in data["data"]["products"][:5]:
            pid = item["id"]
            name = item["name"]
            link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"
            result.append(f"{name}\n{link}")

        return result
    except:
        return []

# ==========================
# SIMPLE IMAGE ANALYSIS
# ==========================
def detect_query():
    # универсальный запрос
    return "одежда"

# ==========================
# PHOTO HANDLER
# ==========================
async def photo_handler(update, context):
    chat_id = update.effective_chat.id

    await bot.send_message(chat_id, "🔍 Ищу похожие товары...")

    query = detect_query()
    goods = wb_search(query)

    if not goods:
        await bot.send_message(chat_id, "❌ Ничего не найдено")
        return

    text = "🛍 Похожие товары:\n\n" + "\n\n".join(goods)
    await bot.send_message(chat_id, text[:4000])

# ==========================
# TELEGRAM APP
# ==========================
telegram_app = Application.builder().token(TOKEN).build()
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

# ==========================
# WEBHOOK
# ==========================
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await telegram_app.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "bot alive"

# ==========================
# START
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
