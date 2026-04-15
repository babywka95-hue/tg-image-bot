import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
URL = os.getenv("PUBLIC_URL")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")

if not URL:
    raise Exception("PUBLIC_URL is missing")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 Фото получено, обработка...")


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path="webhook",
        webhook_url=f"{URL}/webhook"
    )


if __name__ == "__main__":
    main()
