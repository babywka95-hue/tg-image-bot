import os
import io
import requests
from PIL import Image

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --------------------
# SAFE IMPORT torch + clip (ВАЖНО ДЛЯ RENDER)
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

    print("✅ CLIP loaded successfully")

except Exception as e:
    print("⚠️ CLIP disabled:", e)
    model = None
    preprocess = None
    device = "cpu"

# --------------------
def wb_search(query, limit=100):
    try:
        url = f"https://search.wb.ru/exactmatch/ru/common/v5/search"
        params = {"query": query, "page": 1, "limit": limit}

        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []

        data = r.json()
        return data.get("data", {}).get("products", [])

    except Exception as e:
        print("WB error:", e)
        return []

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

    avg_reviews = avg_reviews / total

    return {
        "total": total,
        "strong": strong,
        "ultra": ultra,
        "avg_reviews": avg_reviews
    }

# --------------------
def build_query_from_image(image_input):
    """
    CLIP → запрос (если CLIP есть)
    fallback → если нет CLIP
    """

    if model is None:
        return "product"

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
        2: "beauty",
        3: "clothing",
        4: "electronics",
        5: "goods"
    }

    return query_map.get(idx, "product")

# --------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()

        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        await update.message.reply_text("🔍 Анализируем товар...")

        image_input = None

        if preprocess is not None and model is not None:
            image_input = preprocess(image).unsqueeze(0).to(device)

        query = build_query_from_image(image_input)

        await update.message.reply_text(f"📦 Поиск WB: {query}")

        products = wb_search(query, limit=100)
        stats = analyze(products)

        if not stats:
            await update.message.reply_text("❌ Нет данных")
            return

        msg = (
            f"📊 АНАЛИЗ WB\n\n"
            f"📦 Товаров: {stats['total']}\n"
            f"💪 >300 отзывов: {stats['strong']}\n"
            f"🔥 >1000 отзывов: {stats['ultra']}\n"
            f"📈 Средние отзывы: {int(stats['avg_reviews'])}\n\n"
        )

        if stats["ultra"] > 5:
            msg += "🚫 Вход сложный"
        elif stats["strong"] > 10:
            msg += "🟡 Средняя конкуренция"
        else:
            msg += "🟢 Можно заходить"

        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        print("handler error:", e)

# --------------------
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
