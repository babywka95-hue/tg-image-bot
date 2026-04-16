import logging
import io
from PIL import Image

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# =====================================
# TOKEN
# =====================================
TELEGRAM_TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"

# =====================================
# LOGGING
# =====================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# =====================================
# БАЗА ТОВАРОВ ПО КАТЕГОРИЯМ
# =====================================
PRODUCTS = {
    "audio": [
        "Беспроводные наушники TWS",
        "Bluetooth колонка",
        "Игровая гарнитура",
    ],
    "phone": [
        "Чехол для iPhone",
        "Защитное стекло",
        "Power Bank 20000 mAh",
    ],
    "computer": [
        "Игровая клавиатура",
        "Беспроводная мышь",
        "USB Hub",
    ],
    "wearable": [
        "Смарт часы",
        "Фитнес браслет",
        "Умное кольцо",
    ],
    "home": [
        "LED лампа",
        "Ночник",
        "Увлажнитель воздуха",
    ],
    "fashion": [
        "Рюкзак городской",
        "Худи оверсайз",
        "Солнцезащитные очки",
    ],
}

# =====================================
# ОПРЕДЕЛЕНИЕ ТОВАРА ПО ИЗОБРАЖЕНИЮ
# (лёгкая версия без AI, стабильная)
# =====================================
def detect_category(image: Image.Image):
    width, height = image.size
    ratio = width / height if height else 1

    # Цветовая статистика
    small = image.resize((50, 50)).convert("RGB")
    pixels = list(small.getdata())

    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)

    brightness = (avg_r + avg_g + avg_b) / 3

    # Простейшая эвристика
    if ratio > 1.3:
        return "computer"
    elif brightness < 70:
        return "audio"
    elif avg_b > avg_r and avg_b > avg_g:
        return "phone"
    elif brightness > 190:
        return "home"
    elif ratio < 0.8:
        return "wearable"
    else:
        return "fashion"

# =====================================
# /start
# =====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Отправь фото товара.\n"
        "Я попробую определить категорию и подобрать похожие товары."
    )

# =====================================
# PHOTO HANDLER
# =====================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("📸 Фото получено. Анализирую...")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        category = detect_category(image)
        items = PRODUCTS.get(category, [])

        msg = "🔍 Похоже это товар из категории:\n"
        msg += f"👉 {category.upper()}\n\n"
        msg += "🛍 Похожие товары:\n\n"

        for item in items:
            msg += f"• {item}\n"

        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка обработки фото: {e}")

# =====================================
# MAIN
# =====================================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
