# superadmin.py
# Super-adminlar bilan ishlash uchun handler va funksiyalar shu yerda bo'ladi. 

import sqlite3
from telegram import Update
from telegram.ext import CallbackContext
import logging
from handlers.admin import is_super_admin_func
from db import is_protected_super_admin

logger = logging.getLogger(__name__)

def super_admin_required(func):
    async def wrapper(update: Update, context: CallbackContext):
        if is_super_admin_func(update.message.from_user.username):
            await func(update, context)
        else:
            await update.message.reply_text("Siz bu buyruqdan foydalanish huquqiga ega emassiz.")
            logger.warning(f"Super admin bo'lmagan foydalanuvchi buyruq berishga urindi: @{update.message.from_user.username}")
    return wrapper

# Super adminlarni qo'shish funksiyasi
@super_admin_required
async def add_super_admin(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("Iltimos, super admin qo'shish uchun username kiriting.")
        logger.warning("Super admin username kiritilmagan")
        return

    new_super_admin = context.args[0].strip('@')
    if new_super_admin == "":
        await update.message.reply_text("Username noto'g'ri.")
        logger.warning("Username noto'g'ri formatda kiritilgan")
        return

    try:
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("INSERT INTO super_admins (username) VALUES (?)", (new_super_admin,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Foydalanuvchi @{new_super_admin} super admin sifatida qo'shildi.")
        logger.info(f"Foydalanuvchi @{new_super_admin} super admin sifatida qo'shildi.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"Foydalanuvchi @{new_super_admin} allaqachon super admin.")
        logger.warning(f"Foydalanuvchi @{new_super_admin} allaqachon super admin.")

# Super adminlarni o'chirish funksiyasi
@super_admin_required
async def remove_super_admin(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("Iltimos, super adminni olib tashlash uchun username kiriting.")
        logger.warning("Super admin username kiritilmagan")
        return

    super_admin_to_remove = context.args[0].strip('@')
    if super_admin_to_remove == "":
        await update.message.reply_text("Username noto'g'ri.")
        logger.warning("Username noto'g'ri formatda kiritilgan")
        return

    if is_protected_super_admin(super_admin_to_remove):
        await update.message.reply_text("Bu super adminni o'chirib bo'lmaydi.")
        return

    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM super_admins WHERE username = ?", (super_admin_to_remove,))
        conn.commit()
        await update.message.reply_text(f"Foydalanuvchi @{super_admin_to_remove} super adminlardan olib tashlandi.")
        logger.info(f"Foydalanuvchi @{super_admin_to_remove} super adminlardan olib tashlandi.")
    except Exception as e:
        logger.error(f"Super adminni o'chirishda xatolik: {e}")
    finally:
        conn.close()

# Super adminlarni ro'yxatini ko'rsatish funksiyasi
@super_admin_required
async def list_super_admins(update: Update, context: CallbackContext):
    try:
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM super_admins")
        super_admins = c.fetchall()
        conn.close()

        if not super_admins:
            await update.message.reply_text("Ro'yxatda hech qanday super-admin yo'q.")
            logger.info("Super-adminlar ro'yxati bo'sh yuborildi")
            return

        super_admin_list = "\n".join(f"@{super_admin[0]}" for super_admin in super_admins)
        await update.message.reply_text(f"🥷 Ro'yxatdagi super-adminlar:\n{super_admin_list}")
        logger.info("Super-adminlar ro'yxati yuborildi")
    except Exception as e:
        logger.error(f"Super adminlar ro'yxatini olishda xatolik: {e}")

def ensure_initial_super_admin():
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO super_admins (username) VALUES (?)", ('Z_Mukhammadali',))
    conn.commit()
    conn.close() 