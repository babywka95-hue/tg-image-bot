import os
import logging
import requests
import torch
import clip
import io

from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

# ======================
# CLIP MODEL
# ======================
device = "cpu"  # ⚠️ важно для Render (иначе OOM)
model, preprocess = clip.load("ViT-B/32", device=device)

# ======================
# WB SEARCH (реальная база)
# ======================
def wb_search(query):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"

        params = {
            "query": query,
            "resultset": "catalog",
            "limit": 5
        }

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()

        products = data.get("data", {}).get("products", [])

        results = []

        for p in products:
            pid = p["id"]
            name = p["name"]
            price = p.get("salePriceU", 0) // 100

            link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

            results.append({
                "name": name,
                "price": price,
                "link": link
            })

        return results

    except Exception as e:
        print("WB ERROR:", e)
        return []

# ======================
# CLIP + WB SMART MATCH
# ======================
def clip_smart_query(image):
    """CLIP превращает фото → текстовый запрос"""

    prompts = [
        "epilator",
        "women dress",
        "smartphone",
        "headphones",
        "watch",
        "shoes",
        "bag",
        "cosmetics",
        "kitchen appliance",
        "hair dryer"
    ]

    text_tokens = clip.tokenize(prompts).to(device)

    with torch.no_grad():
        image_input = preprocess(image).unsqueeze(0).to(device)

        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        text_features = model.encode_text(text_tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)

        best_idx = similarity.argmax().item()

        return prompts[best_idx]

# ======================
# HANDLER
# ======================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    await update.message.reply_text("🔍 Анализирую фото...")

    # CLIP → категория
    query = clip_smart_query(image)

    await update.message.reply_text(f"🧠 Понял: {query}")

    # WB search
    products = wb_search(query)

    if not products:
        await update.message.reply_text("❌ Ничего не найдено")
        return

    msg = "🛍 Похожие товары:\n\n"

    for p in products:
        msg += f"• {p['name']}\n💰 {p['price']} ₽\n🔗 {p['link']}\n\n"

    await update.message.reply_text(msg[:4000])

# ======================
# MAIN
# ======================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
