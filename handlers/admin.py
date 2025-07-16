# admin.py
# Adminlarni boshqarish uchun handler va funksiyalar shu yerda bo'ladi. 

import sqlite3
from telegram import Update
from telegram.ext import CallbackContext
import logging
from db import get_admin_usernames, is_super_admin, is_protected_super_admin

logger = logging.getLogger(__name__)

# Foydalanuvchi admin ekanligini tekshirish funksiyasi
def is_admin(username):
    return username in get_admin_usernames() or is_super_admin(username)

# Foydalanuvchi yuqori darajadagi admin ekanligini tekshirish funksiyasi
def is_super_admin_func(username):
    return is_super_admin(username)

# Har qanday buyruqdan oldin adminlikni tekshirish
def admin_required(func):
    async def wrapper(update: Update, context: CallbackContext):
        if is_admin(update.message.from_user.username):
            await func(update, context)
        else:
            await update.message.reply_text("Siz bu buyruqdan foydalanish huquqiga ega emassiz.")
            logger.warning(f"Admin bo'lmagan foydalanuvchi buyruq berishga urindi: @{update.message.from_user.username}")
    return wrapper

# Adminlarni qo'shish funksiyasi
@admin_required
async def add_admin(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("Iltimos, admin qo'shish uchun username kiriting.")
        logger.warning("Admin username kiritilmagan")
        return

    new_admin = context.args[0].strip('@')
    if new_admin == "":
        await update.message.reply_text("Username noto'g'ri.")
        logger.warning("Username noto'g'ri formatda kiritilgan")
        return

    try:
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("INSERT INTO admins (username) VALUES (?)", (new_admin,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Foydalanuvchi @{new_admin} admin sifatida qo'shildi.")
        logger.info(f"Foydalanuvchi @{new_admin} admin sifatida qo'shildi.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"Foydalanuvchi @{new_admin} allaqachon admin.")
        logger.warning(f"Foydalanuvchi @{new_admin} allaqachon admin.")

# Adminlarni o'chirish funksiyasi
@admin_required
async def remove_admin(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("Iltimos, adminni olib tashlash uchun username kiriting.")
        logger.warning("Admin username kiritilmagan")
        return

    admin_to_remove = context.args[0].strip('@')
    if admin_to_remove == "":
        await update.message.reply_text("Username noto'g'ri.")
        logger.warning("Username noto'g'ri formatda kiritilgan")
        return

    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM admins WHERE username = ?", (admin_to_remove,))
        conn.commit()
        await update.message.reply_text(f"Foydalanuvchi @{admin_to_remove} adminlardan olib tashlandi.")
        logger.info(f"Foydalanuvchi @{admin_to_remove} adminlardan olib tashlandi.")
    except Exception as e:
        logger.error(f"Adminni o'chirishda xatolik: {e}")
    finally:
        conn.close()

# Adminlarni ro'yxatini ko'rsatish funksiyasi
@admin_required
async def list_admins(update: Update, context: CallbackContext):
    try:
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins")
        admins = c.fetchall()
        conn.close()

        if not admins:
            await update.message.reply_text("Ro'yxatda hech qanday admin yo'q.")
            logger.info("Adminlar ro'yxati bo'sh yuborildi")
            return

        admin_list = "\n".join(f"@{admin[0]}" for admin in admins)
        await update.message.reply_text(f"👨‍💻 RO'YXATDAGI ADMINLAR:\n{admin_list}")
        logger.info("Adminlar ro'yxati yuborildi")
    except Exception as e:
        logger.error(f"Adminlar ro'yxatini olishda xatolik: {e}")

# Adminlar qaysi guruhlarga biriktirilganini ko'rsatish funksiyasi
@admin_required
async def list_admin_groups(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("Iltimos, admin username'ini kiriting. Misol: /list_admin_groups @username")
        logger.warning("Admin username kiritilmagan")
        return

    admin_username = context.args[0].strip('@')
    if admin_username == "":
        await update.message.reply_text("Username noto'g'ri.")
        logger.warning("Username noto'g'ri formatda kiritilgan")
        return

    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT g.chat_name FROM admin_groups ag JOIN groups g ON ag.chat_id = g.chat_id WHERE ag.admin_username = ?", (admin_username,))
        groups = c.fetchall()
        conn.close()

        if not groups:
            await update.message.reply_text(f"Admin @{admin_username} hech qanday guruhga biriktirilmagan.")
            logger.warning(f"Admin @{admin_username} uchun guruhlar topilmadi")
            return

        group_list = "\n".join(f"{group[0]}" for group in groups)
        await update.message.reply_text(f"Admin @{admin_username} uchun biriktirilgan guruhlar:\n{group_list}")
        logger.info(f"Admin @{admin_username} uchun guruhlar ro'yxati yuborildi")
    except Exception as e:
        logger.error(f"Admin @{admin_username} uchun guruhlar ro'yxatini olishda xatolik: {e}") 