# 📍 File: handlers/payment_reminder.py

import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from database.supabase_client import supabase
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# ------------------- Reset status bulanan otomatis -------------------
def reset_monthly_status():
    try:
        result = supabase.table("HostingServices").select(
            "id, domain, client_user_id, payment_status"
        ).eq("status", "active").execute()

        services = result.data
        if not services:
            logger.info("Tidak ada layanan aktif untuk di-reset bulan ini.")
            return

        for svc in services:
            # Reset hanya yang statusnya approved bulan sebelumnya
            if svc.get("payment_status") == "approved":
                supabase.table("HostingServices").update({
                    "payment_status": "pending",
                    "waiting_payment_proof": True,
                    "payment_proof_url": None
                }).eq("id", svc["id"]).execute()
                logger.info(f"Status bulanan di-reset untuk domain {svc['domain']} user_id={svc['client_user_id']}")

    except Exception as e:
        logger.error(f"Error saat reset status bulanan: {e}", exc_info=True)


# ------------------- Reminder H-3 sampai H-0 (versi bulanan) -------------------
async def send_payment_reminders(bot: Bot):
    today = date.today()
    try:
        result = supabase.table("HostingServices").select(
            "id, client_user_id, provider, domain, expired_date, price_sell, payment_status, approved_date"
        ).eq("status", "active").neq("payment_status", "approved").execute()

        services = result.data
        if not services:
            logger.info("Tidak ada layanan yang perlu diingatkan hari ini.")
            return

        for svc in services:
            # Tentukan tanggal expired dinamis
            if svc.get("approved_date"):
                approved_date = date.fromisoformat(svc["approved_date"])
                display_expired = approved_date + relativedelta(months=1)
            else:
                display_expired = date.fromisoformat(svc["expired_date"])

            days_left = (display_expired - today).days

            # Kirim reminder H-3 sampai H-0
            if 0 <= days_left <= 3:
                countdown_text = f"{days_left} hari lagi" if days_left > 0 else "hari ini"
                message = (
                    f"⚠️ <b>Pengingat Pembayaran Hosting</b>\n\n"
                    f"🌐 Domain: <b>{svc['domain']}</b>\n"
                    f"🏢 Provider: <code>{svc['provider']}</code>\n"
                    f"💰 Harga: <b>Rp {int(svc['price_sell']):,}</b>\n"
                    f"📅 Expired: {display_expired} ({countdown_text})\n\n"
                    f"Silakan lakukan pembayaran sebelum jatuh tempo.\n"
                    f"Kirimkan bukti transfer melalui chat ini."
                )
                await bot.send_message(chat_id=svc["client_user_id"], text=message, parse_mode="HTML")
                logger.info(f"Reminder terkirim ke user_id={svc['client_user_id']} untuk domain {svc['domain']}")

    except Exception as e:
        logger.error(f"Error saat memproses payment reminder: {e}", exc_info=True)


# ------------------- Handler menerima bukti transfer -------------------
async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "-"
    fullname = user.full_name

    if not update.message.photo:
        await update.message.reply_text("⚠️ Kirimkan gambar bukti transfer.")
        return

    photo_file_id = update.message.photo[-1].file_id

    result = supabase.table("HostingServices").select(
        "id, provider, domain, price_sell"
    ).eq("client_user_id", user_id).eq("waiting_payment_proof", True).single().execute()

    if not result.data:
        await update.message.reply_text("⚠️ Tidak ada pembayaran yang menunggu bukti transfer.")
        return

    svc = result.data
    # Update dengan logika lebih jelas
    supabase.table("HostingServices").update({
        "payment_proof_url": photo_file_id,
        "waiting_payment_proof": True,  # tetap True sampai admin approve/reject
        "payment_status": "pending"
    }).eq("id", svc["id"]).execute()

    logger.info(f"User {user_id} kirim bukti transfer untuk domain {svc['domain']}")
    await update.message.reply_text("✅ Bukti transfer diterima. Admin akan meninjau pembayaran Anda.")

    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{svc['id']}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{svc['id']}")
    ]])

    message_text = (
        f"📢 <b>Pembayaran Masuk</b>\n\n"
        f"🌐 Domain: <b>{svc['domain']}</b>\n"
        f"🏢 Provider: <code>{svc['provider']}</code>\n"
        f"💰 Harga: <b>Rp {int(svc['price_sell']):,}</b>\n"
        f"👤 Fullname: {fullname}\n"
        f"📛 Username: {username}\n"
        f"📌 Dari user_id: {user_id}"
    )

    for admin_id in ADMIN_IDS:
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=photo_file_id,
            caption=message_text,
            parse_mode="HTML",
            reply_markup=buttons
        )
        logger.info(f"Notifikasi bukti transfer dikirim ke admin_id={admin_id}")


# ------------------- Handler tombol admin -------------------
async def handle_admin_validation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, svc_id = query.data.split("_")
    svc_id = str(svc_id)
    svc = supabase.table("HostingServices").select("*").eq("id", svc_id).single().execute().data

    if not svc:
        await query.edit_message_text("❌ Data tidak ditemukan.")
        return

    client_id = svc["client_user_id"]

    if action == "approve":
        current_expired = date.fromisoformat(svc['expired_date'])
        new_expired = current_expired + relativedelta(months=1)

        supabase.table("HostingServices").update({
            "payment_status": "approved",
            "waiting_payment_proof": False,
            "approved_date": date.today().isoformat(),
            "expired_date": new_expired.isoformat()
        }).eq("id", svc_id).execute()

        await context.bot.send_message(client_id, "✅ Pembayaran Anda telah diverifikasi oleh admin. Layanan tetap aktif.")
        await query.edit_message_caption("✅ Pembayaran disetujui.", parse_mode="HTML")
        logger.info(f"Admin approve pembayaran domain {svc['domain']} untuk user_id={client_id}, expired updated ke {new_expired}")

    elif action == "reject":
        supabase.table("HostingServices").update({
            "payment_status": "rejected",
            "waiting_payment_proof": True,
            "payment_proof_url": None
        }).eq("id", svc_id).execute()

        await context.bot.send_message(client_id, "❌ Pembayaran Anda ditolak oleh admin. Silakan kirim ulang bukti transfer.")
        await query.edit_message_text("❌ Pembayaran ditolak.")
        logger.info(f"Admin reject pembayaran domain {svc['domain']} untuk user_id={client_id}")


# ------------------- Fungsi untuk main.py -------------------
def get_payment_proof_handler():
    return MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_payment_proof)

def get_admin_validation_handler():
    return CallbackQueryHandler(handle_admin_validation, pattern="^(approve|reject)_")
