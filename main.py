import os
import io
import json
import logging
import requests
from PIL import Image
import torch
import clip

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")
logging.basicConfig(level=logging.INFO)

# ======================
# LOAD CLIP MODEL
# ======================
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# ======================
# WB PARSER
# ======================
def search_wb(query, limit=20):
    """Парсинг Wildberries карточек по ключевому слову"""
    headers = {"User-Agent": "Mozilla/5.0"}
    # Публичный поиск через JSON выдачу
    url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={query}&page=1&count={limit}"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        products = []
        for item in data.get("data", {}).get("products", []):
            products.append({
                "name": item.get("name"),
                "price": item.get("salePriceU") / 100 if item.get("salePriceU") else None,
                "reviews": item.get("feedbacks") or 0,
                "rating": item.get("rating") or 0,
                "link": f"https://www.wildberries.ru/catalog/{item.get('id')}/detail.aspx"
            })
        return products
    except Exception as e:
        print("WB parse error:", e)
        return []

# ======================
# ФИЛЬТР
# ======================
def filter_products(products):
    filtered = []
    for p in products:
        if not p["name"]:
            continue
        if p["reviews"] <= 0:
            continue
        if p["rating"] <= 0:
            continue
        if p["rating"] < 4.0:
            continue
        filtered.append(p)
    filtered.sort(key=lambda x: (x["rating"], x["reviews"]), reverse=True)
    return filtered

# ======================
# PHOTO HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Определяю категорию товара...")

    # CLIP: определяем категорию
    categories = ["epilator", "hair dryer", "sneakers", "smart watch", "backpack", "headphones"]
    text_inputs = clip.tokenize(categories).to(device)

    with torch.no_grad():
        text_features = model.encode_text(text_inputs)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)
        top_idx = similarity.argmax().item()
        query = categories[top_idx]

    await update.message.reply_text(f"🔑 Ключевое слово: {query}")

    # WB поиск
    products = search_wb(query, limit=20)
    products = filter_products(products)

    if not products:
        await update.message.reply_text("❌ Нет товаров с отзывами и рейтингом ≥ 4.0")
        return

    # Вывод топ 5 товаров
    msg = "🛍 ТОП товаров WB:\n\n"
    for p in products[:5]:
        msg += f"• {p['name']}\n"
        msg += f"⭐ Рейтинг: {p['rating']}, 💬 Отзывы: {p['reviews']}\n"
        msg += f"💰 Цена: {p['price']}₽\n"
        msg += f"🔗 {p['link']}\n\n"

    await update.message.reply_text(msg)

# ======================
# MAIN
# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
