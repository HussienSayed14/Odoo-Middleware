from dotenv import load_dotenv
import os

load_dotenv()

# ── Odoo ──────────────────────────────────────────────
ODOO_URL = os.getenv("ODOO_URL")
ODOO_MASTER_PASSWORD = os.getenv("ODOO_MASTER_PASSWORD")
ODOO_ADMIN_USER = os.getenv("ODOO_ADMIN_USER", "admin")
ODOO_ADMIN_PASSWORD = os.getenv("ODOO_ADMIN_PASSWORD")

SECRET_KEY = os.getenv("SECRET_KEY", "any-long-random-string-here")
