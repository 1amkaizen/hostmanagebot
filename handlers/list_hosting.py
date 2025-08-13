# 📍 File: handlers/list_hosting.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from database.supabase_client import supabase
from config import ADMIN_IDS
import logging
from datetime import datetime, timedelta, date
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from handlers.menus.admin_panel import show_admin_menu  # ✅ untuk tombol Back

logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 5
list_state = defaultdict(lambda: {"page": 0, "month": None, "data": []})

async def listhosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Akses perintah ini hanya bisa lewat menu /admin.")
        return

    if update.effective_user.id not in ADMIN_IDS:
        await update.callback_query.answer("❌ Akses ditolak.", show_alert=True)
        return

    logger.info("🔍 Memuat data tanggal_sewa & expired_date dari HostingServices...")
    result = supabase.table("HostingServices").select(
        "tanggal_sewa,expired_date,client_user_id,payment_status,approved_date,domain,provider,service_type,price_sell,status"
    ).execute()
    data = result.data

    if not data:
        await update.callback_query.edit_message_text("Belum ada data hosting.")
        return

    # Buat list bulan
    dates = [r.get("expired_date") or r.get("tanggal_sewa") for r in data]
    months = sorted(set([d[:7] for d in dates]))  # Format "YYYY-MM"

    user_ids = list(set([r["client_user_id"] for r in data]))
    usernames = {}
    if user_ids:
        logger.info(f"🔍 Mengambil username dari HostingClients untuk user_id: {user_ids}")
        user_query = supabase.table("HostingClients").select("user_id,username,full_name").in_("user_id", user_ids).execute()
        for u in user_query.data:
            uid = u["user_id"]
            uname = u.get("username")
            if uname and uname.strip() and uname != "-":
                usernames[uid] = f"@{uname}"
            else:
                usernames[uid] = u.get("full_name", "-")

    keyboard = []
    for m in months:
        month_users = [r["client_user_id"] for r in data if (r.get("expired_date") or r.get("tanggal_sewa")).startswith(m)]
        unique_users = set(month_users)
        displayed_user = "-"
        if unique_users:
            first_uid = next(iter(unique_users))
            displayed_user = usernames.get(first_uid, "-")
        display = f"{m} ({len(unique_users)} {displayed_user})"
        logger.info(f"📅 Tombol bulan: {display}")
        keyboard.append([InlineKeyboardButton(display, callback_data=f"filter_{m}")])

    keyboard.append([InlineKeyboardButton("❌ Lihat Semua", callback_data="filter_all")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])

    await update.callback_query.edit_message_text(
        "Filter berdasarkan bulan expired/tanggal sewa:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def get_filtered_data(month=None):
    q = supabase.table("HostingServices").select(
        "tanggal_sewa,expired_date,client_user_id,payment_status,approved_date,domain,provider,service_type,price_sell,status"
    ).order("expired_date")

    if month:
        start_date = datetime.strptime(month, "%Y-%m")
        end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        logger.info(f"🔍 Filter data antara {start_date.date()} s/d {end_date.date()} (berdasarkan expired_date)")

        # filter utama pakai expired_date
        q = q.gte("expired_date", start_date.date().isoformat())
        q = q.lt("expired_date", end_date.date().isoformat())

    result = q.execute()
    return result.data


async def handle_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "back_to_admin":
        await show_admin_menu(update, context)
        return

    month = None if query.data == "filter_all" else query.data.replace("filter_", "")
    data = get_filtered_data(month)

    list_state[user_id] = {"page": 0, "month": month, "data": data}
    await send_page(query, user_id)

async def send_page(query, user_id):
    state = list_state[user_id]
    page = state["page"]
    data = state["data"]

    if not data:
        await query.edit_message_text(
            "⚠️ Tidak ada data hosting.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]
            ])
        )
        return

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    sliced = data[start:end]

    user_ids = [item['client_user_id'] for item in sliced]
    user_info = {}
    if user_ids:
        user_query = supabase.table("HostingClients").select("user_id,username,full_name").in_("user_id", user_ids).execute()
        for u in user_query.data:
            uid = u["user_id"]
            uname = u.get("username")
            if uname and uname.strip():
                user_info[uid] = f"@{uname}"
            else:
                user_info[uid] = u.get("full_name", "-")

    messages = []
    today = date.today()
    for item in sliced:
        username = user_info.get(item["client_user_id"], "-")

        # Gunakan tanggal_sewa sebagai dasar expired default
        try:
            base_date = datetime.strptime(item.get("tanggal_sewa"), "%Y-%m-%d").date()
            if item.get("expired_date"):
                expired_date_input = datetime.strptime(item["expired_date"], "%Y-%m-%d").date()
            else:
                expired_date_input = base_date  # fallback

            display_expired = expired_date_input


            delta_days = (display_expired - today).days
            if delta_days < 0:
                sisa_waktu = f"❌ Expired {abs(delta_days)} hari lalu"
            elif delta_days <= 3 and item.get("payment_status") != "approved":
                sisa_waktu = f"⚠️ Akan Jatuh Tempo ({delta_days} hari lagi)"
            else:
                sisa_waktu = f"{delta_days} hari lagi"

            # Tentukan status pembayaran
            if item.get("payment_status") == "approved":
                payment_status_text = "✅ Sudah Dibayar"
            else:
                if delta_days < 0:
                    payment_status_text = "❌ Expired"
                elif delta_days <= 3:
                    payment_status_text = "⚠️ Akan Jatuh Tempo"
                else:
                    payment_status_text = "✅ Aktif"

        except Exception as e:
            logger.error(f"❌ Gagal parsing tanggal - {e}")
            display_expired = item.get("expired_date") or item.get("tanggal_sewa")
            sisa_waktu = "-"
            payment_status_text = "-"

        messages.append(
            f"🌐 Domain: {item['domain']}\n"
            f"👤 user_id: {item['client_user_id']} ({username})\n"
            f"🏢 Provider: {item['provider']}\n"
            f"📦 Layanan: {item['service_type']}\n"
            f"📅 Tanggal Sewa: {item.get('tanggal_sewa')}\n"
            f"📅 Expired: {display_expired} ({sisa_waktu})\n"
            f"💳 Status Pembayaran: {payment_status_text}\n"
            f"💸 Harga Jual: {item['price_sell']}\n"
            f"📌 Status: {item['status']}"
        )


    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data="page_prev"))
    if end < len(data):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data="page_next"))

    keyboard = [nav_buttons] if nav_buttons else []
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])

    await query.edit_message_text(
        "\n\n".join(messages),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = list_state[user_id]

    if query.data == "page_prev":
        state["page"] -= 1
    elif query.data == "page_next":
        state["page"] += 1

    await send_page(query, user_id)

def get_list_hosting_handler():
    return [
        CallbackQueryHandler(listhosting, pattern="^listhosting$"),
        CallbackQueryHandler(handle_filter, pattern="^filter_|^back_to_admin$"),
        CallbackQueryHandler(handle_pagination, pattern="^page_"),
    ]
