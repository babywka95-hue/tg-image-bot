import os
import io
import requests
import torch
import clip
from PIL import Image

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# --------------------
TOKEN = os.getenv("BOT_TOKEN")
URL = os.getenv("PUBLIC_URL")
PORT = int(os.getenv("PORT", "10000"))

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")

if not URL:
    raise Exception("PUBLIC_URL is missing")


# --------------------
# CLIP INIT (CPU safe)
# --------------------
device = "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)


# --------------------
# WB SEARCH
# --------------------
def wb_search(query, limit=100):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}&page=1&limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        return []

    data = r.json()
    return data.get("data", {}).get("products", [])


# --------------------
# ANALYZE COMPETITION (ВАШ ФИЛЬТР СОХРАНЁН)
# --------------------
def analyze(products):
    if not products:
        return None

    total = len(products)
    strong = 0
    ultra = 0
    avg_reviews = 0

    for p in products:
        r = p.get("feedbacks", 0) or 0
        avg_reviews += r

        if r > 300:
            strong += 1
        if r > 1000:
            ultra += 1

    avg_reviews = avg_reviews / total if total else 0

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
        "avg_reviews": avg_reviews
    }


# --------------------
# CLIP → QUERY
# --------------------
def build_query_from_image(image_input):
    prompts = [
        "a product sold online",
        "a household item",
        "a beauty product",
        "a fashion item",
        "a tech gadget",
        "a small consumer product"
    ]

    with torch.no_grad():
        text = clip.tokenize(prompts).to(device)
        text_f = model.encode_text(text)
        text_f /= text_f.norm(dim=-1, keepdim=True)

        img_f = model.encode_image(image_input)
        img_f /= img_f.norm(dim=-1, keepdim=True)

        sim = (img_f @ text_f.T).squeeze(0)
        idx = sim.argmax().item()

    query_map = {
        0: "product",
        1: "home goods",
        2: "beauty care",
        3: "clothing",
        4: "electronics",
        5: "consumer goods"
    }

    return query_map[idx]


# --------------------
# HANDLER
# --------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Анализ товара...")

    query = build_query_from_image(image_input)

    await update.message.reply_text(f"📦 Поиск WB: {query}")

    products = wb_search(query, limit=100)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("❌ Нет данных")
        return

    msg = (
        f"📊 АНАЛИЗ WB ТОВАРА\n\n"
        f"📦 Товаров: {stats['total']}\n"
        f"💪 >300 отзывов: {stats['strong']}\n"
        f"🔥 >1000 отзывов: {stats['ultra']}\n"
        f"📈 Средние отзывы: {int(stats['avg_reviews'])}\n\n"
    )

    if stats["ultra"] > 5:
        msg += "🚫 ВХОД ОЧЕНЬ СЛОЖНЫЙ"
    elif stats["strong"] > 10:
        msg += "🟡 СРЕДНЯЯ КОНКУРЕНЦИЯ"
    else:
        msg += "🟢 МОЖНО ЗАХОДИТЬ"

    await update.message.reply_text(msg)


# --------------------
# WEBHOOK (Render FIXED)
# --------------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=f"{URL}/webhook",
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
