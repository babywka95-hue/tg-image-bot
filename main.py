import os
import io
import json
import requests
from PIL import Image
import torch
import clip

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ----------------------
TELEGRAM_TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# ----------------------
CATEGORIES = [
    "epilator",
    "hair dryer",
    "sneakers",
    "smart watch",
    "backpack",
    "headphones"
]

# ----------------------
def wb_mobile_search(query, limit=20):
    """
    Парсинг мобильной версии WB.
    JSON содержит реальные отзывы и рейтинг.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json"
    }

    url = f"https://search.wb.ru/exactmatch/ru/m/catalog?query={query}&page=1&limit={limit}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        products = []

        for item in data.get("data", {}).get("products", []):
            feedbacks = item.get("feedbacks", 0)
            rating = item.get("rating", 0)
            if feedbacks is None: feedbacks = 0
            if rating is None: rating = 0

            products.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "price": item.get("salePriceU", 0)/100,
                "reviews": feedbacks,
                "rating": rating,
                "link": f"https://www.wildberries.ru/catalog/{item.get('id')}/detail.aspx"
            })

        return products
    except Exception as e:
        print("WB mobile search error:", e)
        return []

# ----------------------
def filter_products(products):
    filtered = [p for p in products if p["reviews"] > 0 and p["rating"] >= 4.0]
    filtered.sort(key=lambda x: (x["rating"], x["reviews"]), reverse=True)
    return filtered

# ----------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Анализирую фото...")

    with torch.no_grad():
        text_inputs = clip.tokenize(CATEGORIES).to(device)
        text_features = model.encode_text(text_inputs)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)
        idx = similarity.argmax().item()
        query = CATEGORIES[idx]

    await update.message.reply_text(f"🔑 Категория: {query}")

    products = wb_mobile_search(query, limit=20)
    products = filter_products(products)

    if not products:
        await update.message.reply_text("❌ Нет товаров с рейтингом ≥4 и отзывами ≥1")
        return

    msg = "🛍 ТОП товаров WB:\n\n"
    for p in products[:5]:
        msg += f"• {p['name']}\n"
        msg += f"⭐ Рейтинг: {p['rating']} | 💬 Отзывы: {p['reviews']}\n"
        msg += f"💰 {p['price']} ₽\n"
        msg += f"🔗 {p['link']}\n\n"

    await update.message.reply_text(msg)

# ----------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
