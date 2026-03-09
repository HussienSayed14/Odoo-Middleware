import xmlrpc.client
import requests
import logging
from app.config import ODOO_URL, ODOO_MASTER_PASSWORD, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class OdooClient:
    """Handles Odoo XML-RPC connection and DB management."""

    def __init__(self, db: str, is_new_db: bool = False):
        self.db = db
        self.url = ODOO_URL
        self.admin_user = ODOO_ADMIN_USER if is_new_db else ODOO_ADMIN_USER
        self.admin_password = ODOO_ADMIN_PASSWORD if is_new_db else ODOO_ADMIN_PASSWORD
        logger.info(f"[OdooClient] Connecting to {self.url} — DB: {db} — user: {self.admin_user}")
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        self.uid = self._authenticate()

    def _authenticate(self) -> int:
        logger.info(f"[OdooClient] Authenticating '{self.admin_user}' on DB '{self.db}'")
        uid = self.common.authenticate(self.db, self.admin_user, self.admin_password, {})
        if not uid:
            raise Exception(f"Odoo authentication failed for database '{self.db}'")
        logger.info(f"[OdooClient] Authenticated — UID: {uid}")
        return uid # type: ignore

    def execute(self, model: str, method: str, args: list, kwargs: dict = None) -> any: # type: ignore
        logger.debug(f"[OdooClient] execute — model={model} method={method}")
        result = self.models.execute_kw(
            self.db, self.uid, self.admin_password,
            model, method, args, kwargs or {}
        )
        logger.debug(f"[OdooClient] result — {result}")
        return result

    @staticmethod
    def create_database(db_name: str) -> None:
        logger.info(f"[OdooClient] Creating database '{db_name}' at {ODOO_URL}")

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
            allow_redirects=False,   # ← key fix
        )

        logger.info(f"[OdooClient] DB create status={response.status_code} headers={dict(response.headers)}")

        # Success = Odoo redirects to /web (303 to /web means DB was created)
        if response.status_code == 303 and "/web" in response.headers.get("Location", ""):
            logger.info(f"[OdooClient] Database '{db_name}' created successfully")
            return

        # If we get anything else, something went wrong
        raise Exception(
            f"Failed to create database '{db_name}'. "
            f"Status: {response.status_code}. "
            f"Response: {response.text[:300]}"
        )
    @staticmethod
    def database_exists(db_name: str) -> bool:
        logger.info(f"[OdooClient] Checking if database '{db_name}' exists")
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/db")
        existing_dbs = common.list()
        logger.info(f"[OdooClient] Existing databases: {existing_dbs}")
        exists = db_name in existing_dbs # type: ignore
        logger.info(f"[OdooClient] '{db_name}' exists: {exists}")
        return exists
    
