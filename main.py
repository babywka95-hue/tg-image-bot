import os
import io
import logging

import torch
import clip
from PIL import Image
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# LOGGING
# =========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

print("🔥 MAIN STARTED")

# =========================
# ENV
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN is NOT set")

PORT = int(os.getenv("PORT", "8080"))

# =========================
# DEVICE
# =========================
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info("Device: %s", device)

# =========================
# LAZY LOAD MODEL
# =========================
model = None
preprocess = None
text_features = None

PRODUCTS = [
    ("wireless headphones", "https://wildberries.ru"),
    ("electric shaver epilator", "https://wildberries.ru"),
    ("smartphone", "https://wildberries.ru"),
    ("power bank", "https://wildberries.ru"),
    ("smart watch", "https://wildberries.ru"),
    ("backpack", "https://wildberries.ru"),
]


def load_model():
    global model, preprocess, text_features

    if model is not None:
        return

    logger.info("🔥 Loading CLIP model...")

    model_loaded, preprocess_loaded = clip.load("ViT-B/32", device=device)
    model_loaded = model_loaded.float()

    text_inputs = clip.tokenize([p[0] for p in PRODUCTS]).to(device)

    with torch.no_grad():
        tf = model_loaded.encode_text(text_inputs)
        tf = tf / tf.norm(dim=-1, keepdim=True)

    model = model_loaded
    preprocess = preprocess_loaded
    text_features = tf

    logger.info("✅ CLIP loaded")


# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 👋\n\nОтправь фото товара, и я найду похожие товары."
    )


# =========================
# PHOTO HANDLER
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    await update.message.reply_text("📸 Анализирую фото...")

    # Загружаем модель только при первом фото
    load_model()

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    image_bytes = await file.download_as_bytearray()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features = image_features / image_features.norm(
            dim=-1, keepdim=True
        )

        similarity = (image_features @ text_features.T).squeeze(0)
        top_k = similarity.topk(3)

    msg = "🛍 Похожие товары:\n\n"

    for score, idx in zip(top_k.values, top_k.indices):
        name, url = PRODUCTS[int(idx)]
        msg += (
            f"• {name}\n"
            f"{url}\n"
            f"📊 match: {float(score):.2f}\n\n"
        )

    await update.message.reply_text(msg)


# =========================
# MAIN
# =========================
def main():
    logger.info("🚀 BOT RUNNING (polling mode)")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
