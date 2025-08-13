# 📍 File: handlers/menus/back_button.py

from telegram import Update
from telegram.ext import ContextTypes
from handlers.menus.admin_panel import show_admin_menu

async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_admin_menu(update, context)
