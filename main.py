import logging
import io
import requests
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"

HF_API_URL = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"
HF_TOKEN = ""  # можно пустым (free tier работает, но медленнее)

logging.basicConfig(level=logging.INFO)

# ======================
# HF REQUEST
# ======================
def classify_image(image_bytes: bytes):
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    response = requests.post(
        HF_API_URL,
        headers=headers,
        data=image_bytes
    )

    if response.status_code != 200:
        return "unknown"

    data = response.json()

    # HF возвращает список классов
    if isinstance(data, list) and len(data) > 0:
        return data[0]["label"].lower()

    return "unknown"


# ======================
# MAP TO WB CATEGORY
# ======================
def map_to_category(label: str):
    label = label.lower()

    if any(x in label for x in ["phone", "mobile"]):
        return "phone"

    if any(x in label for x in ["headphone", "earphone", "speaker"]):
        return "audio"

    if any(x in label for x in ["shaver", "razor", "clipper"]):
        return "epilator"

    if any(x in label for x in ["watch"]):
        return "watch"

    if any(x in label for x in ["keyboard", "mouse", "computer"]):
        return "computer"

    return "general"


# ======================
# WB FAKE LINKS (потом заменишь API)
# ======================
PRODUCTS = {
    "epilator": [
        ("Эпилятор Braun Silk-epil", "https://www.wildberries.ru/"),
        ("Фотоэпилятор IPL", "https://www.wildberries.ru/"),
        ("Триммер женский", "https://www.wildberries.ru/")
    ],
    "audio": [
        ("Bluetooth наушники TWS", "https://www.wildberries.ru/"),
        ("Игровые наушники", "https://www.wildberries.ru/"),
        ("Портативная колонка", "https://www.wildberries.ru/")
    ],
    "phone": [
        ("Чехол iPhone", "https://www.wildberries.ru/"),
        ("PowerBank 20000", "https://www.wildberries.ru/"),
        ("Защитное стекло", "https://www.wildberries.ru/")
    ],
    "watch": [
        ("Смарт часы", "https://www.wildberries.ru/"),
        ("Фитнес браслет", "https://www.wildberries.ru/")
    ],
    "computer": [
        ("Игровая клавиатура", "https://www.wildberries.ru/"),
        ("Беспроводная мышь", "https://www.wildberries.ru/")
    ],
    "general": [
        ("Товар WB", "https://www.wildberries.ru/")
    ]
}


# ======================
# HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Анализирую фото...")

    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    # HF classify
    label = classify_image(image_bytes)

    category = map_to_category(label)
    items = PRODUCTS.get(category, PRODUCTS["general"])

    msg = f"🔍 AI определил: {label}\n"
    msg += f"📦 Категория: {category}\n\n"
    msg += "🛍 Похожие товары:\n\n"

    for name, link in items:
        msg += f"• {name}\n{link}\n\n"

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
