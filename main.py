from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import os

TELEGRAM_TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ БОТ ЖИВОЙ. КОД ОБНОВЛЁН И РАБОТАЕТ")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, test))
    app.run_polling()

if __name__ == "__main__":
    main()
