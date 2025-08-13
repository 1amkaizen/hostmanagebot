# 📍 File: handlers/add_hosting.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from database.supabase_client import supabase
import logging
from datetime import datetime
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

(
    CHOOSING_USER, INPUT_PROVIDER, INPUT_DOMAIN,
    INPUT_SERVICE_TYPE, INPUT_TANGGAL_SEWA, INPUT_BUY,
    INPUT_SELL
) = range(7)

temp_data = {}

back_button = InlineKeyboardMarkup(
    [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")]]
)

# Handler tombol back ke menu
async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info(f"back_to_menu_handler dipanggil oleh user_id={query.from_user.id}")
    from handlers.admin_menu import show_admin_menu
    await show_admin_menu(update, context)
    return ConversationHandler.END

# Start add hosting
async def add_hosting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"add_hosting_start dipanggil oleh user_id={update.effective_user.id}")
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        logger.warning(f"Akses ditolak untuk user_id={user_id} di add_hosting_start")
        if update.message:
            await update.message.reply_text("❌ Akses ditolak. Khusus admin.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("❌ Akses ditolak. Khusus admin.")
        return ConversationHandler.END

    result = supabase.table("HostingClients").select("user_id, full_name").execute()
    users = result.data

    logger.info(f"Ditemukan {len(users) if users else 0} user di HostingClients")

    if not users:
        await (update.message or update.callback_query.message).reply_text("⚠️ Belum ada user yang /start.")
        return ConversationHandler.END

    existing_hostings = supabase.table("HostingServices").select("client_user_id").execute()
    hosted_user_ids = set(h["client_user_id"] for h in existing_hostings.data)
    logger.info(f"Ditemukan {len(hosted_user_ids)} user yang sudah punya hosting")

    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if u['user_id'] in hosted_user_ids else ''}{u['full_name']}",
            callback_data=str(u["user_id"])
        )]
        for u in users
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")])

    await (update.message or update.callback_query.message).reply_text(
        "Pilih klien untuk ditambahkan hosting:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_USER

# Handler pilih user
async def choose_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.info(f"choose_user dipanggil dengan callback_data={query.data} oleh user_id={query.from_user.id}")

    if not query.data.isdigit():
        logger.warning(f"choose_user menerima data tidak valid: {query.data}")
        await query.edit_message_text("❌ Pilihan tidak valid.")
        return ConversationHandler.END

    user_id = int(query.data)
    temp_data[query.from_user.id] = {"client_user_id": user_id}
    await query.edit_message_text(
        "Masukkan provider (contoh: rumahweb):",
        reply_markup=back_button
    )
    return INPUT_PROVIDER

async def input_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"input_provider dipanggil oleh user_id={user_id} dengan input={update.message.text}")
    temp_data[user_id]["provider"] = update.message.text
    await update.message.reply_text("Masukkan domain:", reply_markup=back_button)
    return INPUT_DOMAIN

async def input_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"input_domain dipanggil oleh user_id={user_id} dengan input={update.message.text}")
    temp_data[user_id]["domain"] = update.message.text
    keyboard = [[InlineKeyboardButton(x, callback_data=x)] for x in ["hosting", "domain", "VPS", "email"]]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")])
    await update.message.reply_text("Pilih jenis layanan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return INPUT_SERVICE_TYPE

async def input_service_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    logger.info(f"input_service_type dipanggil oleh user_id={user_id} dengan input={query.data}")
    temp_data[user_id]["service_type"] = query.data
    await query.edit_message_text(
        "Masukkan tanggal sewa (format: YYYY-MM-DD):",
        reply_markup=back_button
    )
    return INPUT_TANGGAL_SEWA

async def input_tanggal_sewa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"input_tanggal_sewa dipanggil oleh user_id={user_id} dengan input={update.message.text}")
    try:
        datetime.strptime(update.message.text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("⚠️ Format tanggal salah. Contoh: 2025-12-01", reply_markup=back_button)
        return INPUT_TANGGAL_SEWA
    temp_data[user_id]["tanggal_sewa"] = update.message.text
    await update.message.reply_text("Masukkan harga beli:", reply_markup=back_button)
    return INPUT_BUY

async def input_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"input_buy dipanggil oleh user_id={user_id} dengan input={update.message.text}")
    try:
        temp_data[user_id]["price_buy"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka (contoh: 100000)", reply_markup=back_button)
        return INPUT_BUY
    await update.message.reply_text("Masukkan harga jual:", reply_markup=back_button)
    return INPUT_SELL

async def input_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"input_sell dipanggil oleh user_id={user_id} dengan input={update.message.text}")
    try:
        temp_data[user_id]["price_sell"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka (contoh: 200000)", reply_markup=back_button)
        return INPUT_SELL

    temp_data[user_id]["status"] = "active"

    # Set expired_date sama dengan tanggal_sewa
    temp_data[user_id]["expired_date"] = temp_data[user_id]["tanggal_sewa"]

    await update.message.reply_text("✅ Data akan disimpan. Mohon tunggu...")

    data = temp_data.pop(user_id)
    supabase.table("HostingServices").insert(data).execute()
    logger.info(f"Hosting berhasil disimpan untuk user_id={user_id} dengan data: {data}")

    await update.message.reply_text(
        "✅ Hosting berhasil disimpan.",
        reply_markup=back_button
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    temp_data.pop(user_id, None)
    logger.info(f"Input dibatalkan oleh user_id={user_id}")
    await update.message.reply_text("❌ Input dibatalkan.", reply_markup=back_button)
    return ConversationHandler.END

async def block_direct_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"block_direct_access dipanggil oleh user_id={update.effective_user.id}")
    await update.message.reply_text("❌ Akses fitur hanya tersedia melalui menu /admin.")
    return ConversationHandler.END

def get_add_hosting_handler():
    logger.info("Mendaftarkan get_add_hosting_handler()")
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_hosting_start, pattern="^addhosting$"),
            CommandHandler("addhosting", block_direct_access),
        ],
        states={
            CHOOSING_USER: [
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
                CallbackQueryHandler(choose_user),
            ],
            INPUT_PROVIDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_provider),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$")
            ],
            INPUT_DOMAIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_domain),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$")
            ],
            INPUT_SERVICE_TYPE: [
                CallbackQueryHandler(input_service_type),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$")
            ],
            INPUT_TANGGAL_SEWA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_tanggal_sewa),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$")
            ],
            INPUT_BUY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_buy),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$")
            ],
            INPUT_SELL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_sell),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
