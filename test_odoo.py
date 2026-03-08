import xmlrpc.client
from dotenv import load_dotenv
import os
import json

load_dotenv()

ODOO_URL = os.getenv("ODOO_URL")
ODOO_ADMIN_USER = os.getenv("ODOO_ADMIN_USER", "admin")
ODOO_ADMIN_PASSWORD = os.getenv("ODOO_ADMIN_PASSWORD")

# ── Step 1: Check available databases ─────────────────
print("\n--- Available Databases ---")
db_proxy = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/db")
dbs = db_proxy.list()
print(dbs)

# ── Step 2: Authenticate ───────────────────────────────
DB = dbs[0]  # type: ignore # use the first DB, change if needed
print(f"\n--- Authenticating against '{DB}' ---")
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(DB, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD, {})
print(f"UID: {uid}")

if not uid:
    print("Authentication failed. Check your credentials in .env")
    exit()

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

# ── Step 3: Create a company ───────────────────────────
print("\n--- Creating Company ---")
payload = {
    "name": "Test Company",
    # "is_company": True,
    "email": "test@testcompany.com",
    "phone": "+201001234567",
}
print(f"Request body: {json.dumps(payload, indent=2)}")

company_id = models.execute_kw(
    DB, uid, ODOO_ADMIN_PASSWORD,
    "res.company", "create",
    [payload]
)
print(f"Response (created record ID): {company_id}")

# ── Step 4: Read it back to confirm ───────────────────
print("\n--- Reading Created Company ---")
result = models.execute_kw(
    DB, uid, ODOO_ADMIN_PASSWORD,
    "res.company", "read",
    [[company_id]],
    {"fields": ["name", "email", "phone"]}
)
print(f"Response: {json.dumps(result, indent=2)}")

# ── Step 5: Create a Branch ────────────────────────────
print("\n--- Creating Branch ---")

# First look up the parent company by name
parent_ids = models.execute_kw(
    DB, uid, ODOO_ADMIN_PASSWORD,
    "res.company", "search",
    [[["name", "=", "Test Company"]]]
)
print(f"Found parent company IDs: {parent_ids}")

branch_payload = {
    "name": "Test Branch",
    "email": "branch@testcompany.com",
    "phone": "+201009876543",
    "parent_id": parent_ids[0], # type: ignore
}
print(f"Request body: {json.dumps(branch_payload, indent=2)}")

branch_id = models.execute_kw(
    DB, uid, ODOO_ADMIN_PASSWORD,
    "res.company", "create",
    [branch_payload]
)
print(f"Response (created branch ID): {branch_id}")

# Read it back
branch_result = models.execute_kw(
    DB, uid, ODOO_ADMIN_PASSWORD,
    "res.company", "read",
    [[branch_id]],
    {"fields": ["name", "email", "phone", "parent_id"]}
)
print(f"Response: {json.dumps(branch_result, indent=2)}")


# ── Step 6: Create a User ──────────────────────────────
print("\n--- Creating User ---")

user_payload = {
    "name": "Test User",
    "login": "testuser@testcompany.com",
    "email": "testuser@testcompany.com",
    "company_id": company_id,       # assign to the company we created
    "company_ids": [(4, company_id)],  # grant access to that company
}
print(f"Request body: {json.dumps(user_payload, indent=2)}")

user_id = models.execute_kw(
    DB, uid, ODOO_ADMIN_PASSWORD,
    "res.users", "create",
    [user_payload]
)
print(f"Response (created user ID): {user_id}")

# Read it back
user_result = models.execute_kw(
    DB, uid, ODOO_ADMIN_PASSWORD,
    "res.users", "read",
    [[user_id]],
    {"fields": ["name", "login", "email", "company_id"]}
)
print(f"Response: {json.dumps(user_result, indent=2)}")