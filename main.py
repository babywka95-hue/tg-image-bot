import os
import io
import requests
import torch
import clip
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ======================
TELEGRAM_TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# ======================
# CLIP categories
# ======================
CATEGORIES = [
    "epilator",
    "hair dryer",
    "sneakers",
    "smart watch",
    "backpack",
    "headphones"
]

# ======================
# WB SEARCH (WORKING API)
# ======================
def wb_search(query, limit=10):
    url = (
        "https://search.wb.ru/exactmatch/ru/common/v5/search"
        f"?query={query}&page=1&limit={limit}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    r = requests.get(url, headers=headers, timeout=10)

    if r.status_code != 200:
        return []

    try:
        data = r.json()
    except:
        return []

    products = []

    for item in data.get("data", {}).get("products", []):
        products.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "price": item.get("salePriceU", 0) / 100,
            "rating": item.get("reviewRating", 0),
            "reviews": item.get("feedbacks", 0),
            "link": f"https://www.wildberries.ru/catalog/{item.get('id')}/detail.aspx"
        })

    return products

# ======================
def filter_products(products):
    res = []

    for p in products:
        if p["reviews"] is None or p["reviews"] <= 0:
            continue
        if p["rating"] is None or p["rating"] < 4.0:
            continue
        res.append(p)

    return sorted(res, key=lambda x: (x["rating"], x["reviews"]), reverse=True)

# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Анализирую фото...")

    with torch.no_grad():
        text = clip.tokenize(CATEGORIES).to(device)
        text_features = model.encode_text(text)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        scores = (image_features @ text_features.T).squeeze(0)
        idx = scores.argmax().item()

        query = CATEGORIES[idx]

    await update.message.reply_text(f"🔎 Категория: {query}")

    products = wb_search(query, limit=20)
    products = filter_products(products)

    if not products:
        await update.message.reply_text("❌ Нет товаров с рейтингом ≥ 4.0 и отзывами")
        return

    msg = "🛍 ТОП товаров WB:\n\n"

    for p in products[:5]:
        msg += f"• {p['name']}\n"
        msg += f"⭐ {p['rating']} | 💬 {p['reviews']}\n"
        msg += f"💰 {p['price']} ₽\n"
        msg += f"🔗 {p['link']}\n\n"

    await update.message.reply_text(msg)

# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
