import os
import io
import logging
import requests
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ======================
# ПРОСТОЙ "ПОИСК" (ЗАГЛУШКА API)
# сюда позже вставим WB / Yandex / SerpAPI
# ======================
def fake_search(image: Image.Image):
    return [
        {
            "name": "Эпилятор Philips Satinelle",
            "url": "https://example.com/1"
        },
        {
            "name": "Braun Silk-épil 9",
            "url": "https://example.com/2"
        },
        {
            "name": "Remington эпилятор женский",
            "url": "https://example.com/3"
        }
    ]


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    await update.message.reply_text("🔍 Ищу товар по изображению...")

    results = fake_search(image)

    msg = "🛍 Найденные товары:\n\n"

    for r in results:
        msg += f"• {r['name']}\n🔗 {r['url']}\n\n"

    await update.message.reply_text(msg)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
