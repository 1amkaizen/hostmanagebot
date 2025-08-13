# 📍 File: handlers/edit_hosting.py
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
    MENU_EDIT,
    INPUT_PROVIDER,
    INPUT_DOMAIN,
    INPUT_SERVICE_TYPE,
    INPUT_EXPIRED,
    INPUT_BUY,
    INPUT_SELL
) = range(8)  # sudah dihapus INPUT_NOTES

temp_data = {}

# Tombol kembali
back_button = InlineKeyboardMarkup(
    [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")]]
)

async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    from handlers.admin_menu import show_admin_menu
    await show_admin_menu(update, context)
    return ConversationHandler.END

# Menu pilihan field untuk edit
def get_edit_menu(user_id):
    data = temp_data[user_id]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✏️ Provider ({data['provider']})", callback_data="edit_provider")],
        [InlineKeyboardButton(f"🌐 Domain ({data['domain']})", callback_data="edit_domain")],
        [InlineKeyboardButton(f"📦 Jenis Layanan ({data['service_type']})", callback_data="edit_service_type")],
        [InlineKeyboardButton(f"📅 Expired ({data['expired_date']})", callback_data="edit_expired")],
        [InlineKeyboardButton(f"💰 Harga Beli ({data['price_buy']})", callback_data="edit_buy")],
        [InlineKeyboardButton(f"💵 Harga Jual ({data['price_sell']})", callback_data="edit_sell")],
        [InlineKeyboardButton("✅ Selesai Edit", callback_data="done_edit")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")],
    ])

async def edit_hosting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.message.reply_text("❌ Akses ditolak. Khusus admin.")
        return ConversationHandler.END

    result = supabase.table("HostingServices").select(
        "id, provider, domain, service_type, expired_date, price_buy, price_sell, status, HostingClients(full_name)"
    ).eq("status", "active").execute()

    if not result.data:
        await query.message.reply_text("⚠️ Tidak ada hosting aktif yang ditemukan.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(
            f"{h['HostingClients']['full_name']} | {h['provider']} | {h['domain']}",
            callback_data=h["id"]
        )] for h in result.data
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")])

    await query.edit_message_text("Pilih hosting yang akan diedit:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_HOSTING

async def choose_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hosting_id = query.data
    user_id = query.from_user.id

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
        "price_sell": result.data.get("price_sell") or 0
    }

    await query.edit_message_text("Pilih bagian yang ingin diedit:", reply_markup=get_edit_menu(user_id))
    return MENU_EDIT

# Fungsi umum untuk update DB
async def update_field(user_id, field, value):
    hosting_id = temp_data[user_id]["hosting_id"]
    temp_data[user_id][field] = value
    result = supabase.table("HostingServices").update({field: value}).eq("id", hosting_id).execute()
    logger.info(f"Update {field} untuk hosting_id {hosting_id} => {value}")
    return bool(result.data)

# Handler pilihan menu edit
async def menu_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data

    if action == "done_edit":
        temp_data.pop(user_id, None)
        await query.edit_message_text("✅ Edit selesai.", reply_markup=back_button)
        return ConversationHandler.END

    field_map = {
        "edit_provider": (INPUT_PROVIDER, f"Masukkan provider baru (sekarang: {temp_data[user_id]['provider']}):"),
        "edit_domain": (INPUT_DOMAIN, f"Masukkan domain baru (sekarang: {temp_data[user_id]['domain']}):"),
        "edit_service_type": (INPUT_SERVICE_TYPE, "Pilih jenis layanan:"),
        "edit_expired": (INPUT_EXPIRED, f"Masukkan tanggal expired YYYY-MM-DD (sekarang: {temp_data[user_id]['expired_date']}):"),
        "edit_buy": (INPUT_BUY, f"Masukkan harga beli baru (sekarang: {temp_data[user_id]['price_buy']}):"),
        "edit_sell": (INPUT_SELL, f"Masukkan harga jual baru (sekarang: {temp_data[user_id]['price_sell']}):"),
    }

    if action in field_map:
        state, text = field_map[action]
        if state == INPUT_SERVICE_TYPE:
            keyboard = [[InlineKeyboardButton(x, callback_data=f"stype_{x}")] for x in ["hosting", "domain", "VPS", "email"]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(text)
        return state

    if action.startswith("stype_"):
        value = action.replace("stype_", "")
        await update_field(user_id, "service_type", value)
        await query.edit_message_text(f"✅ Jenis layanan diperbarui ke {value}", reply_markup=get_edit_menu(user_id))
        return MENU_EDIT

# Input field
async def input_text_field(update: Update, context: ContextTypes.DEFAULT_TYPE, field, state_return, validator=None):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if validator:
        if not validator(text):
            await update.message.reply_text("⚠️ Format tidak valid. Coba lagi.")
            return state_return

    await update_field(user_id, field, text)
    await update.message.reply_text(f"✅ {field} diperbarui.", reply_markup=get_edit_menu(user_id))
    return MENU_EDIT

async def input_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await input_text_field(update, context, "provider", INPUT_PROVIDER)

async def input_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await input_text_field(update, context, "domain", INPUT_DOMAIN)

async def input_expired(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def valid_date(val):
        try:
            datetime.strptime(val, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    return await input_text_field(update, context, "expired_date", INPUT_EXPIRED, validator=valid_date)

async def input_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def valid_float(val):
        try:
            float(val)
            return True
        except ValueError:
            return False
    return await input_text_field(update, context, "price_buy", INPUT_BUY, validator=valid_float)

async def input_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def valid_float(val):
        try:
            float(val)
            return True
        except ValueError:
            return False
    return await input_text_field(update, context, "price_sell", INPUT_SELL, validator=valid_float)

def get_edit_hosting_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_hosting_start, pattern="^admin_edithosting$")],
        states={
            CHOOSING_HOSTING: [
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
                CallbackQueryHandler(choose_hosting),
            ],
            MENU_EDIT: [
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
                CallbackQueryHandler(menu_edit_handler),
            ],
            INPUT_PROVIDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_provider)],
            INPUT_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_domain)],
            INPUT_SERVICE_TYPE: [CallbackQueryHandler(menu_edit_handler, pattern="^stype_")],
            INPUT_EXPIRED: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_expired)],
            INPUT_BUY: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_buy)],
            INPUT_SELL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_sell)],
        },
        fallbacks=[CommandHandler("cancel", back_to_menu_handler)],
        per_message=False,
    )
