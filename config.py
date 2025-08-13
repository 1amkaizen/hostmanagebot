# 📍 File: config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Admin Telegram user IDs (dipisah dengan koma di .env)
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
