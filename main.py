import os
import requests
import telebot
from telebot import types
from flask import Flask, request
from supabase import create_client, Client
from datetime import datetime

# Инициализация бота
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# --- ПОДКЛЮЧЕНИЕ К SUPABASE 🔌 ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Хранилище активных таймеров пользователей: {user_id: {'subject': ..., 'start_time': ...}}
user_timers = {}

# Функция для сохранения данных об учебе 📝
def save_study_session(user_id: int, subject: str, duration: int):
    try:
        data = {
            "user_id": user_id,
            "subject": subject,
            "duration_minutes": duration
        }
        supabase.table("study_sessions").insert(data).execute()
        return True
    except Exception as e:
        print(f"Ошибка сохранения в Supabase: {e}")
        return False

ADMIN_ID = 7932204371

CATEGORIES = [
    "5 класс", "6 класс", "7 класс", "8 класс",
    "9 класс", "10 класс", "11 класс", "📚 Внеклассное и Сборники"
]

# Предметы для выбора перед стартом таймера 📚
SUBJECTS = ["Математика 📐", "Физика 🧲", "Химия 🧪", "Английский 🇬🇧", "История 📜"]

all_books = {cat: [] for cat in CATEGORIES}
all_music = []
user_states = {}

# Главное меню 🏠
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📚 Общие Книги (PDF)", "⏱️ Учёба (Таймер)")
    keyboard.row("🌦️ Погода", "🎵 Общая Музыка (MP3)")
    keyboard.row("💡 Случайный факт")
    return keyboard

# Клавиатура предметов (Inline) 🔘
def get_subjects_inline_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for subj in SUBJECTS:
        keyboard.add(types.InlineKeyboardButton(subj, callback_data=f"start_timer_{subj}"))
    return keyboard

# Меню выбора категорий книг 📂
def get_categories_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in CATEGORIES:
        keyboard.add(types.KeyboardButton(cat))
    keyboard.add(types.KeyboardButton("🏠 Главное меню"))
    return keyboard

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Привет! Выбери раздел ниже👇", reply_markup=get_main_keyboard())

