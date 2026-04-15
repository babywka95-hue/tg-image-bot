import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает 🚀")

def main():
    app = Application.builder().token(TOKEN).build()

    # 🔥 УБИРАЕМ КОНФЛИКТЫ С ДРУГИМИ СЕССИЯМИ
    app.bot.delete_webhook(drop_pending_updates=True)

    app.add_handler(CommandHandler("start", start))

    print("Bot started")

    app.run_polling(
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
