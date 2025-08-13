# 📍 File: main.py

import logging
from telegram.ext import ApplicationBuilder, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Config
from config import BOT_TOKEN

# Handlers
from handlers.start import get_start_handler
from handlers.add_hosting import get_add_hosting_handler
from handlers.list_hosting import get_list_hosting_handler
from handlers.admin_menu import get_admin_menu_handler
from handlers.menus.admin_panel import show_admin_menu  # ✅ pastikan file dan fungsi ini ada
from handlers.menus.back_button import back_to_menu_handler  # ✅ handler untuk tombol ⬅️ Kembali
from handlers.edit_hosting import get_edit_hosting_handler  
# Reminder Job
from reminder.reminder_job import run_reminder

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Inisialisasi scheduler global
scheduler = AsyncIOScheduler()

# Fungsi async post-init scheduler
async def on_startup(app):
    scheduler.add_job(run_reminder, "cron", hour=9, args=[app])  # kirim app agar bisa akses bot, context, dsb
    scheduler.start()

# Build aplikasi
app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

# ✅ Register semua handler
app.add_handler(get_start_handler())
app.add_handler(get_add_hosting_handler())
app.add_handler(get_edit_hosting_handler())

# ✅ Register tombol kembali
app.add_handler(CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"))

# ✅ Admin menu handlers
for h in get_admin_menu_handler():
    app.add_handler(h)

# ✅ List hosting handler
for h in get_list_hosting_handler():
    app.add_handler(h)



# ✅ Jalankan bot
if __name__ == "__main__":
    app.run_polling()
