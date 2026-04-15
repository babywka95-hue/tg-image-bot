import os
import io
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# =====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # можно не ставить

# =====================
def wb_search(query, limit=10):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
        params = {
            "query": query,
            "page": 1,
            "limit": limit,
            "appType": 1,
            "curr": "rub",
            "dest": -1257786
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        products = data.get("data", {}).get("products", [])
        results = []

        for p in products:
            id_ = p.get("id")
            name = p.get("name")
            price = p.get("salePriceU", 0) // 100

            link = f"https://www.wildberries.ru/catalog/{id_}/detail.aspx"

            results.append(f"📦 {name}\n💰 {price} ₽\n🔗 {link}\n")

        return results

    except Exception as e:
        print("WB error:", e)
        return []


# =====================
def vision_to_query(image_bytes: bytes) -> str:
    """
    Превращаем фото → текстовый запрос
    """

    # 🔥 если есть OpenAI — будет реально "Google Lens"
    if OPENAI_API_KEY:
        try:
            import base64

            b64 = base64.b64encode(image_bytes).decode()

            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Определи товар на фото и дай короткий поисковый запрос для Wildberries (3-6 слов на русском)."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }
                ],
                "max_tokens": 50
            }

            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )

            return r.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print("Vision error:", e)

    # fallback если нет API
    return "женский товар одежда аксессуар"


# =====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()

        await update.message.reply_text("🔍 Анализирую фото...")

        query = vision_to_query(img_bytes)

        await update.message.reply_text(f"🔎 Поиск: {query}")

        results = wb_search(query)

        if not results:
            await update.message.reply_text("❌ Ничего не найдено")
            return

        msg = "🛍 РЕЗУЛЬТАТЫ WB:\n\n" + "\n".join(results[:5])

        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        print("handler error:", e)


# =====================
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
