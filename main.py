import logging
import warnings
logging.basicConfig(level=logging.ERROR)
warnings.filterwarnings("ignore", category=DeprecationWarning)
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from db import get_admin_groups
from handlers.admin import add_admin, remove_admin, list_admins, list_admin_groups, admin_required, is_admin
from handlers.group import add_group, remove_group, list_groups, group_stats, all_group_stats, add_admin_group
from handlers.stats import send_weekly_stats_command, send_monthly_stats_command, send_weekly_stats, send_monthly_stats
from handlers.superadmin import add_super_admin, remove_super_admin, list_super_admins, super_admin_required, ensure_initial_super_admin
from handlers.help import start, help_command
from db import create_tables, add_initial_admin, get_groups, get_group_name, save_chat_id, ensure_initial_super_admin, is_protected_super_admin, is_super_admin
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import CallbackContext
from utils import main_keyboard
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import sqlite3
from datetime import datetime
from aiogram import types, Dispatcher

BOT_TOKEN = '7401093404:AAH1IJBCDheyk8TASChqRHE13uukv0mu0-Q'

# --- Tugmali buyruqlar uchun umumiy handler ---
async def button_handler(update: Update, context: CallbackContext):
    user = update.message.from_user
    if not user.username:
        await update.message.reply_text("Sizda Telegram username yo‘q. Botdan foydalanish uchun Telegram username o‘rnating (Sozlamalar > Username).", reply_markup=main_keyboard)
        return
    username = user.username
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    text = update.message.text
    # 'Boshlash' tugmasi shaxsiy chatda bosilganda menyu chiqsin
    if text in ["Boshlash", "Boshlash"] and chat_type == "private":
        await update.message.reply_text(
            "Assalomu alaykum! Botga xush kelibsiz! Quyidagi menyudan kerakli bo'limni tanlang:",
            reply_markup=main_keyboard
        )
        return
    # Har safar shaxsiy chatda tugma bosilsa, chat_id ni saqlash
    if chat_type == "private":
        save_chat_id(username, chat_id)
    if not (is_admin(username) or is_super_admin(username)):
        await update.message.reply_text("Sizda botdan foydalanish huquqi yo'q.")
        return
    # --- Faqat super-adminlar uchun Guruh statistikasi ---
    if text in ["Guruh statistikasi", "Guruh statistikasi"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        group_ids = get_groups()
        if not group_ids:
            await update.message.reply_text("Bazada hech qanday guruh yo'q.", reply_markup=main_keyboard)
            return
        group_names = [get_group_name(gid) for gid in group_ids]
        keyboard = ReplyKeyboardMarkup([[name] for name in group_names], resize_keyboard=True)
        await update.message.reply_text("Guruhni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_superadmin_group_stats'] = True
        context.user_data['superadmin_group_stats_group_names'] = group_names
        return
    elif context.user_data.get('awaiting_superadmin_group_stats'):
        group_name = text
        group_names = context.user_data.get('superadmin_group_stats_group_names', [])
        if group_name not in group_names:
            await update.message.reply_text("Bunday guruh topilmadi. Iltimos, ro'yxatdan tanlang.", reply_markup=main_keyboard)
            context.user_data['awaiting_superadmin_group_stats'] = False
            return
        context.user_data['selected_superadmin_group_for_stats'] = group_name
        context.user_data['awaiting_superadmin_group_stats'] = False
        context.user_data['awaiting_superadmin_stats_period'] = True
        period_keyboard = ReplyKeyboardMarkup([
            ["7 kunlik"],
            ["30 kunlik"]
        ], resize_keyboard=True)
        await update.message.reply_text("Statistika davrini tanlang:", reply_markup=period_keyboard)
        return
    elif context.user_data.get('awaiting_superadmin_stats_period'):
        period = text
        group_name = context.user_data.get('selected_superadmin_group_for_stats')
        if not group_name:
            await update.message.reply_text("Guruh tanlanmagan.", reply_markup=main_keyboard)
            context.user_data['awaiting_superadmin_stats_period'] = False
            return
        group_ids = get_groups()
        group_names = [get_group_name(gid) for gid in group_ids]
        if group_name not in group_names:
            await update.message.reply_text("Bunday guruh topilmadi.", reply_markup=main_keyboard)
            context.user_data['awaiting_superadmin_stats_period'] = False
            return
        chat_id = group_ids[group_names.index(group_name)]
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        from handlers.stats import format_stats_message
        if period == "30 kunlik":
            c.execute("SELECT username, COUNT(*), MAX(message_time) FROM messages WHERE chat_id = ? AND substr(message_time, 1, 10) >= date('now', '-30 days') GROUP BY username", (chat_id,))
            stats = c.fetchall()
            message = format_stats_message(group_name, [(row[0], row[1], row[2]) for row in stats], "Oylik")
        elif period == "7 kunlik":
            c.execute("SELECT username, COUNT(*), MAX(message_time) FROM messages WHERE chat_id = ? AND substr(message_time, 1, 10) >= date('now', '-7 days') GROUP BY username", (chat_id,))
            stats = c.fetchall()
            message = format_stats_message(group_name, [(row[0], row[1], row[2]) for row in stats], "Haftalik")
        else:
            await update.message.reply_text("Noto'g'ri davr tanlandi.", reply_markup=main_keyboard)
            context.user_data['awaiting_superadmin_stats_period'] = False
            return
        conn.close()
        await update.message.reply_text(message, reply_markup=main_keyboard)
        context.user_data['awaiting_superadmin_stats_period'] = False
        context.user_data['selected_superadmin_group_for_stats'] = None
        context.user_data['superadmin_group_stats_group_names'] = None
        return
    elif text in ["Yordam", "Yordam"]:
        await help_command(update, context)
    elif text in ["Guruh qo'shish", "Guruh qo'shish"]:
        await add_group(update, context)
    elif text in ["Guruhni o'chirish", "Guruhni o'chirish"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        if chat_type != "private":
            await update.message.reply_text("⚠️ Iltimos, bu buyruqni botning shaxsiy chatida yuboring")
            return
        # Guruhlarni tugma ko'rinishida chiqarish
        group_ids = get_groups()
        if not group_ids:
            await update.message.reply_text("Bazada hech qanday guruh yo'q.", reply_markup=main_keyboard)
            return
        group_names = [get_group_name(gid) for gid in group_ids]
        keyboard = ReplyKeyboardMarkup([[name] for name in group_names], resize_keyboard=True)
        await update.message.reply_text("O'chirmoqchi bo'lgan guruhni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_group_delete'] = True
        return
    elif text in ["Guruhlar ro'yxati", "Guruhlar ro'yxati"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        await list_groups(update, context)
    elif text in ["Adminlar ro'yxati", "Adminlar ro'yxati"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        await list_admins(update, context)
    elif text in ["Admin qo'shish", "Admin qo'shish"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        await update.message.reply_text("Adminning usernameni kiriting (masalan, @username):")
        context.user_data['awaiting_admin_username'] = True
        return
    elif text in ["Adminni olib tashlash", "Adminni olib tashlash"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        # Adminlarni ro'yxatini tugmali ko'rinishda chiqarish
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins")
        admins = [row[0] for row in c.fetchall()]
        conn.close()
        if not admins:
            await update.message.reply_text("Ro'yxatda hech qanday admin yo'q.", reply_markup=main_keyboard)
            return
        keyboard = ReplyKeyboardMarkup([[f"@{admin}"] for admin in admins], resize_keyboard=True)
        await update.message.reply_text("Adminning usernameni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_admin_remove'] = True
        return
    elif text in ["Super-adminlar ro'yxati", "Super-adminlar ro'yxati"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        await list_super_admins(update, context)
    elif text in ["Super-admin qo'shish", "Super-admin qo'shish"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        await update.message.reply_text("Super-adminning usernameni kiriting (masalan, @username):")
        context.user_data['awaiting_super_admin_username'] = True
        return
    elif text in ["Super-adminni olib tashlash", "Super-adminni olib tashlash"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        # Super-adminlarni ro'yxatini tugmali ko'rinishda chiqarish
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM super_admins")
        super_admins = [row[0] for row in c.fetchall()]
        conn.close()
        if not super_admins:
            await update.message.reply_text("Ro'yxatda hech qanday super-admin yo'q.", reply_markup=main_keyboard)
            return
        keyboard = ReplyKeyboardMarkup([[f"@{sa}"] for sa in super_admins], resize_keyboard=True)
        await update.message.reply_text("Super-adminning usernameni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_super_admin_remove'] = True
        return
    elif text in ["Barcha guruh statistikasi", "Barcha guruh statistikasi"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        await all_group_stats(update, context)
    elif text in ["Kunlik statistika", "Kunlik statistika"]:
        await update.message.reply_text("Kunlik statistika funksiyasi o'chirilgan yoki mavjud emas.")
    elif text in ["Haftalik statistika", "Haftalik statistika"]:
        await send_weekly_stats_command(update, context)
    elif text in ["Oylik statistika", "Oylik statistika"]:
        await send_monthly_stats_command(update, context)
    elif text in ["30 kunlik statistika", "30 kunlik statistika"]:
        if chat_type != "private":
            return  # Faqat shaxsiy chatda ishlasin, guruhda umuman javob bermasin
        from datetime import datetime, timedelta
        username = user.username
        # Super-admin bo'lsa — barcha guruhlar, aks holda faqat unga biriktirilganlar
        if is_super_admin(username):
            group_ids = get_groups()
        else:
            group_ids = get_admin_groups(username)
        if not group_ids:
            await update.message.reply_text("⚠️ Sizga biriktirilgan guruh(lar) yo‘q.", reply_markup=main_keyboard)
            return
        now = datetime.utcnow()
        start = now - timedelta(days=30)
        start_str = start.strftime("%Y-%m-%d")
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        found = False
        for gid in group_ids:
            group_name = get_group_name(gid)
            c.execute("""
                SELECT username, COUNT(*)
                FROM messages
                WHERE chat_id = ?
                  AND substr(message_time, 1, 10) >= ?
                GROUP BY username
                ORDER BY COUNT(*) DESC
            """, (gid, start_str))
            rows = c.fetchall()
            text = f"📊 <b>{group_name}</b> (oxirgi 30 kun):\n"
            if rows:
                for username, count in rows:
                    text += f"• @{username}: {count} ta xabar\n"
                found = True
            else:
                text += "• Hech qanday xabar yo‘q\n"
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard)
        conn.close()
        if not found:
            await update.message.reply_text("Sizga biriktirilgan guruhlar uchun 30 kunlik statistik ma'lumot topilmadi.", reply_markup=main_keyboard)
        return
    elif text in ["Haftalik statistika", "Haftalik statistika"]:
        if chat_type != "private":
            return
        from handlers.stats import format_stats_message
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT chat_id, username, COUNT(*), MAX(message_time) FROM messages WHERE substr(message_time, 1, 10) >= date('now', '-7 days') GROUP BY chat_id, username")
        stats = c.fetchall()
        conn.close()
        if is_super_admin(username):
            group_ids = get_groups()
        else:
            group_ids = get_admin_groups(username)
        if not group_ids:
            await update.message.reply_text("Sizga biriktirilgan hech qanday guruh yo'q.", reply_markup=main_keyboard)
            return
        found = False
        for gid in group_ids:
            group_name = get_group_name(gid)
            group_stats = [(row[1], row[2], row[3]) for row in stats if row[0] == gid]
            if group_stats:
                message = format_stats_message(group_name, group_stats, "Haftalik")
                await update.message.reply_text(message, reply_markup=main_keyboard)
                found = True
        if not found:
            await update.message.reply_text("Sizga biriktirilgan guruhlar uchun 7 kunlik statistik ma'lumot topilmadi.", reply_markup=main_keyboard)
        return
    elif context.user_data.get('awaiting_group_delete'):
        # Guruh nomi tanlandi, o'chirishga harakat qilamiz
        group_name = text
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT chat_id FROM groups WHERE chat_name = ?", (group_name,))
        group = c.fetchone()
        if not group:
            await update.message.reply_text("Bunday guruh topilmadi yoki allaqachon o'chirilgan.", reply_markup=main_keyboard)
            context.user_data['awaiting_group_delete'] = False
            return
        c.execute("DELETE FROM groups WHERE chat_id = ?", (group[0],))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Guruh '{group_name}' muvaffaqiyatli o'chirildi.", reply_markup=main_keyboard)
        context.user_data['awaiting_group_delete'] = False
        return
    elif context.user_data.get('awaiting_admin_username'):
        # Foydalanuvchi admin username kiritmoqda
        username = text.strip().lstrip('@')
        if not username:
            await update.message.reply_text("Username noto'g'ri. Qaytadan kiriting (masalan, @username):")
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO admins (username) VALUES (?)", (username,))
            conn.commit()
            await update.message.reply_text(f"Foydalanuvchi @{username} adminlar ro'yxatiga qo'shildi.")
        except sqlite3.IntegrityError:
            await update.message.reply_text(f"Foydalanuvchi @{username} allaqachon adminlar ro'yxatida mavjud.")
        finally:
            conn.close()
        context.user_data['awaiting_admin_username'] = False
        return
    elif context.user_data.get('awaiting_admin_remove'):
        # Foydalanuvchi adminni tanladi, ro'yxatdan o'chiramiz
        username = text.strip().lstrip('@')
        if is_protected_super_admin(username):
            await update.message.reply_text("Bu super adminni o'chirib bo'lmaydi.", reply_markup=main_keyboard)
            context.user_data['awaiting_admin_remove'] = False
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins WHERE username = ?", (username,))
        exists = c.fetchone()
        if not exists:
            await update.message.reply_text("Bunday admin topilmadi yoki allaqachon o'chirilgan.", reply_markup=main_keyboard)
            context.user_data['awaiting_admin_remove'] = False
            conn.close()
            return
        c.execute("DELETE FROM admins WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Foydalanuvchi @{username} adminlar ro'yxatidan o'chirildi.", reply_markup=main_keyboard)
        context.user_data['awaiting_admin_remove'] = False
        return
    elif context.user_data.get('awaiting_super_admin_username'):
        # Foydalanuvchi super-admin username kiritmoqda
        username = text.strip().lstrip('@')
        if not username:
            await update.message.reply_text("Username noto'g'ri. Qaytadan kiriting (masalan, @username):")
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO super_admins (username) VALUES (?)", (username,))
            conn.commit()
            await update.message.reply_text(f"Foydalanuvchi @{username} super-adminlar ro'yxatiga qo'shildi.")
        except sqlite3.IntegrityError:
            await update.message.reply_text(f"Foydalanuvchi @{username} allaqachon super-adminlar ro'yxatida mavjud.")
        finally:
            conn.close()
        context.user_data['awaiting_super_admin_username'] = False
        return
    elif context.user_data.get('awaiting_super_admin_remove'):
        # Foydalanuvchi super-adminni tanladi, ro'yxatdan o'chiramiz
        username = text.strip().lstrip('@')
        if is_protected_super_admin(username):
            await update.message.reply_text("Bu super adminni o'chirib bo'lmaydi.", reply_markup=main_keyboard)
            context.user_data['awaiting_super_admin_remove'] = False
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM super_admins WHERE username = ?", (username,))
        exists = c.fetchone()
        if not exists:
            await update.message.reply_text("Bunday super-admin topilmadi yoki allaqachon o'chirilgan.", reply_markup=main_keyboard)
            context.user_data['awaiting_super_admin_remove'] = False
            conn.close()
            return
        c.execute("DELETE FROM super_admins WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Foydalanuvchi @{username} super-adminlar ro'yxatidan o'chirildi.", reply_markup=main_keyboard)
        context.user_data['awaiting_super_admin_remove'] = False
        return
    # --- ADMINNI GURUHGA BIRIKTIRISH ---
    elif text in ["Adminni guruhga biriktirish", "Adminni guruhga biriktirish"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins")
        admins = [row[0] for row in c.fetchall()]
        conn.close()
        if not admins:
            await update.message.reply_text("Ro'yxatda hech qanday admin yo'q.", reply_markup=main_keyboard)
            return
        keyboard = ReplyKeyboardMarkup([[f"@{admin}"] for admin in admins], resize_keyboard=True)
        await update.message.reply_text("Adminni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_admin_for_group_attach'] = True
        return
    elif context.user_data.get('awaiting_admin_for_group_attach'):
        admin_username = text.strip().lstrip('@')
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins WHERE username = ?", (admin_username,))
        exists = c.fetchone()
        if not exists:
            await update.message.reply_text("Bunday admin topilmadi.", reply_markup=main_keyboard)
            context.user_data['awaiting_admin_for_group_attach'] = False
            conn.close()
            return
        c.execute("SELECT chat_name FROM groups")
        groups = [row[0] for row in c.fetchall()]
        conn.close()
        if not groups:
            await update.message.reply_text("Hech qanday guruh ro'yxatda mavjud emas.", reply_markup=main_keyboard)
            context.user_data['awaiting_admin_for_group_attach'] = False
            return
        context.user_data['selected_admin_for_group_attach'] = admin_username
        keyboard = ReplyKeyboardMarkup([[name] for name in groups], resize_keyboard=True)
        await update.message.reply_text("Guruhni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_group_for_admin_attach'] = True
        context.user_data['awaiting_admin_for_group_attach'] = False
        return
    elif context.user_data.get('awaiting_group_for_admin_attach'):
        group_name = text
        admin_username = context.user_data.get('selected_admin_for_group_attach')
        if not admin_username:
            await update.message.reply_text("Admin tanlanmagan.", reply_markup=main_keyboard)
            context.user_data['awaiting_group_for_admin_attach'] = False
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT chat_id FROM groups WHERE chat_name = ?", (group_name,))
        group = c.fetchone()
        if not group:
            await update.message.reply_text("Bunday guruh topilmadi.", reply_markup=main_keyboard)
            context.user_data['awaiting_group_for_admin_attach'] = False
            conn.close()
            return
        chat_id = group[0]
        try:
            c.execute("INSERT INTO admin_groups (admin_username, chat_id) VALUES (?, ?)", (admin_username, chat_id))
            conn.commit()
            await update.message.reply_text(f"Admin @{admin_username} guruh '{group_name}' uchun biriktirildi.", reply_markup=main_keyboard)
        except sqlite3.IntegrityError:
            await update.message.reply_text(f"Admin @{admin_username} allaqachon guruh '{group_name}' uchun biriktirilgan.", reply_markup=main_keyboard)
        finally:
            conn.close()
        context.user_data['awaiting_group_for_admin_attach'] = False
        context.user_data['selected_admin_for_group_attach'] = None
        return
    # --- ADMINNI BIRIKTIRILGAN GURUHDAN O'CHIRISH ---
    elif text in ["Adminni biriktirilgan guruhdan o'chirish", "Adminni biriktirilgan guruhdan o'chirish"]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins")
        admins = [row[0] for row in c.fetchall()]
        conn.close()
        if not admins:
            await update.message.reply_text("Ro'yxatda hech qanday admin yo'q.", reply_markup=main_keyboard)
            return
        keyboard = ReplyKeyboardMarkup([[f"@{admin}"] for admin in admins], resize_keyboard=True)
        await update.message.reply_text("Adminni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_admin_for_group_unlink'] = True
        return
    elif context.user_data.get('awaiting_admin_for_group_unlink'):
        admin_username = text.strip().lstrip('@')
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins WHERE username = ?", (admin_username,))
        exists = c.fetchone()
        if not exists:
            await update.message.reply_text("Bunday admin topilmadi.", reply_markup=main_keyboard)
            context.user_data['awaiting_admin_for_group_unlink'] = False
            conn.close()
            return
        c.execute("SELECT g.chat_name FROM admin_groups ag JOIN groups g ON ag.chat_id = g.chat_id WHERE ag.admin_username = ?", (admin_username,))
        groups = [row[0] for row in c.fetchall()]
        conn.close()
        if not groups:
            await update.message.reply_text("Bu admin hech qanday guruhga biriktirilmagan.", reply_markup=main_keyboard)
            context.user_data['awaiting_admin_for_group_unlink'] = False
            return
        context.user_data['selected_admin_for_group_unlink'] = admin_username
        keyboard = ReplyKeyboardMarkup([[name] for name in groups], resize_keyboard=True)
        await update.message.reply_text("Guruhni tanlang:", reply_markup=keyboard)
        context.user_data['awaiting_group_for_admin_unlink'] = True
        context.user_data['awaiting_admin_for_group_unlink'] = False
        return
    elif context.user_data.get('awaiting_group_for_admin_unlink'):
        group_name = text
        admin_username = context.user_data.get('selected_admin_for_group_unlink')
        if not admin_username:
            await update.message.reply_text("Admin tanlanmagan.", reply_markup=main_keyboard)
            context.user_data['awaiting_group_for_admin_unlink'] = False
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT chat_id FROM groups WHERE chat_name = ?", (group_name,))
        group = c.fetchone()
        if not group:
            await update.message.reply_text("Bunday guruh topilmadi.", reply_markup=main_keyboard)
            context.user_data['awaiting_group_for_admin_unlink'] = False
            conn.close()
            return
        chat_id = group[0]
        c.execute("DELETE FROM admin_groups WHERE admin_username = ? AND chat_id = ?", (admin_username, chat_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Admin @{admin_username} guruh '{group_name}'dan o'chirildi.", reply_markup=main_keyboard)
        context.user_data['awaiting_group_for_admin_unlink'] = False
        context.user_data['selected_admin_for_group_unlink'] = None
        return
    elif text in ["Biriktirilgan adminning guruhlari", "Biriktirilgan adminning guruhlari "]:
        if not is_super_admin(username):
            await update.message.reply_text("Bu amal faqat super-adminlar uchun ruxsat etilgan.", reply_markup=main_keyboard)
            return
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT username FROM admins")
        admins = [row[0] for row in c.fetchall()]
        if not admins:
            await update.message.reply_text("Ro'yxatda hech qanday admin yo'q.", reply_markup=main_keyboard)
            conn.close()
            return
        await update.message.reply_text("🖋 BARCHA ADMINLARGA BIRIKTIRILGAN GURUHLAR:", reply_markup=main_keyboard)
        for idx, admin in enumerate(admins, 1):
            c.execute("SELECT g.chat_name FROM admin_groups ag JOIN groups g ON ag.chat_id = g.chat_id WHERE ag.admin_username = ?", (admin,))
            groups = [row[0] for row in c.fetchall()]
            if groups:
                group_list = '\n'.join(f"- {g}" for g in groups)
            else:
                group_list = "- Hech qanday guruh biriktirilmagan"
            msg = f"{idx}. @{admin} ga biriktirilgan guruhlar\n{group_list}"
            await update.message.reply_text(msg, reply_markup=main_keyboard)
        conn.close()
        return
    else:
        await update.message.reply_text("Noma'lum buyruq yoki tugma.")

# --- Guruhdagi barcha xabarlarni bazaga yozish uchun handler ---
async def group_message_logger(update: Update, context: CallbackContext):
    chat_type = update.message.chat.type
    if chat_type not in ["group", "supergroup"]:
        return
    user = update.message.from_user
    username = user.username or f"id{user.id}"
    user_id = user.id
    chat_id = update.message.chat.id

    # Xabar turini aniqlash
    if update.message.text is not None and update.message.text.strip() != "":
        msg_type = "text"
    elif update.message.sticker is not None:
        msg_type = "sticker"
    elif update.message.photo is not None:
        msg_type = "photo"
    elif update.message.video is not None:
        msg_type = "video"
    elif update.message.document is not None:
        msg_type = "document"
    elif update.message.voice is not None:
        msg_type = "voice"
    elif update.message.audio is not None:
        msg_type = "audio"
    elif update.message.contact is not None:
        msg_type = "contact"
    elif update.message.location is not None:
        msg_type = "location"
    elif update.message.video_note is not None:
        msg_type = "video_note"
    else:
        msg_type = "other"

    # Faqat haqiqiy xabarlar uchun log qilamiz
    if msg_type == "text" and not (
        (update.message.text and update.message.text.strip() != "") or
        (update.message.caption and update.message.caption.strip() != "")
    ):
        return

    tz = pytz.timezone('Asia/Tashkent')
    now_tashkent = datetime.now(tz).replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO messages (chat_id, user_id, username, message_time, message_type) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, user_id, username, now_tashkent, msg_type))
        conn.commit()
    except Exception as e:
        pass
    finally:
        conn.close()
    # Faqat shaxsiy chat uchun save_chat_id
    if update.message.chat.type == "private":
        save_chat_id(username, chat_id)
    return

# --- DEBUG LOGGER ---
async def debug_logger(update: Update, context: CallbackContext):
    print(f"DEBUG: {update}")

# --- Custom /start handler enforcing group/admin logic ---
async def start_command_handler(update: Update, context: CallbackContext):
    from utils import main_keyboard
    import logging
    user = update.message.from_user
    username = user.username if user and user.username else None
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    text = update.message.text
    from handlers.admin import is_admin
    from db import is_super_admin
    log_msg = f"/start command: user={username}, chat_id={chat_id}, chat_type={chat_type}, text={text}"
    logging.warning(log_msg)
    print(log_msg)
    # Faqat admin yoki super-admin uchun ishlasin
    if not (is_admin(username) or is_super_admin(username)):
        return  # Oddiy foydalanuvchiga umuman javob bermaydi
    if chat_type in ["group", "supergroup"]:
        # Guruhni avtomatik bazaga qo'shish
        chat_name = update.message.chat.title or "Unknown"
        import sqlite3
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT chat_id FROM groups WHERE chat_id = ?", (chat_id,))
        already_exists = c.fetchone()
        if already_exists:
            await update.message.reply_text(
                f"Guruh '{chat_name}' allaqachon ro'yxatda mavjud.",
                reply_markup=ReplyKeyboardRemove()
            )
            logging.info(f"Group already exists: {chat_id} - {chat_name}")
        else:
            c.execute("INSERT INTO groups (chat_id, chat_name) VALUES (?, ?)", (chat_id, chat_name))
            conn.commit()
            await update.message.reply_text(
                f"Guruh '{chat_name}' ro'yxatga qo'shildi.",
                reply_markup=ReplyKeyboardRemove()
            )
            logging.info(f"Group added: {chat_id} - {chat_name}")
        conn.close()
    else:
        # Faqat shaxsiy chatda menyu
        await update.message.reply_text(
            "Assalomu alaykum! Botga xush kelibsiz! Quyidagi menyudan kerakli bo'limni tanlang:",
            reply_markup=main_keyboard
        )

# --- Inline tugma uchun handler ---
async def add_group_callback(update: Update, context: CallbackContext):
    from handlers.admin import is_admin
    from db import is_super_admin
    import logging
    query = update.callback_query
    user = query.from_user
    username = user.username if user and user.username else None
    chat = query.message.chat
    chat_id = chat.id
    chat_name = chat.title or "Unknown"
    chat_type = chat.type
    log_msg = f"add_group_callback: user={username}, chat_id={chat_id}, chat_name={chat_name}, chat_type={chat_type}"
    logging.warning(log_msg)
    print(log_msg)
    try:
        if not (is_admin(username) or is_super_admin(username)):
            await query.answer("Sizda botdan foydalanish huquqi yo'q.", show_alert=True)
            logging.warning(f"Unauthorized user tried to add group: {username}")
            return
        if chat_type not in ["group", "supergroup"]:
            await query.answer("Bu tugma faqat guruhda ishlaydi.", show_alert=True)
            logging.warning(f"Callback not in group: chat_type={chat_type}")
            return
        import sqlite3
        conn = sqlite3.connect('activity.db')
        c = conn.cursor()
        c.execute("SELECT chat_id FROM groups WHERE chat_id = ?", (chat_id,))
        already_exists = c.fetchone()
        if already_exists:
            await query.answer("Guruh allaqachon bazada mavjud!", show_alert=True)
            await query.edit_message_text(f"Guruh '{chat_name}' allaqachon bazada mavjud.")
            logging.info(f"Group already exists: {chat_id} - {chat_name}")
        else:
            c.execute("INSERT INTO groups (chat_id, chat_name) VALUES (?, ?)", (chat_id, chat_name))
            conn.commit()
            await query.answer("Guruh bazaga qo'shildi!", show_alert=True)
            await query.edit_message_text(f"Guruh '{chat_name}' bazaga qo'shildi.")
            logging.info(f"Group added: {chat_id} - {chat_name}")
    except Exception as e:
        await query.answer(f"Xatolik: {e}", show_alert=True)
        logging.error(f"Error in add_group_callback: {e}")
    finally:
        try:
            conn.close()
        except:
            pass

# --- Universal callback logger for debugging ---
async def debug_callback_logger(update: Update, context: CallbackContext):
    import logging
    query = update.callback_query
    if query is not None:
        logging.warning(f"DEBUG CALLBACK: from_user={getattr(query.from_user, 'username', None)}, chat_id={getattr(getattr(query.message, 'chat', None), 'id', None)}, data={query.data}")
        print(f"DEBUG CALLBACK: from_user={getattr(query.from_user, 'username', None)}, chat_id={getattr(getattr(query.message, 'chat', None), 'id', None)}, data={query.data}")
        await query.answer()

def register_handlers(dp: Dispatcher, db_conn):
    @dp.message_handler(content_types=types.ContentTypes.ANY)
    async def log_all_messages(message: types.Message):
        log_message(message, db_conn)

def main():
    create_tables()
    add_initial_admin()
    ensure_initial_super_admin()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # --- ALWAYS register CommandHandler('start', ...) FIRST ---
    app.add_handler(CommandHandler('start', start_command_handler))
    # Register the add_group_callback handler FIRST for callback queries
    app.add_handler(CallbackQueryHandler(add_group_callback, pattern="^add_group$"))
    # Faqat group va supergroup uchun universal logger
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUPS, group_message_logger))
    # Matnli buyruqlar va tugmalar uchun (faqat private chat uchun)
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, button_handler))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('add_admin', add_admin))
    app.add_handler(CommandHandler('remove_admin', remove_admin))
    app.add_handler(CommandHandler('list_admins', list_admins))
    app.add_handler(CommandHandler('list_admin_groups', list_admin_groups))
    app.add_handler(CommandHandler('add_group', add_group))
    app.add_handler(CommandHandler('remove_group', remove_group))
    app.add_handler(CommandHandler('list_groups', list_groups))
    app.add_handler(CommandHandler('group_stats', group_stats))
    app.add_handler(CommandHandler('all_group_stats', all_group_stats))
    app.add_handler(CommandHandler('add_admin_group', add_admin_group))
    app.add_handler(CommandHandler('add_super_admin', add_super_admin))
    app.add_handler(CommandHandler('remove_super_admin', remove_super_admin))
    app.add_handler(CommandHandler('list_super_admins', list_super_admins))
    app.add_handler(CommandHandler('send_weekly_stats', send_weekly_stats_command))
    app.add_handler(CommandHandler('send_monthly_stats', send_monthly_stats_command))
    # --- DEBUG LOGGER HANDLER (last) ---
    app.add_handler(CallbackQueryHandler(debug_callback_logger))
    app.add_handler(MessageHandler(filters.ALL, debug_logger))

    scheduler = AsyncIOScheduler()
    # Haftalik va oylik statistikani avtomatik yuborish (Asia/Tashkent vaqti bilan)
    scheduler.add_job(
        send_weekly_stats,
        CronTrigger(day_of_week='mon', hour=8, minute=0, timezone='Asia/Tashkent'),
        args=[app.bot]
    )
    scheduler.add_job(
        send_monthly_stats,
        CronTrigger(day=1, hour=8, minute=0, timezone='Asia/Tashkent'),
        args=[app.bot]
    )
    async def post_init(application):
        scheduler.start()
    app.post_init = post_init
    app.run_polling()

if __name__ == "__main__":
    main() 