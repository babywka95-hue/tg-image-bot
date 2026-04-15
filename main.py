import os
import io
import requests
import torch
import clip
from PIL import Image
from flask import Flask, request
from telegram import Update

# --------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")

app = Flask(__name__)

# --------------------
device = "cpu"  # важно для Render free

model, preprocess = clip.load("ViT-B/32", device=device)

# --------------------
def send(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

# --------------------
def wb_search(query, limit=30):
    url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
    params = {"query": query, "page": 1, "limit": limit}

    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        return []

    return r.json().get("data", {}).get("products", [])

# --------------------
def get_image_embedding(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        emb = model.encode_image(image_input)
        emb /= emb.norm(dim=-1, keepdim=True)

    return emb

# --------------------
def get_text_embedding(text):
    text_input = clip.tokenize([text]).to(device)

    with torch.no_grad():
        emb = model.encode_text(text_input)
        emb /= emb.norm(dim=-1, keepdim=True)

    return emb

# --------------------
def similarity(a, b):
    return (a @ b.T).item()

# --------------------
def build_candidates():
    return [
        "кроссовки",
        "кеды",
        "футболка",
        "платье",
        "куртка",
        "сумка",
        "часы",
        "наушники",
        "рюкзак",
        "джинсы"
    ]

# --------------------
def find_best_query(img_emb):
    best_q = "товар"
    best_score = -1

    for q in build_candidates():
        txt_emb = get_text_embedding(q)
        score = similarity(img_emb, txt_emb)

        if score > best_score:
            best_score = score
            best_q = q

    return best_q

# --------------------
def build_links(products):
    links = []

    for p in products:
        pid = p.get("id")
        name = p.get("name")

        if pid:
            links.append(
                f"{name}\nhttps://www.wildberries.ru/catalog/{pid}/detail.aspx"
            )

    return links[:5]

# --------------------
@app.route("/", methods=["GET"])
def home():
    return "WB Lens Bot running"

# --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, None)

    if not update.message:
        return "ok"

    chat_id = update.message.chat.id

    # ---------------- PHOTO ----------------
    if update.message.photo:
        send(chat_id, "🔍 Анализирую изображение...")

        photo = update.message.photo[-1]

        file_info = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getFile",
            params={"file_id": photo.file_id}
        ).json()

        file_path = file_info["result"]["file_path"]

        img_bytes = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        ).content

        # 1. embedding изображения
        img_emb = get_image_embedding(img_bytes)

        # 2. определяем категорию
        query = find_best_query(img_emb)

        send(chat_id, f"📦 Похоже на: {query}")

        # 3. поиск WB
        products = wb_search(query)

        if not products:
            send(chat_id, "❌ Ничего не найдено")
            return "ok"

        # 4. ссылки
        links = build_links(products)

        send(chat_id, "🛍 Похожие товары:\n\n" + "\n\n".join(links))

    else:
        send(chat_id, "Отправь фото товара 📸")

    return "ok"

# --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
