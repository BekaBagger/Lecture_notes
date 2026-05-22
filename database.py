import sqlite3

DB_NAME = "lecture_notes.db"

def init_db():
    """Инициализация базы данных и создание всех таблиц"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            group_id INTEGER DEFAULT NULL
        )
    ''')
    
    # 2. Таблица заметок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            note_text TEXT,
            file_id TEXT,
            tags TEXT,
            group_id INTEGER DEFAULT NULL
        )
    ''')
    
    # 3. Таблица логов действий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def register_user(telegram_id, username):
    """Регистрация пользователя в системе"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (telegram_id, username) 
        VALUES (?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET username = EXCLUDED.username
    ''', (telegram_id, username))
    conn.commit()
    conn.close()

def get_all_users():
    """Получить список всех пользователей"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id, username FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def link_user_to_group(telegram_id, group_id):
    """Привязать пользователя к общей базе (группе)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET group_id = ? 
        WHERE telegram_id = ?
    ''', (group_id, telegram_id))
    conn.commit()
    conn.close()

def get_user_group(telegram_id):
    """Узнать группу пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT group_id FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def add_note(user_id, subject, note_text, file_id, tags, group_id=None):
    """Добавление новой заметки"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notes (user_id, subject, note_text, file_id, tags, group_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, subject, note_text, file_id, tags, group_id))
    conn.commit()
    conn.close()

def search_notes(user_id, query):
    """Поиск по личным и общим (групповым) заметкам"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    group_id = get_user_group(user_id)
    
    if group_id:
        sql = '''
            SELECT subject, note_text, file_id, tags FROM notes
            WHERE (user_id = ? OR group_id = ?)
            AND (subject LIKE ? OR note_text LIKE ? OR tags LIKE ?)
        '''
        params = (user_id, group_id, f'%{query}%', f'%{query}%', f'%{query}%')
    else:
        sql = '''
            SELECT subject, note_text, file_id, tags FROM notes
            WHERE user_id = ?
            AND (subject LIKE ? OR note_text LIKE ? OR tags LIKE ?)
        '''
        params = (user_id, f'%{query}%', f'%{query}%', f'%{query}%')
        
    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()
    return results

def log_action(user_id, action):
    """Запись логов"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO logs (user_id, action) VALUES (?, ?)', (user_id, action))
    conn.commit()
    conn.close()