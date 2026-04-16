import os
import io
import logging

import torch
import clip
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

# ======================
# SAFE DEVICE (ВАЖНО ДЛЯ RENDER)
# ======================
device = "cpu"  # ⚠️ фиксируем CPU, чтобы не было OOM на GPU попытке

# ======================
# LOAD CLIP (с защитой)
# ======================
try:
    model, preprocess = clip.load("ViT-B/32", device=device)
    model.eval()
except Exception as e:
    print("CLIP load error:", e)
    raise e

# ======================
# PRODUCTS (как вчера)
# ======================
PRODUCTS = [
    "wireless headphones black",
    "iphone case silicone",
    "nike running shoes",
    "smart watch sport",
    "backpack travel bag",
    "sunglasses fashion"
]

text_inputs = clip.tokenize(PRODUCTS).to(device)

with torch.no_grad():
    text_features = model.encode_text(text_inputs)
    text_features = text_features / text_features.norm(dim=-1, keepdim=True)

# ======================
# PHOTO HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]

        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_input = preprocess(image).unsqueeze(0).to(device)

        await update.message.reply_text("🔍 Анализирую товар...")

        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).squeeze(0)
            top_k = similarity.topk(3)

        msg = "🛍 Похожие товары:\n\n"

        for score, idx in zip(top_k.values, top_k.indices):
            msg += f"• {PRODUCTS[idx]} (match {score.item():.2f})\n"

        await update.message.reply_text(msg)

    except Exception as e:
        logging.exception(e)
        await update.message.reply_text("❌ Ошибка обработки изображения")

# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
