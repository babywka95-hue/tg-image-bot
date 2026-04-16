import logging
import io
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"

logging.basicConfig(level=logging.INFO)

# ======================
# AI (реальный анализ через HF)
# ======================
def classify(image_bytes):
    API = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"

    r = requests.post(API, data=image_bytes)

    try:
        data = r.json()
        if isinstance(data, list):
            return data[0]["label"].lower()
    except:
        pass

    return "electronic device"


# ======================
# WB SEARCH
# ======================
def wb_search(query):
    url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={query}&resultset=catalog"

    r = requests.get(url)

    if r.status_code != 200:
        return []

    data = r.json()
    products = data.get("data", {}).get("products", [])

    results = []

    for p in products[:5]:
        name = p.get("name")
        id_ = p.get("id")

        if not name or not id_:
            continue

        link = f"https://www.wildberries.ru/catalog/{id_}/detail.aspx"
        results.append((name, link))

    return results


# ======================
# MAP CLEAN
# ======================
def clean_query(label):
    label = label.lower()

    if any(x in label for x in ["shaver", "epilator", "razor"]):
        return "эпилятор"

    if any(x in label for x in ["phone", "mobile"]):
        return "смартфон"

    if any(x in label for x in ["headphone", "earphone"]):
        return "наушники"

    if "watch" in label:
        return "смарт часы"

    return "электроника"


# ======================
# HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Анализирую фото...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    # 1. AI classification
    label = classify(image_bytes)

    # 2. clean query
    query = clean_query(label)

    # 3. WB search
    items = wb_search(query)

    msg = f"🔍 Определено: {query}\n\n🛍 Похожие товары:\n\n"

    if not items:
        msg += "Товары не найдены"
    else:
        for name, link in items:
            msg += f"• {name}\n{link}\n\n"

    await update.message.reply_text(msg)


# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
