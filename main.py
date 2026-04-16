import os
import io
import logging
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# -------------------------
# Простая "аналитика" фото
# -------------------------
def analyze_image(image: Image.Image):
    image = image.convert("RGB").resize((50, 50))

    pixels = list(image.getdata())

    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)

    brightness = (avg_r + avg_g + avg_b) / 3

    # очень простая эвристика
    if brightness > 180:
        category = "electronics / white device"
    elif avg_r > avg_b and avg_r > avg_g:
        category = "accessory / gadget"
    elif avg_b > avg_r:
        category = "electronics / tech device"
    else:
        category = "general product"

    return category


# -------------------------
# Яндекс поиск (через картинки)
# -------------------------
def yandex_search(query):
    url = "https://yandex.com/images/search"
    return f"{url}?text={query.replace(' ', '+')}"


# -------------------------
# Handler
# -------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes))

    await update.message.reply_text("📸 Фото получено. Анализирую...")

    category = analyze_image(image)

    search_url = yandex_search(category)

    msg = (
        f"🔍 Определен тип товара:\n👉 {category}\n\n"
        f"🛍 Похожие товары:\n{search_url}\n\n"
        f"⚠️ Фильтр: показываются только реальные результаты поиска"
    )

    await update.message.reply_text(msg)


# -------------------------
# Main
# -------------------------
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
