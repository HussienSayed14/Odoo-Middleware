import xmlrpc.client
import requests
from typing import Any
from app.config import ODOO_URL, ODOO_MASTER_PASSWORD, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD


class OdooClient:
    """Handles Odoo XML-RPC connection and DB management."""

    def __init__(self, db: str):
        self.db = db
        self.url = ODOO_URL
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        self.uid = self._authenticate()

    def _authenticate(self) -> int:
        uid = self.common.authenticate(self.db, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD, {})
        if not uid:
            raise Exception(f"Odoo authentication failed for database '{self.db}'")
        return uid # type: ignore

    def execute(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        return self.models.execute_kw(
            self.db, self.uid, ODOO_ADMIN_PASSWORD,
            model, method, args, kwargs or {}
        )

    @staticmethod
    def create_database(db_name: str) -> None:
        """Create a new Odoo database via the database manager endpoint."""
        response = requests.post(
            f"{ODOO_URL}/web/database/create",
            data={
                "master_pwd": ODOO_MASTER_PASSWORD,
                "name": db_name,
                "lang": "en_US",
                "password": ODOO_ADMIN_PASSWORD,
                "login": "admin",
                "country_code": "eg",
                "phone": "",
            },
        )
        if response.status_code != 200 or "error" in response.text.lower():
            raise Exception(f"Failed to create Odoo database '{db_name}': {response.text[:200]}")

    @staticmethod
    def database_exists(db_name: str) -> bool:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/db")
        existing_dbs = common.list()
        return db_name in existing_dbs # type: ignore