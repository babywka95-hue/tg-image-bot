import os
import requests
import torch
from PIL import Image
from flask import Flask, request

from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, filters, ContextTypes

import clip

# =====================
# CONFIG
# =====================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = TOKEN

bot = Bot(token=TOKEN)

app = Flask(__name__)

# =====================
# MODEL (CLIP)
# =====================
device = "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# =====================
# WB SEARCH (простая версия)
# =====================
def search_wb(query):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}"
    r = requests.get(url, timeout=10)
    data = r.json()

    products = []
    try:
        for item in data["data"]["products"][:5]:
            products.append(
                f"https://www.wildberries.ru/catalog/{item['id']}/detail.aspx"
            )
    except:
        pass

    return products


# =====================
# IMAGE ANALYSIS
# =====================
def analyze_image(image_path):
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)

    text = clip.tokenize([
        "dress",
        "t-shirt",
        "shoes",
        "bag",
        "jacket",
        "phone case",
        "watch",
        "pants"
    ]).to(device)

    with torch.no_grad():
        logits_per_image, logits_per_text = model(image, text)
        probs = logits_per_image.softmax(dim=-1).cpu().numpy()[0]

    labels = ["dress","t-shirt","shoes","bag","jacket","phone case","watch","pants"]
    best = labels[probs.argmax()]

    return best


# =====================
# TELEGRAM HANDLER
# =====================
def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.photo[-1].get_file()
    path = "image.jpg"
    file.download(path)

    update.message.reply_text("🔍 Ищу похожие товары...")

    label = analyze_image(path)
    links = search_wb(label)

    if not links:
        update.message.reply_text("❌ Ничего не найдено")
        return

    result = "🛍 Найденные товары:\n\n" + "\n".join(links)
    update.message.reply_text(result)


# =====================
# FLASK ROUTE (WEBHOOK)
# =====================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "ok"


# =====================
# INIT DISPATCHER
# =====================
dispatcher = Dispatcher(bot=bot, update_queue=None)
dispatcher.add_handler(MessageHandler(filters.PHOTO, handle_photo))


# =====================
# START SERVER (ВАЖНО ДЛЯ RENDER)
# =====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
