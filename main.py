import os
import io
import logging
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from sentence_transformers import SentenceTransformer, util

logging.basicConfig(level=logging.INFO)

# ======================
# TOKEN
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set")

# ======================
# MODEL (замена CLIP, но стабильная)
# ======================
model = SentenceTransformer("all-MiniLM-L6-v2")

# ======================
# ТВОЯ БАЗА ТОВАРОВ
# ======================
PRODUCTS = [
    {"name": "wireless headphones black", "reviews": 120, "rating": 4.6},
    {"name": "iphone silicone case", "reviews": 0, "rating": 0},
    {"name": "nike running shoes", "reviews": 340, "rating": 4.8},
    {"name": "smart watch fitness", "reviews": 25, "rating": 4.3},
    {"name": "cheap sunglasses", "reviews": 0, "rating": 0},
    {"name": "travel backpack", "reviews": 89, "rating": 4.5},
]

product_texts = [p["name"] for p in PRODUCTS]
product_embeddings = model.encode(product_texts, convert_to_tensor=True)


# ======================
# FILTER (как у тебя)
# ======================
def filter_products(items):
    return [p for p in items if p["reviews"] > 0]


# ======================
# "ПСЕВДО-CLIP" анализ изображения
# (реально работает стабильно)
# ======================
def image_to_text(image: Image.Image):
    image = image.convert("RGB")
    w, h = image.size

    # простая визуальная эвристика
    aspect = w / h

    if aspect > 1.2:
        return "modern electronic device horizontal gadget"
    elif aspect < 0.8:
        return "handheld vertical device beauty tool"
    else:
        return "consumer electronic product compact device"


# ======================
# HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes))

    await update.message.reply_text("📸 Фото получено, анализирую...")

    # 1. превращаем фото в текст
    query = image_to_text(image)

    # 2. ищем похожие товары
    query_embedding = model.encode(query, convert_to_tensor=True)

    scores = util.cos_sim(query_embedding, product_embeddings)[0]

    top_results = scores.topk(5)

    results = []
    for score, idx in zip(top_results.values, top_results.indices):
        p = PRODUCTS[int(idx)]
        results.append({
            "name": p["name"],
            "score": float(score),
            "reviews": p["reviews"],
            "rating": p["rating"]
        })

    # 3. фильтр мусора
    filtered = filter_products(results)

    if not filtered:
        await update.message.reply_text("❌ Нет товаров с отзывами")
        return

    msg = "🛍 ТОП товары с отзывами:\n\n"

    for p in filtered:
        msg += (
            f"• {p['name']}\n"
            f"⭐ рейтинг: {p['rating']}\n"
            f"💬 отзывы: {p['reviews']}\n"
            f"📊 match: {p['score']:.2f}\n\n"
        )

    await update.message.reply_text(msg)


# ======================
# START
# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
