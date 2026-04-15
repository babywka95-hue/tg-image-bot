from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"
WEBHOOK_PATH = "/webhook"  # путь webhook
PORT = 10000  # локальный порт, Render его перенаправляет автоматически

app = Flask(__name__)
bot = Bot(token=TOKEN)

# Создаем Application для обработки команд
application = ApplicationBuilder().token(TOKEN).build()

# Пример команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен через webhook!")

application.add_handler(CommandHandler("start", start))

# Flask endpoint для webhook
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    # Обработка update через Application
    application.update_queue.put(update)
    return "OK"

if __name__ == "__main__":
    # Устанавливаем webhook при старте
    webhook_url = f"https://<YOUR_RENDER_SUBDOMAIN>.onrender.com{WEBHOOK_PATH}"
    bot.delete_webhook()
    bot.set_webhook(url=webhook_url)
    
    print(f"Webhook установлен: {webhook_url}")
    
    # Запускаем Flask
    app.run(host="0.0.0.0", port=PORT)
