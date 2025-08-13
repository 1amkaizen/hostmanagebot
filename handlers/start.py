# 📍 File: handlers/start.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database.supabase_client import supabase
from config import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    user_id = user.id
    username = user.username or "-"
    full_name = user.full_name
    language_code = user.language_code or "-"
    is_bot = user.is_bot

    # ✅ Logging lengkap untuk debugging dan audit
    logger.info(
        f"[START] User Info:\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Username: @{username}\n"
        f"📛 Full Name: {full_name}\n"
        f"🌐 Language: {language_code}\n"
        f"🤖 Is Bot: {is_bot}"
    )

    # Cek jika user sudah ada
    result = supabase.table("HostingClients").select("user_id").eq("user_id", user_id).execute()
    if not result.data:
        # Insert user ke Supabase
        supabase.table("HostingClients").insert({
            "user_id": user_id,
            "username": username,
            "full_name": full_name
        }).execute()
        logger.info(f"✅ User baru disimpan ke Supabase: {full_name} ({username})")

    await update.message.reply_text(
        f"👋 Hai {full_name}!\n\n"
        "Notifikasi hosting & domain Anda sudah aktif.\n"
        "Kami akan mengirimkan pengingat otomatis menjelang jatuh tempo layanan Anda.\n\n"
        "Terima kasih 🙏"
    )

def get_start_handler():
    return CommandHandler("start", start)
