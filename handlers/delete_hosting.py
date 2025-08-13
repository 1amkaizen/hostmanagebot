# 📍 File: handlers/delete_hosting.py

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
)
from database.supabase_client import supabase
from handlers.admin_menu import show_admin_menu
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

CHOOSING_HOSTING, CONFIRM_DELETE = range(2)

# Simpan data sementara pilihan hosting user
temp_delete = {}

back_button = InlineKeyboardMarkup(
    [[InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")]]
)

async def delete_hosting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan daftar hosting aktif yang bisa dihapus."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Akses ditolak.")
        logger.warning(f"delete_hosting_start akses ditolak user_id={user_id}")
        return ConversationHandler.END

    result = supabase.table("HostingServices") \
        .select("id, provider, domain, service_type, status") \
        .eq("status", "active") \
        .execute()
    hostings = result.data

    if not hostings:
        await query.edit_message_text("⚠️ Tidak ada hosting aktif yang bisa dihapus.", reply_markup=back_button)
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(f"{h['provider']} - {h['domain']} ({h['service_type']})",
                              callback_data=f"deletehosting_{h['id']}")]
        for h in hostings
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")])

    await query.edit_message_text(
        "Pilih hosting yang ingin dihapus:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_HOSTING


async def choose_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyimpan pilihan hosting yang akan dihapus dan meminta konfirmasi."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if not data.startswith("deletehosting_"):
        await query.edit_message_text("❌ Pilihan tidak valid.")
        return ConversationHandler.END

    hosting_id = data[len("deletehosting_"):]
    temp_delete[user_id] = hosting_id

    keyboard = [
        [InlineKeyboardButton("✅ Ya, hapus", callback_data="confirm_delete")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel_delete")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_to_menu")]
    ]

    await query.edit_message_text(
        "⚠️ Anda yakin ingin menghapus hosting ini?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_DELETE


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menghapus hosting setelah admin konfirmasi."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    hosting_id = temp_delete.get(user_id)
    if not hosting_id:
        await query.edit_message_text("❌ Data hosting tidak ditemukan, batalkan operasi.")
        return ConversationHandler.END

    try:
        res = supabase.table("HostingServices").delete().eq("id", hosting_id).execute()

        if res.data:  # ✅ Cek data terhapus
            logger.info(f"Hosting dengan id={hosting_id} berhasil dihapus oleh admin user_id={user_id}")
            await query.edit_message_text("✅ Hosting berhasil dihapus.", reply_markup=back_button)
        else:
            logger.error(f"Gagal hapus hosting id={hosting_id}, tidak ada data terhapus, user_id={user_id}")
            await query.edit_message_text("❌ Gagal menghapus hosting. Coba lagi nanti.", reply_markup=back_button)

    except Exception as e:
        logger.exception(f"Exception saat hapus hosting id={hosting_id} user_id={user_id}: {e}")
        await query.edit_message_text("❌ Terjadi kesalahan saat menghapus hosting.", reply_markup=back_button)

    temp_delete.pop(user_id, None)
    return ConversationHandler.END


async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan proses penghapusan."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    temp_delete.pop(user_id, None)

    await query.edit_message_text("❌ Penghapusan dibatalkan.", reply_markup=back_button)
    return ConversationHandler.END


async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kembali ke menu admin."""
    query = update.callback_query
    await query.answer()
    await show_admin_menu(update, context)
    return ConversationHandler.END


def get_delete_hosting_handler():
    """Mengembalikan handler untuk proses hapus hosting."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(delete_hosting_start, pattern="^admin_deletehosting$")],
        states={
            CHOOSING_HOSTING: [
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
                CallbackQueryHandler(choose_hosting, pattern="^deletehosting_"),
            ],
            CONFIRM_DELETE: [
                CallbackQueryHandler(confirm_delete, pattern="^confirm_delete$"),
                CallbackQueryHandler(cancel_delete, pattern="^cancel_delete$"),
                CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$")],
        per_message=False,
    )
