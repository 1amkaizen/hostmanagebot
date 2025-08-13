# 📍 File: handlers/info_hosting.py

import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.supabase_client import supabase

logger = logging.getLogger(__name__)

# ------------------- /infohosting -------------------
async def info_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    fullname = update.effective_user.full_name
    logger.info(f"/infohosting dipanggil oleh user_id={user_id} ({fullname})")

    try:
        # Ambil data hosting milik user
        result = supabase.table("HostingServices").select(
            "provider, domain, service_type, expired_date, price_sell, status, payment_status, approved_date"
        ).eq("client_user_id", user_id).execute()

        data_list = result.data

        if not data_list:
            await update.message.reply_text("⚠️ Anda belum memiliki layanan hosting yang terdaftar.")
            return

        today = date.today()

        for data in data_list:
            # Ambil expired_date input awal
            expired_date_input = datetime.strptime(data["expired_date"], "%Y-%m-%d").date()

            # Hitung expired date yang benar
            if data.get("payment_status") == "approved" and data.get("approved_date"):
                approved_date = datetime.strptime(data["approved_date"], "%Y-%m-%d").date()

                # Durasi layanan default 1 bulan
                service_duration = relativedelta(months=1)

                # Tanggal expired baru = tanggal approve + durasi layanan
                display_expired = approved_date + service_duration

                logger.info(f"User {fullname}: expired dynamic dihitung dari approved_date {approved_date} menjadi {display_expired}")
            else:
                # Kalau belum bayar, pakai expired date input awal
                display_expired = expired_date_input

            # Hitung hari tersisa
            days_left = (display_expired - today).days

            # Tentukan status
            if data.get("payment_status") == "approved":
                status_text = "✅ Sudah Dibayar"
            else:
                if days_left < 0:
                    status_text = "❌ Expired"
                elif days_left <= 3:
                    status_text = "⚠️ Akan Jatuh Tempo"
                else:
                    status_text = "✅ Aktif"

            countdown_text = f"{days_left} hari lagi" if days_left >= 0 else f"{abs(days_left)} hari lewat"

            # Buat pesan
            msg = (
                f"📄 *Informasi Hosting Anda*\n"
                f"👤 Nama: {fullname}\n"
                f"🏢 Provider: {data['provider']}\n"
                f"🌐 Domain: {data['domain']}\n"
                f"🛠 Layanan: {data['service_type']}\n"
                f"📅 Expired: {display_expired} ({countdown_text})\n"
                f"💰 Harga: Rp {int(data['price_sell']):,}\n"
                f"📌 Status: {status_text}\n"
                f"📝 Catatan: Hosting harus dibayar sebelum jatuh tempo\n"
            )

            # Tombol Bayar jika belum dibayar
            buttons = None
            if data.get("payment_status") != "approved":
                buttons = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "💳 Bayar Sekarang",
                        callback_data=f"pay_{data['domain']}_{int(data['price_sell'])}"
                    )
                ]])

            if buttons:
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=buttons)
            else:
                await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error di /infohosting: {e}", exc_info=True)
        await update.message.reply_text("❌ Terjadi kesalahan saat mengambil data hosting Anda.")


# ------------------- Handler tombol Bayar -------------------
async def handle_pay_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, domain, price = query.data.split("_")
    price = int(price)
    fullname = query.from_user.full_name

    # Kirim info pembayaran ke user
    message = (
        f"💳 *Pembayaran Hosting*\n\n"
        f"🌐 Domain: {domain}\n"
        f"💰 Total: Rp {price:,}\n"
        f"🏦 No. Rek: 123-456-7890\n"
        f"👤 Atas Nama: {fullname}\n"
        f"Silakan upload bukti transfer melalui chat ini setelah melakukan pembayaran."
    )
    await query.message.reply_text(message, parse_mode="Markdown")

    # Update DB supaya menunggu bukti
    supabase.table("HostingServices").update({
        "waiting_payment_proof": True
    }).eq("domain", domain).execute()


# ------------------- Fungsi untuk main.py -------------------
def get_info_hosting_handler():
    return CommandHandler("infohosting", info_hosting)

def get_pay_button_handler():
    return CallbackQueryHandler(handle_pay_button, pattern="^pay_")
