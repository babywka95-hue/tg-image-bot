import logging
import io
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"

logging.basicConfig(level=logging.INFO)

# ======================
# SIMPLE OCR (очень лёгкий fallback)
# ======================
def extract_keywords(image_bytes):
    """
    Упрощённо: пока без OCR (можно добавить позже tesseract)
    """
    return "эпилятор"


# ======================
# WB SEARCH API (официальный endpoint каталога)
# ======================
def wb_search(query: str):
    url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={query}&resultset=catalog"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return []

    data = r.json()

    products = data.get("data", {}).get("products", [])

    results = []

    for p in products[:5]:
        name = p.get("name")
        id_ = p.get("id")

        link = f"https://www.wildberries.ru/catalog/{id_}/detail.aspx"

        results.append((name, link))

    return results


# ======================
# HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Анализирую товар...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    # 1. получаем ключевое слово
    query = extract_keywords(image_bytes)

    # 2. ищем на WB
    items = wb_search(query)

    if not items:
        await update.message.reply_text("❌ Товары не найдены")
        return

    msg = f"🔍 Найдено по запросу: {query}\n\n🛍 Похожие товары:\n\n"

    for name, link in items:
        msg += f"• {name}\n{link}\n\n"

    await update.message.reply_text(msg)


# ======================
# START
# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
