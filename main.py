import os
import re
import asyncio
import requests
from io import BytesIO
from PIL import Image
from flask import Flask, request

from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters

# ==========================================
# CONFIG
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
telegram_app = Application.builder().token(TOKEN).build()
app = Flask(__name__)

# ==========================================
# OCR API (free)
# ==========================================
OCR_KEY = "helloworld"   # бесплатный demo key

# ==========================================
# START
# ==========================================
async def start(update, context):
    await update.message.reply_text(
        "📸 Отправь фото товара.\n"
        "Я найду похожие товары на Wildberries."
    )

# ==========================================
# OCR FROM IMAGE
# ==========================================
def read_text_from_image(image_bytes):
    try:
        files = {
            "filename": ("image.jpg", image_bytes)
        }

        data = {
            "apikey": OCR_KEY,
            "language": "rus+eng",
            "isOverlayRequired": False
        }

        r = requests.post(
            "https://api.ocr.space/parse/image",
            files=files,
            data=data,
            timeout=30
        )

        result = r.json()

        text = result["ParsedResults"][0]["ParsedText"]

        return text.strip()

    except:
        return ""

# ==========================================
# SMART QUERY
# ==========================================
def detect_query(text):
    text = text.lower()

    words = re.findall(r"[a-zA-Zа-яА-Я0-9]+", text)

    blacklist = {
        "size", "made", "wash", "cotton",
        "xl", "xxl", "l", "m", "s",
        "руб", "цена", "новый"
    }

    good = []

    for w in words:
        if len(w) > 2 and w not in blacklist:
            good.append(w)

    query = " ".join(good[:4])

    if not query:
        query = "женская одежда"

    return query

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

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        data = r.json()

        products = data.get("data", {}).get("products", [])

        result = []

        for item in products[:5]:
            pid = item["id"]
            name = item["name"]
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
# PHOTO HANDLER
# ==========================================
async def photo_handler(update, context):
    chat_id = update.effective_chat.id

    await bot.send_message(chat_id, "🔍 Анализирую фото...")

    try:
        photo = update.message.photo[-1]

        file = await bot.get_file(photo.file_id)

        image_bytes = await file.download_as_bytearray()

        # OCR text
        text = read_text_from_image(image_bytes)

        # detect query
        query = detect_query(text)

        await bot.send_message(
            chat_id,
            f"🧠 Нашёл запрос:\n{query}"
        )

        goods = wb_search(query)

        if not goods:
            await bot.send_message(
                chat_id,
                "❌ Ничего не найдено."
            )
            return

        answer = "🛒 Похожие товары:\n\n"
        answer += "\n\n".join(goods)

        await bot.send_message(chat_id, answer[:4000])

    except Exception as e:
        print("PHOTO ERROR:", e)
        await bot.send_message(
            chat_id,
            "❌ Ошибка обработки фото."
        )

# ==========================================
# HANDLERS
# ==========================================
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.PHOTO, photo_handler)
)

asyncio.run(telegram_app.initialize())

# ==========================================
# WEBHOOK
# ==========================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)

        asyncio.run(
            telegram_app.process_update(update)
        )

        return "ok"

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "error"

@app.route("/")
def home():
    return "bot alive"

# ==========================================
# START SERVER
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
