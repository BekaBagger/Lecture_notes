import telebot
from telebot import types
import database

# Инициализация базы данных при старте программы
database.init_db()

# ⚠️ ВАШИ ИНТЕГРИРОВАННЫЕ ДАННЫЕ
TOKEN = '8817683960:AAGMz7nBEsuq7TT3hhV-VOaFatm7C4moyAQ' 
ADMIN_ID = 904212184  # Ваш личный числовой ID администратора

try:
    bot = telebot.TeleBot(TOKEN)
except Exception as e:
    print(f"Критическая ошибка инициализации бота: {e}")

# Временное хранилище состояний пользователей
user_states = {}

# База знаний и справочные ответы
help_answers = {
    "о проекте": "Бот 'Lecture Notes' — это удобный сервис для хранения учебных конспектов с сортировкой по предметам, тегам и поддержкой файлов.",
    "как искать": "Нажмите кнопку 'Поиск 🔍' и выберите 'Показать всё' для вывода всех записей или 'Ручной поиск' для поиска по ключевым словам.",
    "общие базы": "Администратор может объединять пользователей в общие группы. Все участники группы будут видеть конспекты друг друга.",
    "теги": "Теги помогают группировать лекции (например: #экзамен, #лаба). Пишите их через запятую.",
    "автор": "Проект выполнен студентом в рамках курсовой/практической работы по теме №13."
}

# Функция-помощник для красивой отправки конспекта пользователю
def send_note_to_user(chat_id, note):
    subject, text, file_id, tags = note
    response = f"📘 **Предмет:** {subject}\n📝 **Конспект:** {text}\n🏷️ **Теги:** {tags}"
    
    if file_id != "None":
        try:
            bot.send_photo(chat_id, file_id, caption=response, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, response, parse_mode="Markdown")
            bot.send_document(chat_id, file_id)
    else:
        bot.send_message(chat_id, response, parse_mode="Markdown")

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    
    # Автоматическая регистрация пользователя в БД
    try:
        database.register_user(uid, message.from_user.username or "Без_Ника")
    except Exception:
        pass
        
    database.log_action(uid, "Команда /start")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("Добавить конспект 📝")
    btn2 = types.KeyboardButton("Поиск 🔍")
    btn3 = types.KeyboardButton("Помощь 📋")
    btn4 = types.KeyboardButton("О проекте ℹ️")
    markup.add(btn1, btn2, btn3, btn4)
    
    # Если зашел админ, добавляем кнопку админ-панели
    if uid == ADMIN_ID:
        btn_admin = types.KeyboardButton("🔑 Админ-панель")
        markup.add(btn_admin)
    
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}! 👋\nДобро пожаловать в сервис хранения конспектов 'Lecture Notes'.\n\nИспользуйте меню для создания записей, загрузки файлов и поиска.", 
        reply_markup=markup
    )

# --- ЛОГИКА АДМИН-ПАНЕЛИ (Просмотр юзеров и настройка общих баз) ---

