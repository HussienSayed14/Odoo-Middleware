import gspread
from google.oauth2.service_account import Credentials

from app.data_source.base import DataSource
from app.data_source.models import Row, RowStatus, ActionType
from app.config import GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, SHEET_NAME

# Column index mapping (0-based) — update if you add/reorder columns in the sheet
COL = {
    "customer_name": 0,
    "odoo_db":        1,
    "action":         2,
    "name":           3,
    "parent_company": 4,
    "email":          5,
    "phone":          6,
    "country":        7,
    "status":         8,
    "record_id":      9,
    "error":          10,
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


class GoogleSheetsDataSource(DataSource):

    def __init__(self):
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME) # type: ignore

    def get_pending_rows(self) -> list[Row]:
        all_rows = self.sheet.get_all_values()
        headers = all_rows[0]   # skip header row
        pending = []

        for i, row in enumerate(all_rows[1:], start=2):  # start=2 → actual sheet row number
            status = row[COL["status"]].strip().lower()
            if status != "pending":
                continue
            try:
                pending.append(Row(
                    row_index=i,
                    customer_name=row[COL["customer_name"]].strip(),
                    odoo_db=row[COL["odoo_db"]].strip() or None,
                    action=ActionType(row[COL["action"]].strip()),
                    name=row[COL["name"]].strip(),
                    parent_company=row[COL["parent_company"]].strip() or None,
                    email=row[COL["email"]].strip() or None,
                    phone=row[COL["phone"]].strip() or None,
                    country=row[COL["country"]].strip() or None,
                ))
            except Exception as e:
                # If a row has an invalid action or missing required fields, mark it failed immediately
                self._write_back(i, status="failed", error=str(e))

        return pending

    def update_row(
        self,
        row: Row,
        status: RowStatus,
        odoo_db: str | None = None,
        record_id: str | None = None,
        error: str | None = None,
    ) -> None:
        if odoo_db:
            self.sheet.update_cell(row.row_index, COL["odoo_db"] + 1, odoo_db)
        self._write_back(row.row_index, status=status.value, record_id=record_id, error=error)

    def _write_back(self, row_index: int, status: str, record_id: str | None = None, error: str | None = None):
        self.sheet.update_cell(row_index, COL["status"] + 1, status)
        if record_id is not None:
            self.sheet.update_cell(row_index, COL["record_id"] + 1, str(record_id))
        if error is not None:
            self.sheet.update_cell(row_index, COL["error"] + 1, error)