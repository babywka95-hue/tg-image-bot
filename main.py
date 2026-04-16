import os
import asyncio
import requests
from io import BytesIO

from flask import Flask, request

from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters

from openai import OpenAI

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# START
# =========================
async def start(update, context):
    await update.message.reply_text(
        "📸 Отправь фото товара — я найду точные аналоги на Wildberries"
    )

# =========================
# VISION ANALYSIS
# =========================
def analyze_image(image_bytes):
    try:
        import base64

        img_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Определи что на изображении. Верни только короткий поисковый запрос для интернет-магазина (1-4 слова)."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=20
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("VISION ERROR:", e)
        return "товар"

# =========================
# WB SEARCH
# =========================
def wb_search(query):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"

        params = {
            "query": query,
            "resultset": "catalog",
            "limit": 5
        }

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()

        products = data.get("data", {}).get("products", [])

        result = []

        for p in products[:5]:
            pid = p["id"]
            name = p["name"]
            price = p.get("salePriceU", 0) // 100

            link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

            result.append(
                f"🛍 {name}\n💰 {price} ₽\n🔗 {link}"
            )

        return result

    except Exception as e:
        print("WB ERROR:", e)
        return []

# =========================
# PHOTO HANDLER
# =========================
async def photo_handler(update, context):
    chat_id = update.effective_chat.id

    await bot.send_message(chat_id, "🔍 Анализирую изображение...")

    try:
        photo = update.message.photo[-1]

        file = await bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        # 🔥 AI VISION
        query = analyze_image(image_bytes)

        await bot.send_message(chat_id, f"🧠 Понял: {query}")

        goods = wb_search(query)

        if not goods:
            await bot.send_message(chat_id, "❌ Ничего не найдено")
            return

        text = "🛒 Похожие товары:\n\n" + "\n\n".join(goods)

        await bot.send_message(chat_id, text[:4000])

    except Exception as e:
        print("PHOTO ERROR:", e)
        await bot.send_message(chat_id, "❌ Ошибка обработки")

# =========================
# HANDLERS
# =========================
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

asyncio.run(telegram_app.initialize())

# =========================
# WEBHOOK
# =========================
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
    return "PRO MAX LITE running"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
