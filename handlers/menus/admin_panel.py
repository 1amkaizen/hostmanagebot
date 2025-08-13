# 📍 File: handlers/menus/admin_panel.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS

# ✅ Menu admin utama
async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        if update.message:
            await update.message.reply_text("❌ Akses ditolak. Fitur ini hanya untuk admin.")
        elif update.callback_query:
            await update.callback_query.edit_message_text("❌ Akses ditolak.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Hosting", callback_data="addhosting")],
        [InlineKeyboardButton("📋 Lihat Hosting", callback_data="admin_listhosting")],
        [InlineKeyboardButton("🔄 Edit Hosting", callback_data="admin_edithosting")],
        [InlineKeyboardButton("❌ Hapus Hosting", callback_data="admin_deletehosting")],
    ]

    if update.message:
        await update.message.reply_text(
            "🔧 *Menu Admin:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "🔧 *Menu Admin:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
