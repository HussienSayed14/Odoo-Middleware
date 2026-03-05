from dotenv import load_dotenv
import os

load_dotenv()

# ── Odoo ──────────────────────────────────────────────
ODOO_URL = os.getenv("ODOO_URL")
ODOO_MASTER_PASSWORD = os.getenv("ODOO_MASTER_PASSWORD")
ODOO_ADMIN_USER = os.getenv("ODOO_ADMIN_USER", "admin")
ODOO_ADMIN_PASSWORD = os.getenv("ODOO_ADMIN_PASSWORD")

# ── Google Sheets ──────────────────────────────────────
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")