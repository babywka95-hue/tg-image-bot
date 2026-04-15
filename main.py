import os
import io
import time
from PIL import Image
import torch
import clip

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ---------------------
TELEGRAM_TOKEN = os.getenv("8665178501:AAHR4Asen0W9r3neZJn1Ll6fXZEQSvoApJo")

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

CATEGORIES = ["epilator", "hair dryer", "sneakers", "smart watch", "backpack", "headphones"]

# ---------------------
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

# ---------------------
def parse_wb(query, limit=10):
    driver = setup_driver()
    query_url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}"
    driver.get(query_url)
    time.sleep(3)  # дождаться загрузки страницы JS

    products = []
    items = driver.find_elements(By.CSS_SELECTOR, "div.product-card")
    for item in items[:limit]:
        try:
            name = item.get_attribute("data-name")
            price = item.get_attribute("data-sale")
            reviews = int(item.get_attribute("data-feedbacks") or 0)
            rating = float(item.get_attribute("data-rating") or 0)
            link = item.get_attribute("href")
            if reviews >= 1 and rating >= 4.0:
                products.append({
                    "name": name,
                    "price": price,
                    "reviews": reviews,
                    "rating": rating,
                    "link": link
                })
        except:
            continue

    driver.quit()
    return products

# ---------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    await update.message.reply_text("🔍 Определяю категорию товара...")

    with torch.no_grad():
        text_inputs = clip.tokenize(CATEGORIES).to(device)
        text_features = model.encode_text(text_inputs)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).squeeze(0)
        idx = similarity.argmax().item()
        query = CATEGORIES[idx]

    await update.message.reply_text(f"🔑 Категория: {query}")

    products = parse_wb(query, limit=10)
    if not products:
        await update.message.reply_text("❌ Нет товаров с рейтингом ≥4 и отзывами ≥1")
        return

    msg = "🛍 ТОП товаров WB:\n\n"
    for p in products:
        msg += f"• {p['name']}\n"
        msg += f"⭐ {p['rating']} | 💬 {p['reviews']}\n"
        msg += f"💰 {p['price']} ₽\n"
        msg += f"🔗 {p['link']}\n\n"

    await update.message.reply_text(msg)

# ---------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
