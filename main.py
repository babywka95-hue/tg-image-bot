import os
import io
import requests
import torch
import clip
from PIL import Image
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --------------------
TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")

BASE_URL = os.getenv("https://tg-image-bot-1-nrpn.onrender.com")  # Render сам даёт
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# --------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# --------------------
bot = Bot(token=TOKEN)
app = Flask(__name__)

application = ApplicationBuilder().token(TOKEN).build()

# --------------------
def wb_search(query, limit=100):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}&page=1&limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        return []

    return r.json().get("data", {}).get("products", [])

# --------------------
def analyze(products):
    if not products:
        return None

    total = len(products)
    strong = 0
    ultra = 0
    avg_reviews = 0

    for p in products:
        r = p.get("feedbacks", 0) or 0
        avg_reviews += r

        if r > 300:
            strong += 1
        if r > 1000:
            ultra += 1

    avg_reviews = avg_reviews / total if total else 0

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
        "avg_reviews": avg_reviews
    }

# --------------------
def build_query_from_image(image_input):
    prompts = [
        "a product sold online",
        "a household item",
        "a beauty product",
        "a fashion item",
        "a tech gadget",
        "a small consumer product"
    ]

    with torch.no_grad():
        text = clip.tokenize(prompts).to(device)
        text_f = model.encode_text(text)
        text_f /= text_f.norm(dim=-1, keepdim=True)

        img_f = model.encode_image(image_input)
        img_f /= img_f.norm(dim=-1, keepdim=True)

        sim = (img_f @ text_f.T).squeeze(0)
        idx = sim.argmax().item()

    query_map = {
        0: "product",
        1: "home goods",
        2: "beauty care",
        3: "clothing",
        4: "electronics",
        5: "consumer goods"
    }

    return query_map[idx]

# --------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Анализ товара...")

    query = build_query_from_image(image_input)
    await update.message.reply_text(f"📦 Поиск: {query}")

    products = wb_search(query, 100)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("❌ Нет данных")
        return

    msg = f"""
📊 АНАЛИЗ WB

📦 Товаров: {stats['total']}
💪 >300 отзывов: {stats['strong']}
🔥 >1000 отзывов: {stats['ultra']}
📈 Средние отзывы: {int(stats['avg_reviews'])}
"""

    if stats["ultra"] > 5:
        msg += "\n🚫 СЛОЖНЫЙ РЫНОК"
    elif stats["strong"] > 10:
        msg += "\n🟡 СРЕДНЯЯ КОНКУРЕНЦИЯ"
    else:
        msg += "\n🟢 МОЖНО ЗАХОДИТЬ"

    await update.message.reply_text(msg)

# регистрируем handler
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# --------------------
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put(update)
    return "ok"

# --------------------
if __name__ == "__main__":
    import asyncio

    async def setup():
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(url=WEBHOOK_URL)

    asyncio.run(setup())

    print("BOT STARTED")
    app.run(host="0.0.0.0", port=10000)
