import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# =========================
# 1. ВЫТАСКИВАЕМ ТЕГИ ИЗ ФОТО (БЕЗ AI)
# =========================
def fake_image_understanding():
    # пока без ML — стабильно
    return "shopping item"

# =========================
# 2. WB SEARCH
# =========================
def wb_search(query):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
        params = {"query": query, "resultset": "catalog", "limit": 5}
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()

        products = data.get("data", {}).get("products", [])

        results = []
        for p in products:
            results.append({
                "name": p.get("name"),
                "price": p.get("salePriceU", 0) // 100,
                "link": f"https://www.wildberries.ru/catalog/{p['id']}/detail.aspx"
            })

        return results

    except Exception as e:
        print("WB ERROR:", e)
        return []

# =========================
# HANDLER
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    await update.message.reply_text("🔍 Анализирую фото...")

    # ⚡ пока без CLIP (стабильно)
    query = fake_image_understanding()

    await update.message.reply_text("🧠 Ищу похожие товары...")

    products = wb_search(query)

    if not products:
        await update.message.reply_text("❌ Ничего не найдено")
        return

    msg = "🛍 Найденные товары:\n\n"

    for p in products:
        msg += f"• {p['name']}\n💰 {p['price']} ₽\n🔗 {p['link']}\n\n"

    await update.message.reply_text(msg[:4000])

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
