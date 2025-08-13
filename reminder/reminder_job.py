# 📍 File: reminder/reminder_job.py

from datetime import date, timedelta
from database.supabase_client import supabase
from telegram import Bot
from config import ADMIN_IDS  # ambil dari config
import logging

logger = logging.getLogger(__name__)

def get_upcoming_hostings(target_date):
    resp = supabase.table("HostingServices") \
        .select("*") \
        .eq("expired_date", target_date.isoformat()) \
        .eq("status", "active") \
        .execute()
    return resp.data

def format_hosting_message(h, days_left):
    return (
        f"⚠️ *Reminder Expired - H-{days_left}*\n\n"
        f"🌐 Domain: `{h['domain']}`\n"
        f"📅 Expired: *{h['expired_date']}*\n"
        f"📦 Layanan: {h['service_type']}\n"
        f"💸 Harga Jual: {h['price_sell']}\n"
        f"📌 Status: {h['status']}"
    )

async def run_reminder(bot: Bot):
    today = date.today()
    for days in [30, 7, 1]:
        target = today + timedelta(days=days)
        hostings = get_upcoming_hostings(target)

        if not hostings:
            continue

        for h in hostings:
            msg = format_hosting_message(h, days)

            # kirim ke admin
            for admin_id in ADMIN_IDS:
                await bot.send_message(chat_id=admin_id, text=msg, parse_mode="Markdown")

            # kirim ke klien (jika ada di HostingClients)
            try:
                user_id = h["client_user_id"]
                await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Gagal kirim ke klien {user_id}: {e}")
