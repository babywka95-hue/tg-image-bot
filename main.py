import os
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()
bot = Bot(token=TOKEN)

application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает 🚀")

application.add_handler(CommandHandler("start", start))


@app.get("/")
def home():
    return "Bot is alive"


@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}


@app.on_event("startup")
async def startup():
    await application.initialize()
    await bot.set_webhook(os.getenv("WEBHOOK_URL"))
