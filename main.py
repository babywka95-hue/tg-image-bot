import os
import io
import logging
import requests

from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

# ======================
# SIMPLE IMAGE → QUERY (СТАБИЛЬНО)
# ======================
def detect_query():
    # пока без ML, но стабильно
    return "товар"

# ======================
# WILDBERRIES SEARCH
# ======================
def wb_search(query):
    url = "https://search.wb.ru/exactmatch/ru/common/v5/search"

    params = {
        "query": query,
        "resultset": "catalog",
        "limit": 5
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()

        products = data.get("data", {}).get("products", [])

        results = []

        for p in products:
            pid = p.get("id")
            name = p.get("name")

            results.append({
                "name": name,
                "url": f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"
            })

        return results

    except Exception as e:
        print("WB ERROR:", e)
        return []


# ======================
# HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    # просто читаем (не анализируем тяжёлым AI)
    Image.open(io.BytesIO(image_bytes)).convert("RGB")

    await update.message.reply_text("🔍 Ищу похожие товары...")

    query = detect_query()

    products = wb_search(query)

    if not products:
        await update.message.reply_text("❌ Ничего не найдено")
        return

    msg = "🛍 Найденные товары:\n\n"

    for p in products:
        msg += f"• {p['name']}\n🔗 {p['url']}\n\n"

    await update.message.reply_text(msg[:4000])


# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
