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
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN is NOT set")

logging.basicConfig(level=logging.INFO)

print("🔥 BOT STARTED")

# ======================
# MODEL (CLIP)
# ======================
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# ======================
# SIMPLE PRODUCT DB (замени потом на WB API)
# ======================
PRODUCTS = [
    {"name": "wireless headphones", "url": "https://wildberries.ru", "score_boost": 1.0},
    {"name": "electric shaver epilator", "url": "https://wildberries.ru", "score_boost": 1.2},
    {"name": "smartphone", "url": "https://wildberries.ru", "score_boost": 1.0},
    {"name": "power bank", "url": "https://wildberries.ru", "score_boost": 1.0},
    {"name": "smart watch", "url": "https://wildberries.ru", "score_boost": 1.0},
    {"name": "backpack", "url": "https://wildberries.ru", "score_boost": 1.0},
]

text_inputs = clip.tokenize([p["name"] for p in PRODUCTS]).to(device)

with torch.no_grad():
    text_features = model.encode_text(text_inputs)
    text_features /= text_features.norm(dim=-1, keepdim=True)

# ======================
# FILTER (убираем мусор)
# ======================
def is_valid_product(name: str) -> bool:
    bad = ["unknown", "general", "thing", "object"]
    return not any(b in name.lower() for b in bad)

# ======================
# PHOTO HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    image_bytes = await file.download_as_bytearray()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    await update.message.reply_text("📸 Анализирую фото...")

    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)

        top_k = similarity.topk(3)

    results = []
    for score, idx in zip(top_k.values, top_k.indices):
        product = PRODUCTS[idx]

        if not is_valid_product(product["name"]):
            continue

        final_score = float(score) * product["score_boost"]

        results.append({
            "name": product["name"],
            "url": product["url"],
            "score": final_score
        })

    if not results:
        await update.message.reply_text("❌ Не удалось определить товар")
        return

    # ======================
    # RESPONSE
    # ======================
    msg = "🛍 Похожие товары:\n\n"

    for r in results:
        msg += f"• {r['name']}\n{r['url']}\n📊 match: {r['score']:.2f}\n\n"

    await update.message.reply_text(msg)

# ======================
# START BOT
# ======================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
