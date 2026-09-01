import os
import requests
import telebot
from telebot import types
from flask import Flask, request

BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

ADMIN_ID = 7932204371

# Категории книг 🏫
CATEGORIES = [
    "5 класс", "6 класс", "7 класс", "8 класс",
    "9 класс", "10 класс", "11 класс", "📚 Внеклассное и Сборники"
]

# Структура для хранения: {'5 класс': [{'file_id': ..., 'name': ...}], ...}
all_books = {cat: [] for cat in CATEGORIES}
all_music = []
user_states = {}  # Для запоминания временного файла админа

# Главное меню 🏠
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📚 Общие Книги (PDF)", "💡 Случайный факт")
    keyboard.row("🌦️ Погода", "🎵 Общая Музыка (MP3)")
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
            "📌 Выбери категорию для этой книги:", 
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
    bot.reply_to(message, f"🎵 Трек **«{track_name}»** сохранен!", parse_mode="Markdown")

# 3. Обработка текста и кнопок 💬
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # Сохранение книги в выбранную категорию (для админа) 👑
    if chat_id == ADMIN_ID and chat_id in user_states and text in CATEGORIES:
        file_data = user_states.pop(chat_id)
        all_books[text].append(file_data)
        bot.send_message(
            chat_id, 
            f"✅ Книга **«{file_data['file_name']}»** добавлена в раздел **{text}**!", 
            parse_mode="Markdown", 
            reply_markup=get_main_keyboard()
        )
        return

    if text == "🏠 Главное меню":
        bot.send_message(chat_id, "Главное меню 🏠", reply_markup=get_main_keyboard())

    elif text == "📚 Общие Книги (PDF)":
        bot.send_message(chat_id, "📖 Выбери класс или раздел:", reply_markup=get_categories_keyboard())

    elif text in CATEGORIES:
        books_in_cat = all_books[text]
        if not books_in_cat:
            bot.send_message(chat_id, f"В разделе **{text}** пока нет книг.", parse_mode="Markdown")
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for book in books_in_cat:
                keyboard.add(types.KeyboardButton(f"📖 {book['name']}"))
            keyboard.add(types.KeyboardButton("🏠 Главное меню"))
            bot.send_message(chat_id, f"📚 Книги в разделе **{text}**:", parse_mode="Markdown", reply_markup=keyboard)

    elif text == "🎵 Общая Музыка (MP3)":
        if not all_music:
            bot.send_message(chat_id, "Список музыки пуст.")
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for track in all_music:
                keyboard.add(types.KeyboardButton(f"🎧 {track['name']}"))
            keyboard.add(types.KeyboardButton("🏠 Главное меню"))
            bot.send_message(chat_id, "🎵 Доступные треки:", reply_markup=keyboard)

    elif text.startswith("📖 "):
        b_name = text.replace("📖 ", "")
        for cat_list in all_books.values():
            for book in cat_list:
                if book['name'] == b_name:
                    bot.send_document(chat_id, book['file_id'], caption=f"📖 {book['name']}")
                    return

    elif text.startswith("🎧 "):
        t_name = text.replace("🎧 ", "")
        for track in all_music:
            if track['name'] == t_name:
                bot.send_audio(chat_id, track['file_id'], caption=f"🎧 {track['name']}")
                return

    elif text == "💡 Случайный факт":
        try:
            res = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random")
            bot.send_message(chat_id, f"💡 **Факт:**\n{res.json().get('text')}", parse_mode="Markdown")
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
