import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ==========================================
# TOKEN
# ==========================================
TELEGRAM_TOKEN = "8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo"

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==========================================
# ФЕЙК БАЗА ПОХОЖИХ ТОВАРОВ
# Можно потом заменить на WB API / Parser
# ==========================================
PRODUCTS = {
    "эпилятор": [
        ("Эпилятор Braun Silk-epil 9", "https://www.wildberries.ru/"),
        ("Фотоэпилятор IPL домашний", "https://www.wildberries.ru/"),
        ("Женский триммер для тела", "https://www.wildberries.ru/")
    ],
    "наушники": [
        ("Беспроводные наушники TWS", "https://www.wildberries.ru/"),
        ("Игровая гарнитура RGB", "https://www.wildberries.ru/"),
        ("Bluetooth гарнитура", "https://www.wildberries.ru/")
    ],
    "часы": [
        ("Смарт часы AMOLED", "https://www.wildberries.ru/"),
        ("Фитнес браслет", "https://www.wildberries.ru/"),
        ("Умные часы спортивные", "https://www.wildberries.ru/")
    ],
    "телефон": [
        ("Чехол для iPhone", "https://www.wildberries.ru/"),
        ("PowerBank 20000mah", "https://www.wildberries.ru/"),
        ("Защитное стекло", "https://www.wildberries.ru/")
    ]
}

# ==========================================
# УМНОЕ ОПРЕДЕЛЕНИЕ ПО ПОДПИСИ/ТЕКСТУ
# ==========================================
def detect_product(caption: str):
    if not caption:
        return "телефон"

    text = caption.lower()

    if "эпил" in text or "бритв" in text:
        return "эпилятор"

    if "науш" in text or "airpods" in text:
        return "наушники"

    if "час" in text or "watch" in text:
        return "часы"

    return "телефон"

# ==========================================
# PHOTO HANDLER
# ==========================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Фото получено. Анализирую...")

    caption = update.message.caption if update.message.caption else ""

    category = detect_product(caption)
    items = PRODUCTS.get(category, [])

    msg = f"🔍 Определен товар: {category}\n\n"
    msg += "🛍 Похожие товары:\n\n"

    for name, link in items:
        msg += f"• {name}\n{link}\n\n"

    await update.message.reply_text(msg)

# ==========================================
# START
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 👋\n"
        "Отправь фото товара.\n"
        "Если хочешь точнее анализ — подпиши фото:\n"
        "Например: эпилятор / наушники / часы"
    )

# ==========================================
# MAIN
# ==========================================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