@bot.message_handler(func=lambda m: m.text == "🔑 Админ-панель")
def admin_menu(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Доступ ограничен. Вы не являетесь администратором.")
        return
        
    inline_markup = types.InlineKeyboardMarkup(row_width=1)
    btn_users = types.InlineKeyboardButton("👥 Посмотреть всех пользователей", callback_data="admin_view_users")
    btn_share = types.InlineKeyboardButton("🔗 Настроить общую базу (группу)", callback_data="admin_manage_sharing")
    inline_markup.add(btn_users, btn_share)
    
    bot.send_message(message.chat.id, "--- 🛠️ ПАНЕЛЬ УПРАВЛЕНИЯ АДМИНИСТРАТОРА ---", reply_markup=inline_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    uid = call.from_user.id
    
    # Убираем анимацию загрузки с инлайн-кнопки
    bot.answer_callback_query(call.id)
    
    if uid != ADMIN_ID: return

    if call.data == "admin_view_users":
        try:
            users = database.get_all_users()
            if not users:
                bot.send_message(call.message.chat.id, "Пользователей в базе пока нет.")
                return
                
            report = "👥 <b>Зарегистрированные пользователи:</b>\n\n"
            for user_id, username in users:
                report += f"• ID: <code>{user_id}</code> — @{username}\n"
                
            bot.send_message(call.message.chat.id, report, parse_mode="HTML")
        except Exception as err:
            print(f"Ошибка вывода пользователей: {err}")
            bot.send_message(call.message.chat.id, "❌ Произошла ошибка при получении списка пользователей.")

    elif call.data == "admin_manage_sharing":
        user_states[uid] = {"step": "waiting_sharing_setup"}
        bot.send_message(
            call.message.chat.id, 
            "⚙️ **Создание общей базы данных:**\n\nВведите номер группы и ID пользователя через пробел, чтобы объединить их.\nФормат: `[номер_группы] [id_пользователя]`\nПример: `101 51928301`"
        )

def process_admin_sharing(message):
    uid = message.from_user.id
    try:
        group_id, target_user_id = map(int, message.text.strip().split())
        
        # Привязываем пользователя к группе в БД
        database.link_user_to_group(target_user_id, group_id)
        
        del user_states[uid]
        bot.send_message(message.chat.id, f"✅ Успешно! Пользователь `{target_user_id}` добавлен в общую базу группы `#{group_id}`.")
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Неверный формат. Введите два числа через пробел: `[номер_группы] [id_пользователя]`")

# --- ПРОЦЕСС ДОБАВЛЕНИЯ КОНСПЕКТА (Пошаговый мастер) ---

@bot.message_handler(func=lambda m: m.text == "Добавить конспект 📝")
def start_add_note(message):
    uid = message.from_user.id
    user_states[uid] = {"step": "waiting_subject"}
    bot.send_message(message.chat.id, "Шаг 1/4: Введите название учебного предмета (например, Высшая математика):")

def process_subject(message):
    uid = message.from_user.id
    user_states[uid]["subject"] = message.text.strip()
    user_states[uid]["step"] = "waiting_text"
    bot.send_message(message.chat.id, "Шаг 2/4: Введите текст конспекта / лекции:")

def process_text(message):
    uid = message.from_user.id
    user_states[uid]["note_text"] = message.text.strip()
    user_states[uid]["step"] = "waiting_file"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Пропустить загрузку файла 🚫")
    bot.send_message(message.chat.id, "Шаг 3/4: Отправьте файл/фотографию лекции или нажмите кнопку ниже:", reply_markup=markup)

def process_file(message):
    uid = message.from_user.id
    file_id = "None"
    if message.content_type == 'document': file_id = message.document.file_id
    elif message.content_type == 'photo': file_id = message.photo[-1].file_id
    
    user_states[uid]["file_id"] = file_id
    user_states[uid]["step"] = "waiting_tags"
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Шаг 4/4: Введите теги через запятую (например: #лекция, #важно):", reply_markup=markup)

def process_tags(message):
    uid = message.from_user.id
    tags = message.text.strip()
    data = user_states[uid]
    
    # Проверяем, состоит ли пользователь в общей группе
    group_id = database.get_user_group(uid)
    
    database.add_note(uid, data["subject"], data["note_text"], data["file_id"], tags, group_id)
    del user_states[uid]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Добавить конспект 📝", "Поиск 🔍", "Помощь 📋", "О проекте ℹ️")
    if uid == ADMIN_ID: markup.add("🔑 Админ-панель")
        
    bot.send_message(message.chat.id, "✅ Конспект успешно сохранен в базу данных!", reply_markup=markup)

# --- ИНТЕРАКТИВНЫЙ ПОИСК (ЛИЧНЫЙ + ОБЩИЙ) ---

@bot.message_handler(func=lambda m: m.text == "Поиск 🔍")
def start_search_menu(message):
    inline_markup = types.InlineKeyboardMarkup(row_width=1)
    btn_all = types.InlineKeyboardButton("📋 Показать все мои и общие конспекты", callback_data="search_all")
    btn_manual = types.InlineKeyboardButton("🔍 Ручной поиск по слову", callback_data="search_manual")
    inline_markup.add(btn_all, btn_manual)
    bot.send_message(message.chat.id, "Выберите метод поиска:", reply_markup=inline_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('search_'))
def handle_search_callbacks(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id) # Гасим часики загрузки
    
    if call.data == "search_all":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        results = database.search_notes(uid, "") 
        if not results:
            bot.send_message(call.message.chat.id, "Ваша база конспектов пуста.")
            return
        bot.send_message(call.message.chat.id, f"📋 Всего найдено записей: {len(results)}")
        for note in results: send_note_to_user(call.message.chat.id, note)
            
    elif call.data == "search_manual":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        user_states[uid] = {"step": "waiting_search_query"}
        bot.send_message(call.message.chat.id, "🔍 Введите ключевое слово, название предмета или тег:")

def process_manual_search(message):
    uid = message.from_user.id
    query = message.text.strip()
    results = database.search_notes(uid, query)
    del user_states[uid]
    if not results:
        bot.send_message(message.chat.id, f"По запросу '{query}' ничего не найдено.")
        return
    bot.send_message(message.chat.id, f"📚 Найдено совпадений: {len(results)}")
    for note in results: send_note_to_user(message.chat.id, note)

# --- ГЛОБАЛЬНЫЙ ТЕКСТОВЫЙ ОБРАБОТЧИК ---

@bot.message_handler(content_types=['text', 'photo', 'document'])
def global_handler(message):
    uid = message.from_user.id
    
    if uid in user_states:
        step = user_states[uid]["step"]
        if step == "waiting_subject": process_subject(message)
        elif step == "waiting_text": process_text(message)
        elif step == "waiting_file": process_file(message)
        elif step == "waiting_tags": process_tags(message)
        elif step == "waiting_search_query": process_manual_search(message)
        elif step == "waiting_sharing_setup": process_admin_sharing(message)
        return

    user_text = message.text.strip().lower() if message.text else ""
    if not user_text: return

    if user_text == "о проекте ℹ️":
        bot.send_message(message.chat.id, help_answers["о проекте"])
    elif user_text == "помощь 📋":
        response = "📋 Справочник команд бота:\n" + "\n".join([f"• {k.upper()} — {v}" for k, v in help_answers.items()])
        bot.send_message(message.chat.id, response)
    else:
        bot.reply_to(message, "⚠️ Пожалуйста, используйте кнопки меню для управления.")

if __name__ == '__main__':
    print("Русская версия 'Lecture Notes' успешно запущена...")
    bot.polling(none_stop=True)