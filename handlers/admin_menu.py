from telegram.ext import CommandHandler, CallbackQueryHandler
from config import ADMIN_IDS
import logging

from handlers.menus.admin_panel import show_admin_menu
from handlers.add_hosting import add_hosting_start
from handlers.list_hosting import listhosting
from handlers.edit_hosting import edit_hosting_start  
from handlers.delete_hosting import  delete_hosting_start


logger = logging.getLogger(__name__)

async def admin_menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Akses ditolak.")
        return

    if query.data == "admin_addhosting":
        await add_hosting_start(update, context)
    elif query.data == "admin_listhosting":
        await listhosting(update, context)
    elif query.data == "admin_edithosting":
        await edit_hosting_start(update, context)
    elif query.data == "admin_deletehosting":
        await delete_hosting_start(update, context)  


def get_admin_menu_handler():
    return [
        CommandHandler("admin", show_admin_menu),
        CallbackQueryHandler(admin_menu_callback, pattern="^admin_"),
    ]
