import os
import requests
import telebot
from telebot import types
from flask import Flask, request

BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# Словари для хранения списков файлов пользователей
user_books = {}
user_music = {}

# Главное меню (кнопки под клавиатурой)
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📚 Мои Книги (PDF)", "💡 Случайный факт")
    keyboard.row("🌦️ Погода", "🎵 Моя Музыка (MP3)")
    return keyboard

# Меню со списком книг
def get_books_keyboard(chat_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    books = user_books.get(chat_id, [])
    for book in books:
        keyboard.add(types.KeyboardButton(text=f"📖 {book['name']}"))
    keyboard.add(types.KeyboardButton(text="🏠 Главное меню"))
    return keyboard

# Меню со списком музыки
def get_music_keyboard(chat_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    tracks = user_music.get(chat_id, [])
    for track in tracks:
        keyboard.add(types.KeyboardButton(text=f"🎧 {track['name']}"))
    keyboard.add(types.KeyboardButton(text="🏠 Главное меню"))
    return keyboard

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id, 
        "Привет! Выбери раздел ниже или отправь мне PDF / MP3 файл! 👇", 
        reply_markup=get_main_keyboard()
    )

# Обработка документов (PDF)
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.document.mime_type == 'application/pdf':
        chat_id = message.chat.id
        file_id = message.document.file_id
        file_name = message.document.file_name or "Книга.pdf"
        
        if chat_id not in user_books:
            user_books[chat_id] = []
        user_books[chat_id].append({'file_id': file_id, 'name': file_name})
        bot.reply_to(message, f"📚 Книга **«{file_name}»** сохранена!", parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        bot.reply_to(message, "Пожалуйста, отправь файл в формате PDF.")

# Обработка аудио (MP3)
@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    chat_id = message.chat.id
    file_id = message.audio.file_id
    track_name = message.audio.title or message.audio.file_name or "Аудиозапись"
    
    if chat_id not in user_music:
        user_music[chat_id] = []
    user_music[chat_id].append({'file_id': file_id, 'name': track_name})
    bot.reply_to(message, f"🎵 Трек **«{track_name}»** сохранён!", parse_mode="Markdown", reply_markup=get_main_keyboard())

# Обработка текстовых команд и нажатий на кнопки
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text == "🏠 Главное меню":
        bot.send_message(chat_id, "Возвращаемся в главное меню 🏠", reply_markup=get_main_keyboard())

    elif text == "💡 Случайный факт":
        try:
            res = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random")
            if res.status_code == 200:
                fact_text = res.json().get('text')
                bot.send_message(chat_id, f"💡 **Интересный факт:**\n{fact_text}", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "Попробуй ещё раз!")
        except Exception:
            bot.send_message(chat_id, "Ошибка при запросе к API.")

    elif text == "🌦️ Погода":
        bot.send_message(chat_id, "🌦️ Напиши название города в чат (например: *Ташкент*):", parse_mode="Markdown")

    elif text == "📚 Мои Книги (PDF)":
        books = user_books.get(chat_id, [])
        if not books:
            bot.send_message(chat_id, "📚 У тебя нет сохранённых PDF-книг. Отправь мне PDF-файл!", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, "📚 Выбери нужную книгу из списка ниже:", reply_markup=get_books_keyboard(chat_id))

    elif text == "🎵 Моя Музыка (MP3)":
        tracks = user_music.get(chat_id, [])
        if not tracks:
            bot.send_message(chat_id, "🎵 У тебя нет сохранённых MP3-треков. Отправь мне MP3-файл!", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, "🎵 Выбери нужный трек из списка ниже:", reply_markup=get_music_keyboard(chat_id))

    # Выдача конкретной книги при нажатии на её название
    elif text.startswith("📖 "):
        book_name = text.replace("📖 ", "")
        books = user_books.get(chat_id, [])
        found = False
        for book in books:
            if book['name'] == book_name:
                bot.send_document(chat_id, book['file_id'], caption=f"📖 {book['name']}")
                found = True
                break
        if not found:
            bot.send_message(chat_id, "Книга не найдена.")

    # Выдача конкретного трека при нажатии на его название
    elif text.startswith("🎧 "):
        track_name = text.replace("🎧 ", "")
        tracks = user_music.get(chat_id, [])
        found = False
        for track in tracks:
            if track['name'] == track_name:
                bot.send_audio(chat_id, track['file_id'], caption=f"🎧 {track['name']}")
                found = True
                break
        if not found:
            bot.send_message(chat_id, "Трек не найден.")

    # Если текст не кнопка — ищем погоду в градусах Цельсия (?m)
    else:
        try:
            res = requests.get(f"https://wttr.in/{text}?m&format=3")
            if res.status_code == 200 and "Unknown location" not in res.text:
                bot.reply_to(message, f"🌦️ **Погода:**\n{res.text}")
            else:
                bot.reply_to(message, f"Не удалось найти город «{text}».")
        except Exception:
            bot.reply_to(message, "Ошибка при запросе погоды.")

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
