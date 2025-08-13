# handlers/edit_hosting.py

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters, CommandHandler
)
from database.supabase_client import supabase
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

(
    CHOOSING_HOSTING,
    INPUT_PROVIDER,
    INPUT_DOMAIN,
    INPUT_SERVICE_TYPE,
    INPUT_EXPIRED,
    INPUT_BUY,
    INPUT_SELL,
    INPUT_NOTES,
    CONFIRM_SAVE,
) = range(9)

temp_data = {}

back_button = InlineKeyboardMarkup(
    [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")]]
)

async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info(f"back_to_menu_handler dipanggil oleh user_id={query.from_user.id}")
    from handlers.admin_menu import show_admin_menu
    await show_admin_menu(update, context)
    return ConversationHandler.END

async def edit_hosting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        logger.warning(f"Akses ditolak untuk user_id={user_id} di edit_hosting_start")
        await query.message.reply_text("❌ Akses ditolak. Khusus admin.")
        return ConversationHandler.END

    # Ambil list hosting lengkap dengan nama klien
    result = supabase.table("HostingServices").select(
        "id, provider, domain, service_type, expired_date, price_buy, price_sell, status, notes, client_user_id, HostingClients(full_name)"
    ).eq("status", "active").execute()

    # Cek hasil data tanpa akses .error langsung
    if not result.data:
        await query.message.reply_text("⚠️ Tidak ada hosting aktif yang ditemukan.")
        return ConversationHandler.END

    keyboard = []
    for h in result.data:
        label = f"{h['HostingClients']['full_name']} | {h['provider']} | {h['domain']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=h["id"])])

    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")])

    await query.edit_message_text(
        "Pilih hosting yang akan diedit:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_HOSTING

async def choose_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hosting_id = query.data
    user_id = query.from_user.id

    if hosting_id == "back_to_menu":
        from handlers.admin_menu import show_admin_menu
        await show_admin_menu(update, context)
        return ConversationHandler.END

    # Ambil data hosting terpilih
    result = supabase.table("HostingServices").select("*").eq("id", hosting_id).single().execute()
    if not result.data:
        await query.edit_message_text("❌ Data hosting tidak ditemukan.")
        return ConversationHandler.END

    temp_data[user_id] = {
        "hosting_id": hosting_id,
        "provider": result.data.get("provider") or "",
        "domain": result.data.get("domain") or "",
        "service_type": result.data.get("service_type") or "",
        "expired_date": result.data.get("expired_date") or "",
        "price_buy": result.data.get("price_buy") or 0,
        "price_sell": result.data.get("price_sell") or 0,
        "notes": result.data.get("notes") or "",
    }

    await query.edit_message_text(
        f"Edit provider (sekarang: {temp_data[user_id]['provider']}):\nKetik baru atau sama untuk lanjut",
        reply_markup=back_button,
    )
    return INPUT_PROVIDER

async def input_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text:
        temp_data[user_id]["provider"] = text
    await update.message.reply_text(
        f"Edit domain (sekarang: {temp_data[user_id]['domain']}):\nKetik baru atau sama untuk lanjut",
        reply_markup=back_button,
    )
    return INPUT_DOMAIN

async def input_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text:
        temp_data[user_id]["domain"] = text

    keyboard = [[InlineKeyboardButton(x, callback_data=x)] for x in ["hosting", "domain", "VPS", "email"]]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")])

    await update.message.reply_text(
        f"Pilih jenis layanan (sekarang: {temp_data[user_id]['service_type']}):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return INPUT_SERVICE_TYPE

async def input_service_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if data:
        temp_data[user_id]["service_type"] = data
    await query.edit_message_text(
        f"Edit tanggal expired (YYYY-MM-DD) (sekarang: {temp_data[user_id]['expired_date']}):",
        reply_markup=back_button,
    )
    return INPUT_EXPIRED

async def input_expired(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
        temp_data[user_id]["expired_date"] = text
    except ValueError:
        await update.message.reply_text("⚠️ Format tanggal salah. Contoh: 2025-12-01", reply_markup=back_button)
        return INPUT_EXPIRED

    await update.message.reply_text(
        f"Edit harga beli (sekarang: {temp_data[user_id]['price_buy']}):",
        reply_markup=back_button,
    )
    return INPUT_BUY

async def input_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    try:
        temp_data[user_id]["price_buy"] = float(text)
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka (contoh: 100000)", reply_markup=back_button)
        return INPUT_BUY

    await update.message.reply_text(
        f"Edit harga jual (sekarang: {temp_data[user_id]['price_sell']}):",
        reply_markup=back_button,
    )
    return INPUT_SELL

async def input_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    try:
        temp_data[user_id]["price_sell"] = float(text)
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka (contoh: 200000)", reply_markup=back_button)
        return INPUT_SELL

    await update.message.reply_text(
        f"Edit catatan (sekarang: {temp_data[user_id]['notes'] or '-'}):\nKetik '-' untuk kosongkan catatan",
        reply_markup=back_button,
    )
    return INPUT_NOTES

async def input_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text == "-":
        temp_data[user_id]["notes"] = None
    else:
        temp_data[user_id]["notes"] = text

    await update.message.reply_text("✅ Menyimpan data... Mohon tunggu...")

    data = temp_data.pop(user_id)
    hosting_id = data.pop("hosting_id")

    # Update ke Supabase
    result = supabase.table("HostingServices").update(data).eq("id", hosting_id).execute()
    if not result.data:
        logger.error(f"Gagal update hosting id={hosting_id}: {result.error}")
        await update.message.reply_text("❌ Gagal menyimpan data. Coba lagi.")
        return ConversationHandler.END

    logger.info(f"Hosting berhasil diupdate id={hosting_id} oleh user_id={user_id} data: {data}")
    await update.message.reply_text(
        "✅ Hosting berhasil diperbarui.",
        reply_markup=back_button,
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    temp_data.pop(user_id, None)
    logger.info(f"Edit hosting dibatalkan oleh user_id={user_id}")
    await update.message.reply_text("❌ Edit dibatalkan.", reply_markup=back_button)
    return ConversationHandler.END

def get_edit_hosting_handler():
    logger.info("Mendaftarkan get_edit_hosting_handler()")
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_hosting_start, pattern="^admin_edithosting$")],
        states={
            CHOOSING_HOSTING: [
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
                CallbackQueryHandler(choose_hosting),
            ],
            INPUT_PROVIDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_provider),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
            INPUT_DOMAIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_domain),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
            INPUT_SERVICE_TYPE: [
                CallbackQueryHandler(input_service_type),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
            INPUT_EXPIRED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_expired),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
            INPUT_BUY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_buy),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
            INPUT_SELL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_sell),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
            INPUT_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_notes),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
