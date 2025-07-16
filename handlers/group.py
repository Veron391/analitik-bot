# group.py
# Guruhlarni boshqarish uchun handler va funksiyalar shu yerda bo'ladi. 

import sqlite3
from telegram import Update
from telegram.ext import CallbackContext
import logging
from handlers.admin import admin_required
from handlers.superadmin import super_admin_required
from utils import format_time

logger = logging.getLogger(__name__)

# Guruh qo'shish funksiyasi
@admin_required
async def add_group(update: Update, context: CallbackContext):
    user = update.message.from_user
    username = user.username if user and user.username else None
    chat_id = update.message.chat.id
    chat_name = update.message.chat.title
    chat_type = update.message.chat.type
    log_msg = f"add_group called: user={username}, chat_id={chat_id}, chat_name={chat_name}, chat_type={chat_type}"
    logger.warning(log_msg)
    print(log_msg)
    if chat_type == "private":
        await update.message.reply_text("⚠️ Iltimos, bu buyruqni guruh chatida yuboring")
        return

    if not chat_name or chat_name.strip() == "":
        await update.message.reply_text("Guruh nomini kiritish kerak.")
        return

    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO groups (chat_id, chat_name) VALUES (?, ?)", (chat_id, chat_name))
        conn.commit()
        await update.message.reply_text(f"Guruh '{chat_name}' qo'shildi.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("Guruh allaqachon ro'yxatta mavjud")
    finally:
        conn.close()

# Guruh o'chirish funksiyasi
@admin_required
async def remove_group(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        await update.message.reply_text("Iltimos, guruh nomini kiriting. Misol: /remove_group GuruhNomi")
        return

    group_name = ' '.join(context.args).strip()

    if not group_name:
        await update.message.reply_text("Guruh nomini kiritish kerak.")
        return

    conn = sqlite3.connect('activity.db')
    c = conn.cursor()

    try:
        if group_name.lower() == 'none' or group_name.strip() == "":
            c.execute("SELECT chat_id, chat_name FROM groups WHERE chat_name IS NULL OR chat_name = '' OR chat_name = 'None'")
        else:
            c.execute("SELECT chat_id, chat_name FROM groups WHERE chat_name = ?", (group_name,))

        result = c.fetchall()

        if not result:
            await update.message.reply_text(f"Guruh '{group_name}' topilmadi.")
            return

        for chat_id, chat_name in result:
            c.execute("DELETE FROM groups WHERE chat_id = ?", (chat_id,))
            await update.message.reply_text(f"Guruh '{chat_name}' ro'yxatdan olib tashlandi.")

        conn.commit()
    except Exception as e:
        await update.message.reply_text(f"Guruhni olib tashlashda xatolik: {e}")
    finally:
        conn.close()

# Guruh nomini olish funksiyasi
def get_group_name(chat_id):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT chat_name FROM groups WHERE chat_id = ?", (chat_id,))
    group = c.fetchone()
    conn.close()
    return group[0] if group else "Unknown"

# Guruh ro'yxatini olish funksiyasi
def get_groups():
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups WHERE chat_name IS NOT NULL AND chat_name != ''")
    groups = c.fetchall()
    conn.close()
    return [group[0] for group in groups]

# Ro'yxatdagi guruhlarni ko'rsatish funksiyasi
@admin_required
async def list_groups(update: Update, context: CallbackContext):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT chat_name, chat_id FROM groups")
        groups = c.fetchall()
        conn.close()

        if not groups:
            await update.message.reply_text("Hech qanday guruh ro'yxatda mavjud emas.")
            logger.warning("Hech qanday guruh ro'yxatda mavjud emas")
            return

        message = "Ro'yxatdagi guruhlar:\n"
        for group in groups:
            message += f"Guruh nomi: {group[0]}, Chat ID: {group[1]}\n"

        await update.message.reply_text(message)
        logger.info("Guruhlar ro'yxati yuborildi")
    except Exception as e:
        logger.error(f"Guruhlar ro'yxatini olishda xatolik: {e}")

# Guruh statistikasini ko'rsatish funksiyasi
@admin_required
async def group_stats(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Iltimos, guruh nomini kiriting. Misol: /group_stats GuruhNomi")
        logger.warning("Guruh nomi kiritilmagan")
        return

    group_name_requested = ' '.join(context.args)
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT chat_id FROM groups WHERE chat_name = ?", (group_name_requested,))
        chat_id = c.fetchone()

        if not chat_id:
            await update.message.reply_text(f"Guruh nomi '{group_name_requested}' topilmadi.")
            logger.warning(f"Guruh nomi '{group_name_requested}' topilmadi")
            return

        # Guruhdagi barcha foydalanuvchilar (tarixiy) ro'yxati
        c.execute("SELECT DISTINCT username FROM messages WHERE chat_id = ?", (chat_id[0],))
        all_users = set(row[0] for row in c.fetchall())

        # Har bir foydalanuvchi uchun so'nggi 30 kun va 7 kun ichida xabar bor-yo'qligini tekshirish
        stats_30 = {}
        c.execute("SELECT username, COUNT(*), MAX(message_time) FROM messages WHERE chat_id = ? AND substr(message_time, 1, 10) >= date('now', '-30 days') GROUP BY username", (chat_id[0],))
        for username, count, last_time in c.fetchall():
            stats_30[username] = (count, last_time)

        stats_7 = {}
        c.execute("SELECT username, COUNT(*), MAX(message_time) FROM messages WHERE chat_id = ? AND substr(message_time, 1, 10) >= date('now', '-7 days') GROUP BY username", (chat_id[0],))
        for username, count, last_time in c.fetchall():
            stats_7[username] = (count, last_time)

        message = f"Guruh '{group_name_requested}' statistikasi (so'nggi 30 va 7 kun):\n\n"
        for username in sorted(all_users):
            count_30, last_30 = stats_30.get(username, (0, None))
            count_7, last_7 = stats_7.get(username, (0, None))
            formatted_time = format_time(last_30) if last_30 else "-"
            message += f"Foydalanuvchi: @{username}\n"
            message += f"   30 kunlik xabarlar soni: {count_30}\n"
            message += f"   7 kunlik xabarlar soni: {count_7}\n"
            message += f"   Oxirgi xabar vaqti: {formatted_time} (UTC +5)\n\n"

        await update.message.reply_text(message)
        logger.info(f"Guruh '{group_name_requested}' statistikasi yuborildi (faol va nofaol a'zolar bilan)")
    except Exception as e:
        logger.error(f"Guruh statistikasi olishda xatolik: {e}")
    finally:
        conn.close()

# Barcha guruhlar statistikasi
@super_admin_required
async def all_group_stats(update: Update, context: CallbackContext):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT chat_id FROM groups")
        groups = c.fetchall()

        if not groups:
            await update.message.reply_text("Hech qanday guruh ro'yxatda mavjud emas.")
            logger.warning("Hech qanday guruh ro'yxatda mavjud emas")
            return

        for group in groups:
            chat_id = group[0]
            group_name = get_group_name(chat_id)

            # Guruhdagi barcha foydalanuvchilar (tarixiy)
            c.execute("SELECT DISTINCT username FROM messages WHERE chat_id = ?", (chat_id,))
            all_users = set(row[0] for row in c.fetchall())

            # 7 kunlik statistika
            stats_7 = {}
            c.execute("SELECT username, COUNT(*), MAX(message_time) FROM messages WHERE chat_id = ? AND message_time >= datetime('now', '-7 days') GROUP BY username", (chat_id,))
            for username, count, last_time in c.fetchall():
                stats_7[username] = (count, last_time)

            weekly_message = f"📅 Har haftalik faoliyat statistikasi uchun guruh '{group_name}':\n\n"
            total_weekly_messages = 0
            for username in sorted(all_users):
                count, last_time = stats_7.get(username, (0, None))
                formatted_time = format_time(last_time) if last_time else "-"
                weekly_message += f"Foydalanuvchi: @{username}\n"
                weekly_message += f"   Yuborilgan xabarlar soni: {count}\n"
                weekly_message += f"   Oxirgi xabar vaqti: {formatted_time} (UTC +5)\n\n"
                total_weekly_messages += count
            weekly_message += f"📅 Oxirgi hafta ichida yuborilgan jami xabarlar soni: {total_weekly_messages}\n"

            await update.message.reply_text(weekly_message)
            logger.info(f"{group_name} uchun har haftalik statistika yuborildi (faol va nofaol a'zolar bilan)")

    except Exception as e:
        logger.error(f"Barcha guruhlar statistikasi olishda xatolik: {e}")
    finally:
        conn.close()

# Admin va guruh o'rtasidagi aloqani qo'shish funksiyasi
@admin_required
async def add_admin_group(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        await update.message.reply_text("Iltimos, admin va guruh nomini kiriting. Misol: /add_admin_group @username GuruhNomi")
        return

    admin_username = context.args[0].strip('@')
    group_name = ' '.join(context.args[1:])

    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT chat_id FROM groups WHERE chat_name = ?", (group_name,))
        group = c.fetchone()
        if not group:
            await update.message.reply_text(f"Guruh '{group_name}' topilmadi.")
            return

        chat_id = group[0]

        c.execute("INSERT INTO admin_groups (admin_username, chat_id) VALUES (?, ?)", (admin_username, chat_id))
        conn.commit()
        await update.message.reply_text(f"Admin @{admin_username} guruh '{group_name}' uchun qo'shildi.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"Admin @{admin_username} allaqachon guruh '{group_name}' uchun mavjud.")
    finally:
        conn.close() 