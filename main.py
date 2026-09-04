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

# Хранилища активных таймеров и состояний пользователей
user_timers = {}
user_states = {}

ADMIN_ID = 7932204371

CATEGORIES = [
    "5 класс", "6 класс", "7 класс", "8 класс",
    "9 класс", "10 класс", "11 класс", "📚 Внеклассное и Сборники"
]

SUBJECTS = ["Математика 📐", "Физика 🧲", "Химия 🧪", "Английский 🇬🇧", "История 📜"]

# --- ФУНКЦИИ РАБОТЫ С SUPABASE 💾 ---

def save_study_session(user_id: int, subject: str, duration: int):
    try:
        supabase.table("study_sessions").insert({
            "user_id": user_id, "subject": subject, "duration_minutes": duration
        }).execute()
        return True
    except Exception as e:
        print(f"Ошибка сохранения сессии: {e}")
        return False

def save_book_to_db(name: str, category: str, file_id: str):
    try:
        supabase.table("books").insert({
            "name": name, "category": category, "file_id": file_id
        }).execute()
        return True
    except Exception as e:
        print(f"Ошибка сохранения книги: {e}")
        return False

def get_books_by_category(category: str):
    try:
        res = supabase.table("books").select("*").eq("category", category).execute()
        return res.data
    except Exception as e:
        print(f"Ошибка получения книг: {e}")
        return []

# Сохранение музыки в базу Supabase 🎵
def save_music_to_db(name: str, file_id: str):
    try:
        supabase.table("music").insert({
            "name": name, "file_id": file_id
        }).execute()
        return True
    except Exception as e:
        print(f"Ошибка сохранения музыки: {e}")
        return False

def get_all_music():
    try:
        res = supabase.table("music").select("*").execute()
        return res.data
    except Exception as e:
        print(f"Ошибка получения музыки: {e}")
        return []

# --- КЛАВИАТУРЫ ⌨️ ---

# Главное меню 🏠
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📚 Общие Книги (PDF)", "⏱️ Учёба (Таймер)")
    keyboard.row("🌦️ Погода", "🎵 Общая Музыка (MP3)")
    keyboard.row("💡 Случайный факт")
    return keyboard

def get_subjects_inline_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for subj in SUBJECTS:
        keyboard.add(types.InlineKeyboardButton(subj, callback_data=f"start_timer_{subj}"))
    return keyboard

def get_categories_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in CATEGORIES:
        keyboard.add(types.KeyboardButton(cat))
    keyboard.add(types.KeyboardButton("🏠 Главное меню"))
    return keyboard

# --- ОБРАБОТКА КОМАНД И НАЖАТИЙ ---

@bot.message_handler(commands=['start'])
def start_message(message):
    user_states.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "Привет! Выбери раздел ниже👇", reply_markup=get_main_keyboard())

# Обработка Inline-кнопки (Таймер) 🔘
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_clicks(call):
    user_id = call.from_user.id
    
    if call.data.startswith("start_timer_"):
        subject_name = call.data.replace("start_timer_", "")
        user_timers[user_id] = {"subject": subject_name, "start_time": datetime.now()}
        
        stop_keyboard = types.InlineKeyboardMarkup()
        stop_keyboard.add(types.InlineKeyboardButton("🛑 Завершить сессию", callback_data="stop_timer"))
        
        bot.edit_message_text(
            f"⏱️ **Таймер запущен!**\n\nПредмет: **{subject_name}**\nВремя пошло... Удачи в учёбе! 📚",
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            parse_mode="Markdown", reply_markup=stop_keyboard
        )
    elif call.data == "stop_timer":
        if user_id in user_timers:
            session_info = user_timers.pop(user_id)
            duration_minutes = max(1, round((datetime.now() - session_info["start_time"]).total_seconds() / 60))
            success = save_study_session(user_id, session_info["subject"], duration_minutes)
            
            if success:
                bot.edit_message_text(
                    f"🎉 **Отличная работа!**\n\nПредмет: **{session_info['subject']}**\nВремя: **{duration_minutes} мин.**\n\nДанные сохранены в базу! 💾",
                    chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown"
                )
            else:
                bot.edit_message_text("❌ Не удалось сохранить данные в базу.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Таймер не был запущен!", show_alert=True)

