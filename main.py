import os
import telebot
from telebot import types
from flask import Flask, request

# Получаем токен из настроек Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# Главное меню с кнопками 🔘
def get_main_keyboard():
    keyboard = types.InlineKeyboardMarkup()
        
            # Создаем кнопки
                btn_books = types.InlineKeyboardButton(text="📚 Книги", callback_data="books")
                    btn_facts = types.InlineKeyboardButton(text="💡 Факты", callback_data="facts")
                        btn_weather = types.InlineKeyboardButton(text="🌦️ Погода", callback_data="weather")
                            btn_music = types.InlineKeyboardButton(text="🎵 Музыка", callback_data="music")
                                
                                    # Добавляем их по парам в каждый ряд
                                        keyboard.add(btn_books, btn_facts)
                                            keyboard.add(btn_weather, btn_music)
                                                
                                                    return keyboard

                                                    # Обработка команды /start
                                                    @bot.message_handler(commands=['start'])
                                                    def start_message(message):
                                                        bot.send_message(
                                                                message.chat.id, 
                                                                        "Привет! Выбери нужный раздел из меню ниже: 👇", 
                                                                                reply_markup=get_main_keyboard()
                                                                                    )

                                                                                    # Обработка нажатий на кнопки 🖱️
                                                                                    @bot.callback_query_handler(func=lambda call: True)
                                                                                    def handle_menu_click(call):
                                                                                        # Обязательно убираем значок загрузки с кнопки 🔄
                                                                                            bot.answer_callback_query(call.id)
                                                                                                
                                                                                                    if call.data == "books":
                                                                                                            bot.send_message(call.message.chat.id, "📚 Раздел с PDF-книгами скоро появится!")
                                                                                                                elif call.data == "facts":
                                                                                                                        bot.send_message(call.message.chat.id, "💡 Раздел со случайными фактами в разработке!")
                                                                                                                            elif call.data == "weather":
                                                                                                                                    bot.send_message(call.message.chat.id, "🌦️ Раздел с погодой скоро будет готов!")
                                                                                                                                        elif call.data == "music":
                                                                                                                                                bot.send_message(call.message.chat.id, "🎵 Раздел с музыкой скоро заработает!")

                                                                                                                                                # Маршруты для Webhook Flask 🌐
                                                                                                                                                @app.route('/' + BOT_TOKEN, methods=['POST'])
                                                                                                                                                def getMessage():
                                                                                                                                                    json_string = request.get_data().decode('utf-8')
                                                                                                                                                        update = telebot.types.Update.de_json(json_string)
                                                                                                                                                            bot.process_new_updates([update])
                                                                                                                                                                return "!", 200

                                                                                                                                                                @app.route("/")
                                                                                                                                                                def webhook():
                                                                                                                                                                    bot.remove_webhook()
                                                                                                                                                                        # Твой URL на Render
                                                                                                                                                                            bot.set_webhook(url='https://my-book-bot-9ga9.onrender.com/' + BOT_TOKEN)
                                                                                                                                                                                return "Bot is running!", 200

                                                                                                                                                                                if __name__ == "__main__":
                                                                                                                                                                                    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
                                                                                                                                                                                    
