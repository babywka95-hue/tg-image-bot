import os
import io
import logging
from PIL import Image

from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


def handle_photo(update: Update, context: CallbackContext):
    photo = update.message.photo[-1]

    file = context.bot.get_file(photo.file_id)
    image_bytes = file.download_as_bytearray()

    Image.open(io.BytesIO(image_bytes)).convert("RGB")

    update.message.reply_text("📸 Фото получено. Базовая версия работает")


def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))

    print("Bot started")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
