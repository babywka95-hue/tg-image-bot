import os
import io
import requests
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise Exception("TELEGRAM_TOKEN is missing")


def simple_image_classifier(image: Image.Image):
    image = image.convert("RGB")
    pixels = list(image.getdata())

    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)

    brightness = (avg_r + avg_g + avg_b) / 3

    if brightness > 180:
        return "beauty product"
    elif avg_r > avg_g and avg_r > avg_b:
        return "fashion item"
    elif avg_b > avg_r:
        return "electronics"
    else:
        return "household item"


def wb_search(query, limit=50):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}&page=1&limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        return []

    return r.json().get("data", {}).get("products", [])


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

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
        "avg_reviews": avg_reviews / total
    }


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(img_bytes))

    await update.message.reply_text("🔍 Анализ...")

    query = simple_image_classifier(image)

    await update.message.reply_text(f"📦 WB поиск: {query}")

    products = wb_search(query)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("❌ Нет данных")
        return

    msg = (
        f"📊 WB АНАЛИЗ\n\n"
        f"📦 Товаров: {stats['total']}\n"
        f"💪 >300 отзывов: {stats['strong']}\n"
        f"🔥 >1000 отзывов: {stats['ultra']}\n"
        f"📈 Средние: {int(stats['avg_reviews'])}\n"
    )

    await update.message.reply_text(msg)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
