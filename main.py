import os
import io
import logging
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")


print("🔥 MAIN STARTED (NO TORCH VERSION)")


# ----------------------------
# Анализ изображения (без AI)
# ----------------------------
def analyze_image(image: Image.Image):
    image = image.convert("RGB").resize((40, 40))
    pixels = list(image.getdata())

    r = sum(p[0] for p in pixels) / len(pixels)
    g = sum(p[1] for p in pixels) / len(pixels)
    b = sum(p[2] for p in pixels) / len(pixels)

    brightness = (r + g + b) / 3

    # простая, но стабильная логика
    if brightness > 200:
        return "electronics / white device"
    elif r > b and r > g:
        return "accessories / small gadgets"
    elif b > r:
        return "tech / electronics device"
    else:
        return "general product"


# ----------------------------
# Яндекс поиск картинок
# ----------------------------
def yandex_search(query: str):
    return f"https://yandex.com/images/search?text={query.replace(' ', '+')}"


# ----------------------------
# Telegram handler
# ----------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]

        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        image = Image.open(io.BytesIO(image_bytes))

        await update.message.reply_text("📸 Фото получено. Анализирую...")

        category = analyze_image(image)
        search_url = yandex_search(category)

        response = (
            f"🔍 Категория товара:\n👉 {category}\n\n"
            f"🛍 Похожие товары:\n{search_url}\n\n"
            f"⚠️ Поиск через Яндекс Images (без API ограничений)"
        )

        await update.message.reply_text(response)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


# ----------------------------
# MAIN
# ----------------------------
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN is NOT set")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 BOT IS RUNNING")
    app.run_polling()


if __name__ == "__main__":
    main()
