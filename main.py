import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from PIL import Image
import io

import torch
import clip

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

# ======================
# LOAD AI MODEL (CLIP)
# ======================

device = "cpu"  # ⚠️ ВАЖНО: Render = CPU (иначе OOM / падения)

model, preprocess = clip.load("ViT-B/32", device=device)

# тестовая база товаров
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
    text_features /= text_features.norm(dim=-1, keepdim=True)


# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Анализирую товар...")

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)

        top_k = similarity.topk(3)

    msg = "🛍 Похожие товары:\n\n"

    for score, idx in zip(top_k.values, top_k.indices):
        msg += f"• {PRODUCTS[idx]} (match {score.item():.2f})\n"

    await update.message.reply_text(msg)


# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
