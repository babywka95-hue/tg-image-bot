import os
import io
import logging
from PIL import Image

import torch
import clip

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN is NOT set")

BASE_URL = "https://tg-image-bot-production-aa33.up.railway.app"

print("🔥 BOT STARTING...")

# =========================
# LOAD CLIP
# =========================
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

model, preprocess = clip.load("ViT-B/32", device=device)
model = model.float()

print("✅ CLIP LOADED")

# =========================
# PRODUCTS
# =========================
PRODUCTS = [
    ("wireless headphones", "https://wildberries.ru"),
    ("electric shaver epilator", "https://wildberries.ru"),
    ("smartphone", "https://wildberries.ru"),
    ("power bank", "https://wildberries.ru"),
    ("smart watch", "https://wildberries.ru"),
    ("backpack", "https://wildberries.ru"),
]

text_inputs = clip.tokenize([p[0] for p in PRODUCTS]).to(device)

with torch.no_grad():
    text_features = model.encode_text(text_inputs)
    text_features /= text_features.norm(dim=-1, keepdim=True)

print("✅ TEXT FEATURES READY")

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Бот работает.\n\n"
        "Отправь фото товара — найду похожие позиции."
    )

# =========================
# PHOTO HANDLER
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.photo:
            return

        await update.message.reply_text("📸 Анализирую фото...")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        image_bytes = await file.download_as_bytearray()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        image_input = preprocess(image).unsqueeze(0).to(device)

        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).squeeze(0)
            top_k = similarity.topk(3)

        msg = "🛍 Похожие товары:\n\n"

        for score, idx in zip(top_k.values, top_k.indices):
            name, url = PRODUCTS[int(idx)]
            msg += f"• {name}\n{url}\n📊 match: {float(score):.2f}\n\n"

        await update.message.reply_text(msg)

    except Exception as e:
        logging.exception(e)
        await update.message.reply_text("❌ Ошибка обработки фото")

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 RUNNING WEBHOOK")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{BASE_URL}/{TOKEN}",
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
