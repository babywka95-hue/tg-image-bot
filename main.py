import io
import logging
import torch
import clip
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ======================
# ВСТАВЬ СЮДА ТОКЕН
# ======================
TELEGRAM_TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"

logging.basicConfig(level=logging.INFO)

device = "cpu"

model, preprocess = clip.load("ViT-B/32", device=device)
model.eval()

PRODUCTS = [
    {"name": "wireless headphones black", "reviews": 120, "rating": 4.6},
    {"name": "iphone silicone case", "reviews": 0, "rating": 0},
    {"name": "nike running shoes", "reviews": 340, "rating": 4.8},
    {"name": "smart watch fitness", "reviews": 25, "rating": 4.3},
    {"name": "cheap sunglasses", "reviews": 0, "rating": 0},
    {"name": "travel backpack", "reviews": 89, "rating": 4.5},
]

with torch.no_grad():
    text_inputs = clip.tokenize([p["name"] for p in PRODUCTS]).to(device)
    text_features = model.encode_text(text_inputs)
    text_features = text_features / text_features.norm(dim=-1, keepdim=True)

def filter_products(items):
    return [p for p in items if p["reviews"] > 10 and p["rating"] > 0]

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Анализирую товар...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize((224, 224))

    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)
        probs = similarity.softmax(dim=0)

        top_k = torch.topk(probs, k=5)

    results = []

    for score, idx in zip(top_k.values, top_k.indices):
        p = PRODUCTS[idx]
        results.append({
            "name": p["name"],
            "reviews": p["reviews"],
            "rating": p["rating"],
            "score": float(score)
        })

    results = filter_products(results)

    if not results:
        await update.message.reply_text("❌ Нет товаров с отзывами")
        return

    msg = "🛍 ТОП товары:\n\n"

    for r in results:
        msg += (
            f"• {r['name']}\n"
            f"⭐ {r['rating']}\n"
            f"💬 {r['reviews']}\n"
            f"📊 match: {r['score']:.3f}\n\n"
        )

    await update.message.reply_text(msg)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
