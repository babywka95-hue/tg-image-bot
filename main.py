import os
import io
import requests
import torch
import clip
from PIL import Image

from flask import Flask, request

# --------------------
app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")

API = f"https://api.telegram.org/bot{TOKEN}"

# --------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)


# --------------------
def send_message(chat_id, text):
    requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )


# --------------------
def wb_search(query, limit=50):
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?query={query}&page=1&limit={limit}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return []
    return r.json().get("data", {}).get("products", [])


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

    return total, strong, ultra, avg


# --------------------
def build_query_from_image(image_input):
    prompts = [
        "a product",
        "a household item",
        "a beauty product",
        "a clothing item",
        "a gadget",
        "a consumer product"
    ]

    with torch.no_grad():
        text = clip.tokenize(prompts).to(device)
        text_f = model.encode_text(text)
        text_f /= text_f.norm(dim=-1, keepdim=True)

        img_f = model.encode_image(image_input)
        img_f /= img_f.norm(dim=-1, keepdim=True)

        sim = (img_f @ text_f.T).squeeze(0)
        idx = sim.argmax().item()

    return ["product", "home goods", "beauty", "clothes", "electronics", "goods"][idx]


# --------------------
@app.route("/", methods=["GET"])
def home():
    return "OK", 200


# --------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]

    # ---------------- TEXT
    if "text" in msg:
        send_message(chat_id, f"📩 Ты написал: {msg['text']}")
        return "ok", 200

    # ---------------- PHOTO
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]

        file = requests.get(f"{API}/getFile", params={"file_id": file_id}).json()
        file_path = file["result"]["file_path"]

        img_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        img_bytes = requests.get(img_url).content

        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        image_input = preprocess(image).unsqueeze(0).to(device)

        send_message(chat_id, "🔍 Анализ товара...")

        query = build_query_from_image(image_input)
        send_message(chat_id, f"📦 Поиск WB: {query}")

        products = wb_search(query)
        stats = analyze(products)

        if not stats:
            send_message(chat_id, "❌ Нет данных")
            return "ok", 200

        total, strong, ultra, avg = stats

        msg_text = f"""
📊 АНАЛИЗ WB

📦 Товаров: {total}
💪 >300 отзывов: {strong}
🔥 >1000 отзывов: {ultra}
📈 Средние отзывы: {int(avg)}
"""

        if ultra > 5:
            msg_text += "\n🚫 СЛОЖНАЯ НИША"
        elif strong > 10:
            msg_text += "\n🟡 СРЕДНЯЯ КОНКУРЕНЦИЯ"
        else:
            msg_text += "\n🟢 МОЖНО ЗАХОДИТЬ"

        send_message(chat_id, msg_text)

    return "ok", 200


# --------------------
def set_webhook():
    requests.get(
        f"{API}/setWebhook",
        params={"url": f"{PUBLIC_URL}/webhook"}
    )


# --------------------
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
