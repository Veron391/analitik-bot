# help.py
# Yordam va umumiy buyruqlar uchun handler va funksiyalar shu yerda bo'ladi. 
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
import logging
from handlers.admin import admin_required
from utils import main_keyboard

logger = logging.getLogger(__name__)

# Botni ishga tushirish
@admin_required
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Assalomu alaykum! Botga xush kelibsiz! Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=main_keyboard
    )
    logger.info(f"@{update.message.from_user.username} tomonidan /start buyruq berildi")

# Help command handler
@admin_required
async def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Quyidagi bo‘limlar mavjud:\n"
        "• /start yoki Boshlash - Asosiy menyu\n"
        "• /help yoki Yordam - Yordam ma’lumotlari\n"
        "• Guruh qo‘shish - Guruhni statistikaga qo‘shish\n"
        "• Guruhni o‘chirish - Guruhni statistikadan o‘chirish\n"
        "• Guruhlar ro‘yxati - Ro‘yxatdagi guruhlar\n"
        "• Guruh statistikasi - Guruh bo‘yicha statistikani ko‘rish\n"
        "• Admin qo‘shish - Yangi admin qo‘shish\n"
        "• Adminni olib tashlash - Adminni olib tashlash\n"
        "• Adminlar ro‘yxati - Adminlar ro‘yxati\n"
        "• Super-admin qo‘shish - Yangi super-admin qo‘shish\n"
        "• Super-adminni olib tashlash - Super-adminni olib tashlash\n"
        "• Super-adminlar ro‘yxati - Super-adminlar ro‘yxati\n"
        "• Barcha guruh statistikasi - Barcha guruhlar bo‘yicha statistikani ko‘rish\n"
        "• Haftalik statistika - Haftalik hisobotni jo‘natish"
    )
    await update.message.reply_text(help_text, reply_markup=main_keyboard)
    logger.info(f"@{update.message.from_user.username} tomonidan /help buyruq berildi") 