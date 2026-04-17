import os
import io
import logging
import torch
import os

import clip
import torch
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
print("🔥 NEW CODE VERSION 3 RUNNING")
TOKEN = os.getenv("TELEGRAM_TOKEN")
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN is NOT set")

logging.basicConfig(level=logging.INFO)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8080"))

print("🔥 BOT STARTED")
logger.info("🔥 BOT STARTED")

# Railway обычно работает в CPU-контейнере, поэтому оставляем авто-выбор.
device = "cuda" if torch.cuda.is_available() else "cpu"

model, preprocess = clip.load("ViT-B/32", device=device)
model = model.float()

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
        name, url = PRODUCTS[idx]
        name, url = PRODUCTS[int(idx)]
        msg += f"• {name}\n{url}\n📊 match: {float(score):.2f}\n\n"

    await update.message.reply_text(msg)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 RUNNING")
    app.run_polling()
    if WEBHOOK_URL:
        logger.info("🚀 RUNNING (webhook mode on port %s)", PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}",
            drop_pending_updates=True,
        )
    else:
        logger.info("🚀 RUNNING (polling mode)")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
