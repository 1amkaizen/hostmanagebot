# 📍 File: database/supabase_client.py

from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

# ✅ Inisialisasi Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
