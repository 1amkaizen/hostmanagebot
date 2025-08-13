# 📍 File: test_reset.py
from datetime import date
from handlers.payment_reminder import reset_monthly_status

# Simulasi 1 September 2025
reset_monthly_status(simulated_today=date(2025, 9, 1))

