# utils.py
# Yordamchi funksiyalar shu yerda bo'ladi. 

from datetime import datetime, timezone, timedelta
from telegram import ReplyKeyboardMarkup, KeyboardButton
import logging
import pytz

# Log faylini sozlash
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

GMT_OFFSET = timedelta(hours=5)  # Toshkent (GMT+5)

def format_time(time_str):
    # Bazaga allaqachon Asia/Tashkent vaqti yozilgan, shunchaki chiqaramiz
    return time_str

main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton(text="Boshlash"), KeyboardButton(text="Yordam")],
        [KeyboardButton(text="Guruh qo'shish"), KeyboardButton(text="Guruhni o'chirish")],
        [KeyboardButton(text="Guruhlar ro'yxati"), KeyboardButton(text="Guruh statistikasi")],
        [KeyboardButton(text="Adminlar ro'yxati")],
        [KeyboardButton(text="Admin qo'shish"), KeyboardButton(text="Adminni olib tashlash")],
        [KeyboardButton(text="Super-adminlar ro'yxati")],
        [KeyboardButton(text="Super-admin qo'shish"), KeyboardButton(text="Super-adminni olib tashlash")],
        [KeyboardButton(text="Barcha guruh statistikasi")],
        [KeyboardButton(text="Haftalik statistika"), KeyboardButton(text="30 kunlik statistika")],
        [KeyboardButton(text="Adminni guruhga biriktirish"), KeyboardButton(text="Adminni biriktirilgan guruhdan o'chirish")],
        [KeyboardButton(text="Biriktirilgan adminning guruhlari ")],
    ],
    resize_keyboard=True
) 