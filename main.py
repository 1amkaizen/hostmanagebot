# 📍 File: main.py

import logging
from telegram.ext import ApplicationBuilder, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Config
from config import BOT_TOKEN

# Handlers utama
from handlers.start import get_start_handler
from handlers.add_hosting import get_add_hosting_handler
from handlers.list_hosting import get_list_hosting_handler
from handlers.admin_menu import get_admin_menu_handler
from handlers.menus.back_button import back_to_menu_handler
from handlers.edit_hosting import get_edit_hosting_handler
from handlers.delete_hosting import (
    choose_hosting,
    confirm_delete,
    cancel_delete,
    back_to_menu_handler as delete_back_to_menu_handler
)
from handlers.info_hosting import get_info_hosting_handler
from handlers.info_hosting import get_pay_button_handler



# Payment Reminder + bukti transfer + admin validation
from handlers.payment_reminder import (
    send_payment_reminders,
    get_payment_proof_handler,
    get_admin_validation_handler
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Scheduler global
scheduler = AsyncIOScheduler(timezone="Asia/Jakarta")

# Fungsi async post-init scheduler
async def on_startup(app):
    # ✅ Reminder otomatis setiap hari jam 13:30
    #scheduler.add_job(send_payment_reminders, "cron", hour=13, minute=30, args=[app.bot])
    scheduler.add_job(send_payment_reminders, "interval", minutes=1, args=[app.bot])
    scheduler.start()
    logging.info("Scheduler untuk payment reminder aktif.")

# Build aplikasi
app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

# ✅ Start handler
app.add_handler(get_start_handler())

# ✅ Add Hosting
app.add_handler(get_add_hosting_handler())

# ✅ Edit Hosting
app.add_handler(get_edit_hosting_handler())

# ✅ Info Hosting
app.add_handler(get_info_hosting_handler())

# Tombol Bayar Sekarang
app.add_handler(get_pay_button_handler())
# ✅ Tombol kembali umum
app.add_handler(CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"))

# ✅ Admin menu
for h in get_admin_menu_handler():
    app.add_handler(h)

# ✅ List Hosting
for h in get_list_hosting_handler():
    app.add_handler(h)

# ✅ Step lanjutan Delete Hosting
app.add_handler(CallbackQueryHandler(choose_hosting, pattern="^deletehosting_"))
app.add_handler(CallbackQueryHandler(confirm_delete, pattern="^confirm_delete$"))
app.add_handler(CallbackQueryHandler(cancel_delete, pattern="^cancel_delete$"))
app.add_handler(CallbackQueryHandler(delete_back_to_menu_handler, pattern="^back_to_menu$"))

# ✅ Payment proof dari klien
app.add_handler(get_payment_proof_handler())

# ✅ Admin validation (Approve/Reject)
app.add_handler(get_admin_validation_handler())

# ✅ Jalankan bot
if __name__ == "__main__":
    app.run_polling()
