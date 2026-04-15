@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        update = Update.de_json(data, bot)

        if not update.message:
            return "ok"

        chat_id = update.message.chat.id

        # --- если фото ---
        if update.message.photo:
            bot.send_message(chat_id, "🔍 Анализируем фото...")

            photo = update.message.photo[-1]
            file = bot.get_file(photo.file_id)

            # скачиваем
            img_bytes = requests.get(file.file_path).content

            # сейчас без CLIP → просто заглушка
            query = "товар"

            products = wb_search(query)
            stats = analyze(products)

            if not stats:
                bot.send_message(chat_id, "❌ Нет данных")
                return "ok"

            total, strong, ultra, avg = stats

            msg = (
                f"📊 АНАЛИЗ\n\n"
                f"📦 Товаров: {total}\n"
                f"💪 >300 отзывов: {strong}\n"
                f"🔥 >1000 отзывов: {ultra}\n"
                f"📈 Средние: {avg}\n\n"
            )

            if ultra > 5:
                msg += "🚫 Сложно"
            elif strong > 10:
                msg += "🟡 Средне"
            else:
                msg += "🟢 Можно заходить"

            bot.send_message(chat_id, msg)

        else:
            bot.send_message(chat_id, "Отправь фото товара 📸")

        return "ok"

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "error"
