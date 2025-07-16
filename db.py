# db.py
# Ma'lumotlar bazasi bilan ishlash uchun funksiyalar shu yerda bo'ladi. 

import sqlite3
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Ma'lumotlar bazasini yaratish funksiyasi
def create_tables():
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS admins (username TEXT PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS super_admins (username TEXT PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (chat_id INTEGER, user_id INTEGER, username TEXT, message_time TEXT, message_type TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, chat_name TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_ids (username TEXT PRIMARY KEY, chat_id INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admin_groups (admin_username TEXT, chat_id INTEGER, PRIMARY KEY (admin_username, chat_id), FOREIGN KEY (admin_username) REFERENCES admins(username), FOREIGN KEY (chat_id) REFERENCES groups(chat_id))''')
        conn.commit()
        logger.info("Ma'lumotlar bazasi muvaffaqiyatli yaratildi")
    except Exception as e:
        logger.error(f"Ma'lumotlar bazasini yaratishda xatolik: {e}")
    finally:
        conn.close()

def get_admin_usernames():
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT username FROM admins")
    admins = c.fetchall()
    conn.close()
    return [admin[0] for admin in admins]

def get_super_admin_usernames():
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT username FROM super_admins")
    super_admins = c.fetchall()
    conn.close()
    return [super_admin[0] for super_admin in super_admins]

async def get_chat_id_by_username(username):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT chat_id FROM user_ids WHERE username=?", (username,))
        result = c.fetchone()
        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        logger.error(f"Error retrieving chat_id for {username}: {e}")
        return None
    finally:
        conn.close()

def get_admin_groups(admin_username):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM admin_groups WHERE admin_username = ?", (admin_username,))
    groups = c.fetchall()
    conn.close()
    return [group[0] for group in groups]

def is_super_admin(username):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT username FROM super_admins WHERE username = ?", (username,))
    super_admin = c.fetchone()
    conn.close()
    return super_admin is not None

def save_chat_id(username, chat_id):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO user_ids (username, chat_id) VALUES (?, ?)", (username, chat_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Chat ID saqlashda xatolik: {e}")
    finally:
        conn.close()

def get_group_name(chat_id):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT chat_name FROM groups WHERE chat_id = ?", (chat_id,))
    group = c.fetchone()
    conn.close()
    return group[0] if group else "Unknown"

def get_groups():
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups WHERE chat_name IS NOT NULL AND chat_name != ''")
    groups = c.fetchall()
    conn.close()
    return [group[0] for group in groups]

def add_initial_admin():
    initial_admin = 'Z_Mukhammadali'
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO super_admins (username) VALUES (?)", (initial_admin,))
        c.execute("INSERT INTO admins (username) VALUES (?)", (initial_admin,))
        conn.commit()
        logger.info(f"Foydalanuvchi @{initial_admin} boshlang'ich super admin va admin sifatida qo'shildi.")
    except sqlite3.IntegrityError:
        logger.info(f"Foydalanuvchi @{initial_admin} allaqachon super admin yoki admin.")
    except Exception as e:
        logger.error(f"Boshlang'ich super adminni qo'shishda xatolik: {e}")
    finally:
        conn.close()

def is_initial_super_admin(username):
    return username == 'Z_Mukhammadali'

def ensure_initial_super_admin():
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO super_admins (username) VALUES (?)", ("Z_Mukhammadali",))
    conn.commit()
    conn.close()

def is_protected_super_admin(username):
    return username == "Z_Mukhammadali" 