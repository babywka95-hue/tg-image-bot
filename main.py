import os
import io
import logging

import clip
import torch
from PIL import Image
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ======================
# LOGGING
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ======================
# ENV
# ======================
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN is NOT set")

PORT = int(os.getenv("PORT", "8080"))


def resolve_webhook_url():
    explicit = os.getenv("WEBHOOK_URL")
    if explicit:
        return explicit.rstrip("/")

    railway_static = os.getenv("RAILWAY_STATIC_URL")
    if railway_static:
        if railway_static.startswith("http"):
            return railway_static.rstrip("/")
        return f"https://{railway_static.strip('/')}"

    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if railway_domain:
        return f"https://{railway_domain.strip('/')}"

    return None


WEBHOOK_URL = resolve_webhook_url()

# ======================
# MODEL
# ======================
logger.info("🔥 BOT STARTED")

device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info("Device: %s", device)

model, preprocess = clip.load("ViT-B/32", device=device)
model = model.float()

# ======================
# PRODUCTS
# ======================
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
    text_features = text_features / text_features.norm(dim=-1, keepdim=True)


# ======================
# HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь фото товара, и я найду похожие 🛍"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    image_bytes = await file.download_as_bytearray()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    await update.message.reply_text("📸 Анализирую фото...")

    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)
        top_k = similarity.topk(3)

    msg = "🛍 Похожие товары:\n\n"

    for score, idx in zip(top_k.values, top_k.indices):
        name, url = PRODUCTS[int(idx)]
        msg += f"• {name}\n{url}\n📊 match: {float(score):.2f}\n\n"

    await update.message.reply_text(msg)


# ======================
# MAIN
# ======================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    if WEBHOOK_URL:
        logger.info("🚀 RUNNING WEBHOOK MODE")
        logger.info("Webhook: %s/%s", WEBHOOK_URL, TOKEN)

        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
            drop_pending_updates=True,
        )
    else:
        logger.info("🚀 RUNNING POLLING MODE")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
