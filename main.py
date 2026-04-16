import logging
import io
import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"

logging.basicConfig(level=logging.INFO)

# ======================
# YANDEX IMAGE SEARCH
# ======================
def yandex_reverse_search(image_bytes: bytes):
    """
    Отправляем картинку в Яндекс reverse search
    """

    files = {
        "upfile": ("image.jpg", image_bytes, "image/jpeg")
    }

    params = {
        "rpt": "imageview",
        "format": "json",
        "request": "search",
        "cbir": "1"
    }

    url = "https://yandex.ru/images/search"

    response = requests.post(url, params=params, files=files, headers={
        "User-Agent": "Mozilla/5.0"
    })

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "lxml")

    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "http" in href and "yandex" not in href:
            links.append(href)

    # убираем дубликаты
    return list(dict.fromkeys(links))[:5]


# ======================
# ANALYZE TEXT (простая логика)
# ======================
def extract_type_from_text(text):
    text = text.lower()

    if any(x in text for x in ["shaver", "epilator", "razor"]):
        return "Эпилятор / бритва"

    if any(x in text for x in ["phone", "iphone", "smartphone"]):
        return "Телефон"

    if any(x in text for x in ["headphone", "airpods"]):
        return "Наушники"

    if any(x in text for x in ["watch"]):
        return "Часы"

    return "Электроника / товар"


# ======================
# HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Анализирую через Яндекс...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    links = yandex_reverse_search(image_bytes)

    if not links:
        await update.message.reply_text("❌ Не удалось найти похожие товары")
        return

    msg = "🔍 Похожие товары (Яндекс):\n\n"

    for i, link in enumerate(links, 1):
        msg += f"{i}. {link}\n"

    await update.message.reply_text(msg)


# ======================
# START BOT
# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
