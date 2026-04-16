import os
import io
import logging
import torch
import clip
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

# ======================
# AI MODEL (CLIP)
# ======================
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# ======================
# БАЗА ТОВАРОВ (потом заменим на WB)
# reviewCount имитируем
# ======================
PRODUCTS = [
    {"name": "wireless headphones black", "reviews": 120, "rating": 4.6},
    {"name": "iphone silicone case", "reviews": 0, "rating": 0},
    {"name": "nike running shoes", "reviews": 340, "rating": 4.8},
    {"name": "smart watch fitness", "reviews": 25, "rating": 4.3},
    {"name": "cheap sunglasses", "reviews": 0, "rating": 0},
    {"name": "travel backpack", "reviews": 89, "rating": 4.5},
]

text_inputs = clip.tokenize([p["name"] for p in PRODUCTS]).to(device)

with torch.no_grad():
    text_features = model.encode_text(text_inputs)
    text_features /= text_features.norm(dim=-1, keepdim=True)

# ======================
# FILTER (ОТЗЫВЫ)
# ======================
def filter_products(product_list):
    return [p for p in product_list if p["reviews"] > 0]

# ======================
# HANDLE PHOTO
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Анализирую товар...")

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)
        top_k = similarity.topk(5)

    results = []

    for score, idx in zip(top_k.values, top_k.indices):
        product = PRODUCTS[idx]

        results.append({
            "name": product["name"],
            "score": float(score),
            "reviews": product["reviews"],
            "rating": product["rating"]
        })

    # фильтр по отзывам
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
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
