import os
import io
import requests
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise Exception("TELEGRAM_TOKEN не задан в Environment")

# --------------------
torch = None
clip = None
model = None
preprocess = None
device = "cpu"

try:
    import torch as _torch
    import clip as _clip

    torch = _torch
    clip = _clip

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)

    print("CLIP loaded")

except Exception as e:
    print("CLIP disabled:", e)

# --------------------
def wb_search(query, limit=100):
    url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
    params = {"query": query, "page": 1, "limit": limit}

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return data.get("data", {}).get("products", [])
    except:
        return []

# --------------------
def analyze(products):
    if not products:
        return None

    strong = 0
    ultra = 0
    total = len(products)
    avg = 0

    for p in products:
        f = p.get("feedbacks", 0) or 0
        avg += f

        if f > 300:
            strong += 1
        if f > 1000:
            ultra += 1

    avg = avg / total if total else 0

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
        "avg": avg
    }

# --------------------
def build_query(image_input):
    if model is None:
        return "product"

    prompts = [
        "product", "home item", "beauty product",
        "clothing item", "electronics", "consumer goods"
    ]

    with torch.no_grad():
        text = clip.tokenize(prompts).to(device)
        t = model.encode_text(text)
        t /= t.norm(dim=-1, keepdim=True)

        i = model.encode_image(image_input)
        i /= i.norm(dim=-1, keepdim=True)

        sim = (i @ t.T).squeeze(0)
        return prompts[sim.argmax().item()]

# --------------------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(img)).convert("RGB")

    await update.message.reply_text("Анализ...")

    image_input = None
    if model and preprocess:
        image_input = preprocess(image).unsqueeze(0).to(device)

    query = build_query(image_input)

    products = wb_search(query)
    stats = analyze(products)

    if not stats:
        await update.message.reply_text("Нет данных")
        return

    msg = (
        f"Товаров: {stats['total']}\n"
        f">300 отзывов: {stats['strong']}\n"
        f">1000 отзывов: {stats['ultra']}\n"
        f"Средние: {int(stats['avg'])}\n"
    )

    await update.message.reply_text(msg)

# --------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handler))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
