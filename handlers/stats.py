# stats.py
# Statistika va hisobotlar uchun handler va funksiyalar shu yerda bo'ladi. 

import sqlite3
from telegram import Update, Bot
from telegram.ext import CallbackContext
import logging
from db import get_admin_usernames, get_super_admin_usernames, get_chat_id_by_username, is_super_admin, get_groups, get_admin_groups, get_group_name
from utils import format_time

logger = logging.getLogger(__name__)

def format_stats_message(group_name, stats, period_label, all_users=None):
    # all_users: set of all usernames (if provided, show 0 for missing)
    message = f"📅 {period_label} faoliyat statistikasi uchun guruh '{group_name}':\n\n"
    total_messages = 0
    shown_users = set()
    for username, message_count, last_message_time in stats:
        message += f"Foydalanuvchi: @{username}\n"
        message += f"   Yuborilgan xabarlar soni: {message_count}\n"
        message += f"   Oxirgi xabar vaqti: {format_time(last_message_time)} (UTC +5)\n\n"
        total_messages += message_count
        shown_users.add(username)
    # Add users with 0 messages if all_users is provided
    if all_users:
        for username in sorted(all_users - shown_users):
            message += f"Foydalanuvchi: @{username}\n"
            message += f"   Yuborilgan xabarlar soni: 0\n"
            message += f"   Oxirgi xabar vaqti: -\n\n"
    if period_label == "Oylik":
        message += f"📅 Joriy oyda yuborilgan jami xabarlar soni: {total_messages}\n"
    else:
        message += f"📅 Oxirgi 7 kun ichida yuborilgan jami xabarlar soni: {total_messages}\n"
    return message

# Har haftalik statistika jo'natish funksiyasi
async def send_weekly_stats(bot: Bot):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT chat_id, username, COUNT(*), MAX(message_time) FROM messages WHERE message_time >= datetime('now', '-7 days') GROUP BY chat_id, username")
        stats = c.fetchall()
        # --- all group users ---
        c.execute("SELECT chat_id, username FROM messages")
        all_users_map = {}
        for chat_id, username in c.fetchall():
            all_users_map.setdefault(chat_id, set()).add(username)
        for admin_username in get_admin_usernames():
            admin_chat_id = await get_chat_id_by_username(admin_username)
            if not admin_chat_id:
                continue
            if is_super_admin(admin_username):
                groups = get_groups()
            else:
                groups = get_admin_groups(admin_username)
            for chat_id in groups:
                group_name = get_group_name(chat_id)
                group_stats = [(row[1], row[2], row[3]) for row in stats if row[0] == chat_id]
                all_users = all_users_map.get(chat_id, set())
                message = format_stats_message(group_name, group_stats, "Haftalik", all_users)
                await bot.send_message(admin_chat_id, text=message)
                logger.info(f"Weekly statistics sent to @{admin_username}")
    except Exception as e:
        logger.error(f"Error sending weekly statistics: {e}")
    finally:
        conn.close()

# Har oylik statistika jo'natish funksiyasi
async def send_monthly_stats(bot: Bot):
    conn = sqlite3.connect('activity.db')
    c = conn.cursor()
    try:
        c.execute("SELECT chat_id, username, COUNT(*), MAX(message_time) FROM messages WHERE message_time >= date('now', 'start of month') GROUP BY chat_id, username")
        stats = c.fetchall()
        # --- all group users ---
        c.execute("SELECT chat_id, username FROM messages")
        all_users_map = {}
        for chat_id, username in c.fetchall():
            all_users_map.setdefault(chat_id, set()).add(username)
        for admin_username in get_admin_usernames():
            admin_chat_id = await get_chat_id_by_username(admin_username)
            if not admin_chat_id:
                continue
            if is_super_admin(admin_username):
                groups = get_groups()
            else:
                groups = get_admin_groups(admin_username)
            for chat_id in groups:
                group_name = get_group_name(chat_id)
                group_stats = [(row[1], row[2], row[3]) for row in stats if row[0] == chat_id]
                all_users = all_users_map.get(chat_id, set())
                message = format_stats_message(group_name, group_stats, "Oylik", all_users)
                await bot.send_message(admin_chat_id, text=message)
                logger.info(f"Monthly statistics sent to @{admin_username}")
    except Exception as e:
        logger.error(f"Error sending monthly statistics: {e}")
    finally:
        conn.close()

# Weekly stats command handler
async def send_weekly_stats_command(update: Update, context: CallbackContext):
    if update.message.chat.type != "private":
        return  # Guruhda yoki boshqa chatda hech qanday xabar yuborilmasin
    await send_weekly_stats(context.bot)
    await update.message.reply_text("Haftalik statistika shaxsiy chatga yuborildi.")
    logger.info(f"@{update.message.from_user.username} tomonidan /send_weekly_stats buyruq berildi")

# Monthly stats command handler
async def send_monthly_stats_command(update: Update, context: CallbackContext):
    if update.message.chat.type != "private":
        return  # Guruhda yoki boshqa chatda hech qanday xabar yuborilmasin
    await send_monthly_stats(context.bot)
    await update.message.reply_text("Oylik statistika shaxsiy chatga yuborildi.")
    logger.info(f"@{update.message.from_user.username} tomonidan /send_monthly_stats buyruq berildi") 