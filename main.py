import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN")
URL = os.getenv("PUBLIC_URL")  # https://xxxx.onrender.com

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set")

# ---------------- APP ----------------
app = Flask(__name__)

telegram_app = Application.builder().token(TOKEN).build()

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает ✅")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ты написал: {update.message.text}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# ---------------- WEBHOOK ROUTE ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)

    telegram_app.update_queue.put_nowait(update)
    return "ok"

# ---------------- STARTUP ----------------
@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

def set_webhook():
    webhook_url = f"{URL}/webhook"
    telegram_app.bot.set_webhook(url=webhook_url)
    print("Webhook set:", webhook_url)

# ---------------- RUN ----------------
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
