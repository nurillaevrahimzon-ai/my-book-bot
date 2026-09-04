# --- ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ---

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # 1. Если пользователь ранее нажал "Погода" и бот ждет название города
    if chat_id in user_states and user_states[chat_id].get('action') == 'waiting_for_city':
        if text == "🏠 Главное меню":
            user_states.pop(chat_id, None)
            bot.send_message(chat_id, "Главное меню 🏠", reply_markup=get_main_keyboard())
            return

        try:
            res = requests.get(f"https://wttr.in/{text}?m&format=3")
            if res.status_code == 200 and "Unknown location" not in res.text:
                bot.reply_to(message, f"🌦️ **Погода в городе {text}:**\n{res.text}", parse_mode="Markdown")
                user_states.pop(chat_id, None)  # Сбрасываем состояние
            else:
                bot.reply_to(message, f"❌ Город «{text}» не найден. Попробуй ввести название ещё раз:")
        except Exception:
            bot.reply_to(message, "Ошибка запроса погоды. Попробуй позже.")
        return

    # 2. Сохранение книги от Админа
    if chat_id == ADMIN_ID and chat_id in user_states and text in CATEGORIES:
        file_data = user_states.pop(chat_id)
        success = save_book_to_db(file_data['file_name'], text, file_data['file_id'])
        if success:
            bot.send_message(chat_id, f"✅ Книга **«{file_data['file_name']}»** сохранена!", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ Ошибка при сохранении книги.", reply_markup=get_main_keyboard())
        return

    # 3. Главное меню
    if text == "🏠 Главное меню":
        user_states.pop(chat_id, None)
        bot.send_message(chat_id, "Главное меню 🏠", reply_markup=get_main_keyboard())

    # 4. Нажатие на кнопку "Погода"
    elif text == "🌦️ Погода":
        user_states[chat_id] = {'action': 'waiting_for_city'}
        
        # Создаем кнопку отмены для удобства
        cancel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_keyboard.add(types.KeyboardButton("🏠 Главное меню"))
        
        bot.send_message(
            chat_id, 
            "🌍 **Напишите название города**, чтобы узнать погоду (например: *Ташкент*, *Москва*, *Самарканд*):", 
            parse_mode="Markdown",
            reply_markup=cancel_keyboard
        )

    # 5. Раздел с музыкой
    elif text == "🎵 Общая Музыка (MP3)":
        music_list = get_all_music()
        if not music_list:
            bot.send_message(chat_id, "📭 Раздел музыки пока пуст.")
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for track in music_list:
                keyboard.add(types.KeyboardButton(f"🎧 {track['name']}"))
            keyboard.add(types.KeyboardButton("🏠 Главное меню"))
            bot.send_message(chat_id, "🎵 Выберите трек для прослушивания:", reply_markup=keyboard)

    # 6. Прослушивание трека
    elif text.startswith("🎧 "):
        t_name = text.replace("🎧 ", "")
        try:
            response = supabase.table("music").select("file_id").eq("name", t_name).execute()
            if response.data:
                file_id = response.data[0]['file_id']
                bot.send_audio(chat_id, file_id, caption=f"🎧 {t_name}")
            else:
                bot.send_message(chat_id, "Аудиозапись не найдена в базе данных.")
        except Exception:
            bot.send_message(chat_id, "Ошибка при поиске аудиозаписи.")

    # 7. Таймер
    elif text == "⏱️ Учёба (Таймер)":
        if chat_id in user_timers:
            bot.send_message(chat_id, "⚠️ У тебя уже запущен таймер!")
        else:
            bot.send_message(chat_id, "📚 Выбери предмет, чтобы начать отсчёт времени:", reply_markup=get_subjects_inline_keyboard())

    # 8. Книги
    elif text == "📚 Общие Книги (PDF)":
        bot.send_message(chat_id, "📖 Выбери класс или раздел из списка ниже:", reply_markup=get_categories_keyboard())

    elif text in CATEGORIES:
        books_in_cat = get_books_by_category(text)
        if not books_in_cat:
            bot.send_message(chat_id, f"📭 В разделе **{text}** пока нет доступных книг.", parse_mode="Markdown", reply_markup=get_categories_keyboard())
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for book in books_in_cat:
                keyboard.add(types.KeyboardButton(f"📖 {book['name']}"))
            keyboard.add(types.KeyboardButton("🏠 Главное меню"))
            bot.send_message(chat_id, f"📚 Книги в разделе **{text}**:", parse_mode="Markdown", reply_markup=keyboard)

    elif text.startswith("📖 "):
        b_name = text.replace("📖 ", "")
        try:
            response = supabase.table("books").select("file_id").eq("name", b_name).execute()
            if response.data:
                bot.send_document(chat_id, response.data[0]['file_id'], caption=f"📖 {b_name}")
            else:
                bot.send_message(chat_id, "Файл не найден.")
        except Exception:
            bot.send_message(chat_id, "Ошибка при поиске файла.")

    # 9. Факты
    elif text == "💡 Случайный факт":
        try:
            res = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random")
            bot.send_message(chat_id, f"💡 **Интересный факт:**\n{res.json().get('text')}", parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, "Не удалось получить факт.")
