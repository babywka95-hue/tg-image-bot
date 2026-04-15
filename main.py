import os
import io
import requests
from flask import Flask, request
from telegram import Update

# --------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise Exception("Missing TELEGRAM_TOKEN")

app = Flask(__name__)

# --------------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

# --------------------
def wb_search(query, limit=100):
    try:
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
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
    avg = 0

    for p in products:
        r = p.get("feedbacks", 0) or 0
        avg += r

        if r > 300:
            strong += 1
        if r > 1000:
            ultra += 1

    avg = avg / total if total else 0

    return total, strong, ultra, int(avg)

# --------------------
@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        update = Update.de_json(data, None)

        if not update.message:
            return "ok"

        chat_id = update.message.chat.id

        # ---------------- PHOTO ----------------
        if update.message.photo:
            send_message(chat_id, "🔍 Анализируем фото...")

            photo = update.message.photo[-1]
            file_id = photo.file_id

            # получаем файл через Telegram API
            file_info = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getFile",
                params={"file_id": file_id}
            ).json()

            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

            img_bytes = requests.get(file_url).content

            # 👉 временно без AI (можно улучшить позже)
            query = "товар"

            products = wb_search(query)
            stats = analyze(products)

            if not stats:
                send_message(chat_id, "❌ Нет данных")
                return "ok"

            total, strong, ultra, avg = stats

            msg = (
                f"📊 АНАЛИЗ WB\n\n"
                f"📦 Товаров: {total}\n"
                f"💪 >300 отзывов: {strong}\n"
                f"🔥 >1000 отзывов: {ultra}\n"
                f"📈 Средние отзывы: {avg}\n\n"
            )

            if ultra > 5:
                msg += "🚫 Вход сложный"
            elif strong > 10:
                msg += "🟡 Средняя конкуренция"
            else:
                msg += "🟢 Можно заходить"

            send_message(chat_id, msg)

        else:
            send_message(chat_id, "📸 Отправь фото товара")

        return "ok"

    except Exception as e:
        print("ERROR:", e)
        return "ok"

# --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