# Прием документов (PDF книги или MP3 музыка) 📁
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Загружать файлы может только администратор.")
        return

    file_name = message.document.file_name or ""
    mime_type = message.document.mime_type or ""

    # Если PDF — готовим к сохранению книги
    if mime_type == 'application/pdf' or file_name.endswith('.pdf'):
        user_states[ADMIN_ID] = {
            'action': 'save_book',
            'file_id': message.document.file_id,
            'file_name': file_name or "Книга.pdf"
        }
        bot.reply_to(message, "📌 Отлично! Теперь нажми на кнопку с нужным классом ниже, чтобы сохранить книгу:", reply_markup=get_categories_keyboard())
    
    # Если файл с музыкой (.mp3)
    elif mime_type in ['audio/mpeg', 'audio/mp3'] or file_name.endswith('.mp3'):
        track_name = message.caption or file_name.replace('.mp3', '') or "Музыкальный трек"
        if len(track_name) > 50:
            track_name = track_name[:47] + "..."
            
        success = save_music_to_db(track_name, message.document.file_id)
        if success:
            bot.reply_to(message, f"🎵 Трек **«{track_name}»** успешно сохранен в базу музыки!", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Ошибка при сохранении трека в базу.")
    else:
        bot.reply_to(message, "⚠️ Принимаются только PDF файлы для книг и MP3 файлы для музыки.")

# Прием обычных аудиозаписей 🎵
@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Загружать музыку может только администратор.")
        return

    file_id = message.audio.file_id
    track_name = message.audio.title or message.audio.file_name or message.caption or "Музыкальный трек"
    
    if len(track_name) > 50:
        track_name = track_name[:47] + "..."

    success = save_music_to_db(track_name, file_id)
    if success:
        bot.reply_to(message, f"🎵 Трек **«{track_name}»** успешно сохранен в базу данных!", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Ошибка при сохранении трека в базу.")

# 3. Обработка текста и кнопок 💬
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text == "🏠 Главное меню":
        user_states.pop(chat_id, None)
        bot.send_message(chat_id, "Главное меню 🏠", reply_markup=get_main_keyboard())
        return

    # Ожидание города для погоды 🌦️
    if user_states.get(chat_id) == "waiting_for_weather":
        user_states.pop(chat_id, None)
        try:
            detailed_res = requests.get(f"https://wttr.in/{text}?m&lang=ru&format=%l:+%C+%t+(ощущается+как+%f),+ветер:+%w")
            
            if detailed_res.status_code == 200 and "Unknown location" not in detailed_res.text:
                bot.send_message(
                    chat_id, 
                    f"🌍 **Погода в городе {text.capitalize()}:**\n\n📌 {detailed_res.text}\n\n*Хорошего дня!* ☀️", 
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                bot.send_message(chat_id, f"❌ Город «{text}» не найден. Попробуй еще раз, нажав кнопку «🌦️ Погода».", reply_markup=get_main_keyboard())
        except Exception:
            bot.send_message(chat_id, "⚠️ Ошибка при запросе погоды. Попробуйте позже.", reply_markup=get_main_keyboard())
        return

    # Сохранение книги 💾
    if chat_id == ADMIN_ID and user_states.get(chat_id, {}).get('action') == 'save_book' and text in CATEGORIES:
        file_data = user_states.pop(chat_id)
        success = save_book_to_db(file_data['file_name'], text, file_data['file_id'])
        
        if success:
            bot.send_message(chat_id, f"✅ Книга **«{file_data['file_name']}»** успешно сохранена для раздела **{text}**!", parse_mode="Markdown", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, "❌ Ошибка при сохранении книги в базу.", reply_markup=get_main_keyboard())
        return

    if text == "⏱️ Учёба (Таймер)":
        if chat_id in user_timers:
            bot.send_message(chat_id, "⚠️ У тебя уже запущен таймер! Заверши его перед новым стартом.")
        else:
            bot.send_message(chat_id, "📚 Выбери предмет, чтобы начать отсчёт времени:", reply_markup=get_subjects_inline_keyboard())

    elif text == "📚 Общие Книги (PDF)":
        bot.send_message(chat_id, "📖 Выбери класс или раздел из списка ниже:", reply_markup=get_categories_keyboard())

    elif text == "🎵 Общая Музыка (MP3)":
        music_list = get_all_music()
        if not music_list:
            bot.send_message(chat_id, "📭 В базе пока нет сохраненной музыки.", reply_markup=get_main_keyboard())
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for track in music_list:
                keyboard.add(types.KeyboardButton(f"🎧 {track['name']}"))
            keyboard.add(types.KeyboardButton("🏠 Главное меню"))
            bot.send_message(chat_id, "🎵 Вот доступные треки:\nНажми на нужный, чтобы послушать:", reply_markup=keyboard)

    elif text == "🌦️ Погода":
        user_states[chat_id] = "waiting_for_weather"
        cancel_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_kb.add(types.KeyboardButton("🏠 Главное меню"))
        
        bot.send_message(
            chat_id, 
            "🌤️ **Погода**\n\nВ каком месте ты хочешь узнать погоду? Напиши название города (например, *Ташкент*):", 
            parse_mode="Markdown",
            reply_markup=cancel_kb
        )

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
            res = supabase.table("books").select("file_id").eq("name", b_name).execute()
            if res.data:
                bot.send_document(chat_id, res.data[0]['file_id'], caption=f"📖 {b_name}")
            else:
                bot.send_message(chat_id, "Файл не найден в базе данных.")
        except Exception:
            bot.send_message(chat_id, "Ошибка при поиске файла.")

    elif text.startswith("🎧 "):
        t_name = text.replace("🎧 ", "")
        try:
            res = supabase.table("music").select("file_id").eq("name", t_name).execute()
            if res.data:
                bot.send_audio(chat_id, res.data[0]['file_id'], caption=f"🎧 {t_name}")
            else:
                bot.send_message(chat_id, "Аудиозапись не найдена в базе.")
        except Exception:
            bot.send_message(chat_id, "Ошибка при поиске аудио.")

    elif text == "💡 Случайный факт":
        try:
            res = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random")
            bot.send_message(chat_id, f"💡 **Интересный факт:**\n{res.json().get('text')}", parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, "Не удалось получить факт.")

    else:
        bot.send_message(chat_id, "Я не понял команду. Воспользуйся главным меню 👇", reply_markup=get_main_keyboard())

# --- FLASK ВЕБХУК ДЛЯ RENDER ---

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
