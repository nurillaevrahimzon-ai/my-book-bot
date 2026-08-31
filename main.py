import os
from threading import Thread
from flask import Flask

app = Flask('')


@app.route('/')
def home():
  return 'OK'


def run():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  Thread(target=run).start()


keep_alive()

import telebot
from telebot import types

TOKEN = "8725622521:AAE8psytiYFVm6adEELKgnbyIUdENXHDmhs"
bot = telebot.TeleBot(TOKEN)

# Список для хранения книг
# Структура: {"id": int, "title": str, "owner": str, "owner_id": int}
books_db = []
book_id_counter = 1

# Состояния пользователей
user_states = {}

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("📚 Каталог книг"), types.KeyboardButton("➕ Отдать книгу"))
    markup.row(types.KeyboardButton("❓ Помощь"))
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id, 
        "Привет! Я бот для обмена школьными учебниками.\nВыбери действие ниже:", 
        reply_markup=get_main_menu()
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    global book_id_counter
    chat_id = message.chat.id
    text = message.text

    # Процесс добавления книги
    if user_states.get(chat_id) == 'waiting_for_book':
        user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        
        book_info = {
            "id": book_id_counter,
            "title": text,
            "owner": user_name,
            "owner_id": chat_id
        }
        books_db.append(book_info)
        book_id_counter += 1
        user_states[chat_id] = None
        
        bot.send_message(
            chat_id, 
            f"✅ Книга «{text}» успешно добавлена в каталог!", 
            reply_markup=get_main_menu()
        )
        return

    # Каталог книг
    if text == "📚 Каталог книг":
        if not books_db:
            bot.send_message(chat_id, "📖 Каталог пока пуст. Никто ещё не добавил книги.")
        else:
            bot.send_message(chat_id, "📚 **Доступные книги для обмена:**")
            for book in books_db:
                markup = types.InlineKeyboardMarkup()
                
                # Если смотрим свою же книгу — даем кнопку «Удалить», если чужую — «Забрать»
                if book['owner_id'] == chat_id:
                    btn_delete = types.InlineKeyboardButton("🗑 Удалить мою книгу", callback_data=f"del_{book['id']}")
                    markup.add(btn_delete)
                else:
                    btn_take = types.InlineKeyboardButton("📖 Хочу забрать эту книгу", callback_data=f"take_{book['id']}")
                    markup.add(btn_take)
                
                bot.send_message(
                    chat_id, 
                    f"📌 **{book['title']}**\n👤 Отдает: {book['owner']}", 
                    reply_markup=markup, 
                    parse_mode="Markdown"
                )

    # Отдать книгу
    elif text == "➕ Отдать книгу":
        user_states[chat_id] = 'waiting_for_book'
        bot.send_message(
            chat_id, 
            "Напиши название учебника и класс (например: *Алгебра 8 класс*):", 
            parse_mode="Markdown"
        )

    # Помощь
    elif text == "❓ Помощь":
        bot.send_message(
            chat_id, 
            "💡 **Как работать с ботом:**\n"
            "1. Жми «➕ Отдать книгу», чтобы добавить свой учебник.\n"
            "2. В «📚 Каталог книг» жми «Хочу забрать», чтобы бот уведомил владельца!\n"
            "3. Свои книги можно удалять из каталога прямо кнопкой под сообщением.",
            parse_mode="Markdown"
        )

# Нажатие на «Хочу забрать»
@bot.callback_query_handler(func=lambda call: call.data.startswith('take_'))
def callback_take_book(call):
    book_id = int(call.data.split('_')[1])
    book = next((b for b in books_db if b['id'] == book_id), None)
    
    if book:
        buyer_name = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
        
        # Отправляем уведомление владельцу книги
        try:
            bot.send_message(
                book['owner_id'], 
                f"🔔 **Кто-то хочет забрать твою книгу!**\n\nПользователь {buyer_name} интересуется учебником: **«{book['title']}»**.\nСвяжись с ним для передачи!", 
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "Владельцу книги отправлено уведомление!")
            bot.send_message(call.message.chat.id, f"✅ Мы отправили сообщение владельцу ({book['owner']}). Скоро он свяжется с тобой!")
        except Exception:
            bot.answer_callback_query(call.id, "Не удалось отправить сообщение владельцу.")
    else:
        bot.answer_callback_query(call.id, "Эта книга уже недоступна.")

# Нажатие на «Удалить мою книгу»
@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def callback_delete_book(call):
    book_id = int(call.data.split('_')[1])
    global books_db
    
    # Удаляем книгу из списка
    books_db = [b for b in books_db if b['id'] != book_id]
    
    bot.answer_callback_query(call.id, "Книга удалена из каталога!")
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text="🗑 *Эта книга была удалена из каталога.*", 
        parse_mode="Markdown"
    )

print("Улучшенный бот запущен!")
bot.infinity_polling()
