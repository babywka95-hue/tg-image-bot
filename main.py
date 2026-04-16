import os
import asyncio
import requests
import torch
import clip
from PIL import Image
from io import BytesIO
from flask import Flask, request

from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()

device = "cuda" if torch.cuda.is_available() else "cpu"

model, preprocess = clip.load("ViT-B/32", device=device)

# =========================
# WB SEARCH
# =========================
def wb_search(query):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"

        params = {
            "query": query,
            "resultset": "catalog",
            "limit": 5
        }

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()

        products = data.get("data", {}).get("products", [])

        out = []

        for p in products[:5]:
            pid = p["id"]
            name = p["name"]
            price = p.get("salePriceU", 0) // 100

            link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

            out.append(
                f"🛍 {name}\n💰 {price} ₽\n🔗 {link}"
            )

        return out

    except Exception as e:
        print("WB ERROR:", e)
        return []

# =========================
# CLIP CATEGORY DETECTION
# =========================
CATEGORIES = [
    "epilator",
    "shoes sneakers",
    "handbag",
    "smartphone",
    "watch",
    "hair trimmer",
    "cosmetics",
    "kitchen appliance",
    "vacuum cleaner",
    "clothing dress",
]

def classify_image(image):
    image_input = preprocess(image).unsqueeze(0).to(device)

    text_inputs = clip.tokenize(CATEGORIES).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        text_features = model.encode_text(text_inputs)

        logits = image_features @ text_features.T
        probs = logits.softmax(dim=-1).cpu().numpy()[0]

    best_idx = probs.argmax()

    return CATEGORIES[best_idx]

# =========================
# PHOTO HANDLER
# =========================
async def photo_handler(update, context):
    chat_id = update.effective_chat.id

    await bot.send_message(chat_id, "🔍 Анализирую изображение...")

    try:
        photo = update.message.photo[-1]
        file = await bot.get_file(photo.file_id)

        image_bytes = await file.download_as_bytearray()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        category = classify_image(image)

        await bot.send_message(
            chat_id,
            f"🧠 Определено: {category}"
        )

        goods = wb_search(category)

        if not goods:
            await bot.send_message(chat_id, "❌ Ничего не найдено")
            return

        text = "🛒 Похожие товары:\n\n" + "\n\n".join(goods)

        await bot.send_message(chat_id, text[:4000])

    except Exception as e:
        print("PHOTO ERROR:", e)
        await bot.send_message(chat_id, "❌ Ошибка обработки")

# =========================
# START
# =========================
async def start(update, context):
    await update.message.reply_text("📸 Отправь фото товара")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

asyncio.run(telegram_app.initialize())

# =========================
# WEBHOOK
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)

    asyncio.run(telegram_app.process_update(update))
    return "ok"

@app.route("/")
def home():
    return "Lens PRO 2.0 running"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