# Обработка нажатий на Inline-кнопки (предметы и стоп) 🔘
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_clicks(call):
    user_id = call.from_user.id
    
    # 1. Нажатие на выбор предмета
    if call.data.startswith("start_timer_"):
        subject_name = call.data.replace("start_timer_", "")
        
        # Запоминаем предмет и время старта ⏱️
        user_timers[user_id] = {
            "subject": subject_name,
            "start_time": datetime.now()
        }
        
        # Кнопка для остановки таймера
        stop_keyboard = types.InlineKeyboardMarkup()
        stop_keyboard.add(types.InlineKeyboardButton("🛑 Завершить сессию", callback_data="stop_timer"))
        
        bot.edit_message_text(
            f"⏱️ **Таймер запущен!**\n\nПредмет: **{subject_name}**\nВремя пошло... Удачи в учёбе! 📚",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=stop_keyboard
        )
    
    # 2. Нажатие на «Завершить сессию» 🛑
    elif call.data == "stop_timer":
        if user_id in user_timers:
            session_info = user_timers.pop(user_id)
            start_time = session_info["start_time"]
            subject = session_info["subject"]
            
            # Вычисляем длительность в минутах ⏳
            elapsed_seconds = (datetime.now() - start_time).total_seconds()
            duration_minutes = round(elapsed_seconds / 60)
            
            # Записываем в базу даже если прошел 0 мин (для теста), ставим минимум 1 мин
            final_minutes = max(1, duration_minutes)
            
            success = save_study_session(user_id, subject, final_minutes)
            
            if success:
                bot.edit_message_text(
                    f"🎉 **Отличная работа!**\n\nПредмет: **{subject}**\nВремя: **{final_minutes} мин.**\n\nДанные сохранены в базу! 💾",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown"
                )
            else:
                bot.edit_message_text(
                    "❌ Не удалось сохранить данные в базу.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
        else:
            bot.answer_callback_query(call.id, "Таймер не был запущен!", show_alert=True)

# 1. Прием PDF от Админа 🔒
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Загружать файлы может только администратор.")
        return

    if message.document.mime_type == 'application/pdf':
        user_states[ADMIN_ID] = {
            'file_id': message.document.file_id,
            'file_name': message.document.file_name or "Книга.pdf"
        }
        bot.reply_to(
            message, 
            "📌 Отлично! Теперь нажми на кнопку с нужным классом ниже, чтобы сохранить книгу:", 
            reply_markup=get_categories_keyboard()
        )
    else:
        bot.reply_to(message, "Пожалуйста, отправь файл в формате PDF.")

# 2. Прием MP3 от Админа 🎵
@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Загружать музыку может только администратор.")
        return

    file_id = message.audio.file_id
    track_name = message.audio.title or message.audio.file_name or "Аудиозапись"
    all_music.append({'file_id': file_id, 'name': track_name})
    bot.reply_to(message, f"🎵 Трек **«{track_name}»** успешно сохранен!", parse_mode="Markdown")

# 3. Обработка текста и кнопок 💬
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id == ADMIN_ID and chat_id in user_states and text in CATEGORIES:
        file_data = user_states.pop(chat_id)
        all_books[text].append(file_data)
        bot.send_message(
            chat_id, 
            f"✅ Книга **«{file_data['file_name']}»** сохранена в раздел **{text}**!", 
            parse_mode="Markdown", 
            reply_markup=get_main_keyboard()
        )
        return

    if text == "🏠 Главное меню":
        user_states.pop(chat_id, None)
        bot.send_message(chat_id, "Главное меню 🏠", reply_markup=get_main_keyboard())

    elif text == "⏱️ Учёба (Таймер)":
        if chat_id in user_timers:
            bot.send_message(chat_id, "⚠️ У тебя уже запущен таймер! Заверши его перед новым стартом.")
        else:
            bot.send_message(
                chat_id, 
                "📚 Выбери предмет, чтобы начать отсчёт времени:", 
                reply_markup=get_subjects_inline_keyboard()
            )

    elif text == "📚 Общие Книги (PDF)":
        bot.send_message(chat_id, "📖 Выбери класс или раздел из списка ниже:", reply_markup=get_categories_keyboard())

    elif text in CATEGORIES:
        books_in_cat = all_books[text]
        if not books_in_cat:
            bot.send_message(
                chat_id, 
                f"📭 В разделе **{text}** пока нет доступных книг.", 
                parse_mode="Markdown",
                reply_markup=get_categories_keyboard()
            )
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for book in books_in_cat:
                keyboard.add(types.KeyboardButton(f"📖 {book['name']}"))
            keyboard.add(types.KeyboardButton("🏠 Главное меню"))
            bot.send_message(
                chat_id, 
                f"📚 Вот книги, доступные в разделе **{text}**:\nНажми на нужную книгу для скачивания.", 
                parse_mode="Markdown", 
                reply_markup=keyboard
            )

    elif text == "🎵 Общая Музыка (MP3)":
        if not all_music:
            bot.send_message(chat_id, "🎵 Список музыки пока пуст.", reply_markup=get_main_keyboard())
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for track in all_music:
                keyboard.add(types.KeyboardButton(f"🎧 {track['name']}"))
            keyboard.add(types.KeyboardButton("🏠 Главное меню"))
            bot.send_message(chat_id, "🎵 Выбери трек для прослушивания:", reply_markup=keyboard)

    elif text.startswith("📖 "):
        b_name = text.replace("📖 ", "")
        for cat_list in all_books.values():
            for book in cat_list:
                if book['name'] == b_name:
                    bot.send_document(chat_id, book['file_id'], caption=f"📖 {book['name']}")
                    return
        bot.send_message(chat_id, "Файл не найден.")

    elif text.startswith("🎧 "):
        t_name = text.replace("🎧 ", "")
        for track in all_music:
            if track['name'] == t_name:
                bot.send_audio(chat_id, track['file_id'], caption=f"🎧 {track['name']}")
                return
        bot.send_message(chat_id, "Аудиозапись не найдена.")

    elif text == "💡 Случайный факт":
        try:
            res = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random")
            bot.send_message(chat_id, f"💡 **Интересный факт:**\n{res.json().get('text')}", parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, "Не удалось получить факт.")

    else:
        try:
            res = requests.get(f"https://wttr.in/{text}?m&format=3")
            if res.status_code == 200 and "Unknown location" not in res.text:
                bot.reply_to(message, f"🌦️ **Погода:**\n{res.text}", parse_mode="Markdown")
            else:
                bot.reply_to(message, f"Город «{text}» не найден.")
        except Exception:
            bot.reply_to(message, "Ошибка запроса погоды.")

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://my-book-bot-9ga9.onrender.com/' + BOT_TOKEN)
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
