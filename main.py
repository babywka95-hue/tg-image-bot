import os
import io
import requests
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise Exception("TELEGRAM_TOKEN не задан")

# --------------------
def wb_search(query, limit=100):
    url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
    params = {"query": query, "page": 1, "limit": limit}

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return data.get("data", {}).get("products", [])
    except Exception as e:
        print("WB error:", e)
        return []

# --------------------
def analyze(products):
    if not products:
        return None

    total = len(products)
    strong = 0
    ultra = 0
    avg = 0

    for p in products:
        f = p.get("feedbacks", 0) or 0
        avg += f

        if f > 300:
            strong += 1
        if f > 1000:
            ultra += 1

    avg = avg / total if total else 0

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
        "avg": avg
    }

# --------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Анализ товара...")

    # 👉 пока используем универсальный запрос
    query = "товар"

    products = wb_search(query)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("❌ Нет данных")
        return

    msg = (
        f"📊 АНАЛИЗ WB\n\n"
        f"📦 Товаров: {stats['total']}\n"
        f"💪 >300 отзывов: {stats['strong']}\n"
        f"🔥 >1000 отзывов: {stats['ultra']}\n"
        f"📈 Средние отзывы: {int(stats['avg'])}\n\n"
    )

    if stats["ultra"] > 5:
        msg += "🚫 Вход сложный"
    elif stats["strong"] > 10:
        msg += "🟡 Средняя конкуренция"
    else:
        msg += "🟢 Можно заходить"

    await update.message.reply_text(msg)

# --------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
