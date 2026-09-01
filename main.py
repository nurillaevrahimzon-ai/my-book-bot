import os
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# --- 1. ВЕБ-СЕРВЕР DLYA RENDER ---
app = Flask('')

@app.route('/')
def home():
    return 'Bot is running!'

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

keep_alive()

# --- 2. NASTROYKA BOTA ---
TOKEN = '8725622521:AAE8psytiYFVm6adEELKgnbyIUdENXHDmhs'
bot = telebot.TeleBot(TOKEN)

# Baza dannykh i sostoyaniya
books_db = []
user_states = {}

# --- 3. KLAVIATURA (KNOPKI) ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add = types.KeyboardButton('📥 Добавить книгу')
    btn_list = types.KeyboardButton('📚 Мои книги')
    btn_fact = types.KeyboardButton('🎲 Факт о книгах')
    btn_quiz = types.KeyboardButton('❓ Викторина')
    markup.add(btn_add, btn_list)
    markup.add(btn_fact, btn_quiz)
    return markup

# --- 4. OBROBOTCHIKI ---
@bot.message_handler(commands=['start'])
def start_message(message):
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id,
        'Привет! Выбери действие на клавиатуре внизу 👇',
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text

    # Нажали кнопку "Добавить книгу"
    if text == '📥 Добавить книгу':
        user_states[chat_id] = 'waiting_for_title'
        bot.send_message(chat_id, 'Напиши название книги и автора:')
    
    # Нажали кнопку "Мои книги"
    elif text == '📚 Мои книги':
        if not books_db:
            bot.send_message(chat_id, 'Ваш список книг пока пуст! 📭')
        else:
            response = "📖 Ваши книги:\n\n"
            for i, book in enumerate(books_db, 1):
                response += f"{i}. {book}\n"
            bot.send_message(chat_id, response)
            
    # Нажали кнопку "Факт"
    elif text == '🎲 Факт о книгах':
        bot.send_message(chat_id, '💡 Интересный факт: Самой продаваемой книгой всех времен является Библия!')

    # Нажали кнопку "Викторина"
    elif text == '❓ Викторина':
        bot.send_message(chat_id, '❓ Вопрос: Кто написал серию книг о Гарри Поттере?\n(Отправь имя автора)')

    # Сохраняем книгу, если бот ждал название
    elif user_states.get(chat_id) == 'waiting_for_title':
        books_db.append(text)
        user_states[chat_id] = None
        bot.send_message(chat_id, f'✅ Книга "{text}" успешно добавлена!', reply_markup=main_keyboard())

    else:
        bot.send_message(chat_id, 'Пожалуйста, выберите кнопку из меню ниже 👇', reply_markup=main_keyboard())

# --- 5. ZAPUSK ---
if __name__ == '__main__':
    print('Бот запущен...')
    bot.polling(non_stop=True)
