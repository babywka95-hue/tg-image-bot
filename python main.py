import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")

async def test_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Просто отвечает на любое сообщение.
    Это проверка, что бот живой.
    """
    await update.message.reply_text("✅ БОТ ЖИВОЙ! Render Background Worker работает.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # реагирует на все сообщения (текст, фото, стикеры)
    app.add_handler(MessageHandler(filters.ALL, test_message))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
