import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
URL = os.getenv("PUBLIC_URL")
PORT = int(os.getenv("PORT", "10000"))

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")

if not URL:
    raise Exception("PUBLIC_URL is missing")

# Обработчик фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Берем самое большое изображение
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Создаем папку downloads, если нет
        os.makedirs("downloads", exist_ok=True)
        file_path = f"downloads/{photo.file_id}.jpg"

        # Скачиваем фото
        await file.download_to_drive(file_path)

        # Ответ пользователю
        await update.message.reply_text(f"📦 Фото получено и сохранено как {file_path}")

    except Exception as e:
        logging.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке фото.")

def main():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчик фото
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Запуск в режиме webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=f"{URL}/webhook"
    )

if __name__ == "__main__":
    main()
