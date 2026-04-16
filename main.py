import os
import io
import logging
import requests
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# -------------------------
# 1. "AI" (ЗАГЛУШКА СЕЙЧАС)
# потом заменим на Yandex Vision
# -------------------------
def classify_image(image_bytes):
    # временно: просто возвращаем универсальную категорию
    return "epilator"

# -------------------------
# 2. ПОИСК (1688 MOCK / потом API)
# -------------------------
def search_products(query):
    # тут потом подключим 1688 / scraping / API
    return [
        {"name": "Philips epilator BRE700", "price": 55, "rating": 4.8, "reviews": 1240, "url": "https://example.com/1"},
        {"name": "cheap epilator no brand", "price": 10, "rating": 3.2, "reviews": 0, "url": "https://example.com/2"},
        {"name": "Braun Silk Epil 9", "price": 80, "rating": 4.7, "reviews": 980, "url": "https://example.com/3"},
    ]

# -------------------------
# 3. ФИЛЬТР МУСОРА
# -------------------------
def is_good(p):
    return (
        p.get("price", 0) > 0 and
        p.get("rating", 0) >= 4.0 and
        p.get("reviews", 0) >= 10
    )

# -------------------------
# 4. SCORE
# -------------------------
def score(p):
    return (
        (p["rating"] / 5) * 0.5 +
        min(p["reviews"] / 1000, 1) * 0.5
    )

# -------------------------
# HANDLER
# -------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    await update.message.reply_text("🔍 Анализирую товар...")

    category = classify_image(image_bytes)
    products = search_products(category)

    good = [p for p in products if is_good(p)]

    if not good:
        await update.message.reply_text("❌ Ничего качественного не найдено")
        return

    ranked = sorted(good, key=score, reverse=True)

    msg = "🛍 ТОП товары:\n\n"

    for p in ranked[:5]:
        msg += (
            f"• {p['name']}\n"
            f"⭐ {p['rating']} | 💬 {p['reviews']}\n"
            f"💰 {p['price']}$\n"
            f"🔗 {p['url']}\n\n"
        )

    await update.message.reply_text(msg)

# -------------------------
# MAIN
# -------------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("BOT STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
