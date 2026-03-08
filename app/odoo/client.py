import xmlrpc.client
import requests
import logging
from app.config import ODOO_URL, ODOO_MASTER_PASSWORD, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class OdooClient:
    """Handles Odoo XML-RPC connection and DB management."""

    def __init__(self, db: str):
        self.db = db
        self.url = ODOO_URL
        logger.info(f"[OdooClient] Connecting to {self.url} — DB: {db}")
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        self.uid = self._authenticate()

    def _authenticate(self) -> int:
        logger.info(f"[OdooClient] Authenticating user '{ODOO_ADMIN_USER}' on DB '{self.db}'")
        uid = self.common.authenticate(self.db, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD, {})
        if not uid:
            raise Exception(f"Odoo authentication failed for database '{self.db}'")
        logger.info(f"[OdooClient] Authenticated — UID: {uid}")
        return uid # type: ignore

    def execute(self, model: str, method: str, args: list, kwargs: dict = None) -> any: # type: ignore
        logger.debug(f"[OdooClient] execute — model={model} method={method} args={args} kwargs={kwargs}")
        result = self.models.execute_kw(
            self.db, self.uid, ODOO_ADMIN_PASSWORD,
            model, method, args, kwargs or {}
        )
        logger.debug(f"[OdooClient] execute result — {result}")
        return result

    @staticmethod
    def create_database(db_name: str) -> None:
        logger.info(f"[OdooClient] Creating database '{db_name}' at {ODOO_URL}")
        logger.debug(f"[OdooClient] master_pwd={'*' * len(ODOO_MASTER_PASSWORD)} admin_user=admin") # type: ignore

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

        logger.info(f"[OdooClient] DB create response — status={response.status_code}")
        logger.debug(f"[OdooClient] DB create response body — {response.text[:500]}")

        if response.status_code != 200 or "error" in response.text.lower():
            raise Exception(f"Failed to create Odoo database '{db_name}': {response.text[:500]}")

        logger.info(f"[OdooClient] Database '{db_name}' created successfully")

    @staticmethod
    def database_exists(db_name: str) -> bool:
        logger.info(f"[OdooClient] Checking if database '{db_name}' exists")
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/db")
        existing_dbs = common.list()
        logger.info(f"[OdooClient] Existing databases: {existing_dbs}")
        exists = db_name in existing_dbs # type: ignore
        logger.info(f"[OdooClient] '{db_name}' exists: {exists}")
        return exists