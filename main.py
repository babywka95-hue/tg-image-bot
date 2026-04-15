import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ---------------- CONFIG ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PUBLIC_URL = os.environ.get("PUBLIC_URL")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing")

if not PUBLIC_URL:
    raise Exception("PUBLIC_URL is missing")

# ---------------- TELEGRAM APP ----------------
app_telegram = Application.builder().token(BOT_TOKEN).build()

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает ✅")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📷 Фото получено! Бот работает.")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ты написал: {update.message.text}")

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

# ---------------- FLASK ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    update = Update.de_json(data, app_telegram.bot)

    # ВАЖНО: это правильная очередь PTB
    app_telegram.update_queue.put_nowait(update)

    return "ok"

# ---------------- SET WEBHOOK ----------------
def setup_webhook():
    url = f"{PUBLIC_URL}/webhook"
    app_telegram.bot.set_webhook(url=url)
    print("Webhook set:", url)

# ---------------- START ----------------
if __name__ == "__main__":
    setup_webhook()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
