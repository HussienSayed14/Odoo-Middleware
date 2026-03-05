from app.data_source.base import DataSource
from app.data_source.models import Row, RowStatus, ActionType
from app.odoo.client import OdooClient
from app.odoo.actions.create_company import CreateCompanyAction
from app.odoo.actions.create_branch import CreateBranchAction
from app.odoo.actions.create_user import CreateUserAction


ACTION_MAP = {
    ActionType.create_company: CreateCompanyAction,
    ActionType.create_branch:  CreateBranchAction,
    ActionType.create_user:    CreateUserAction,
}


def _resolve_db_name(customer_name: str) -> str:
    """Generate a clean DB name from customer name."""
    return customer_name.lower().strip().replace(" ", "_") + "_db"


def process(source: DataSource) -> dict:
    rows = source.get_pending_rows()
    results = {"processed": 0, "success": 0, "failed": 0}

    for row in rows:
        results["processed"] += 1
        try:
            # ── Step 1: Ensure DB exists ───────────────────────────────
            if not row.odoo_db:
                db_name = _resolve_db_name(row.customer_name)
                if not OdooClient.database_exists(db_name):
                    OdooClient.create_database(db_name)
                # Write DB name back to sheet immediately
                source.update_row(row, status=RowStatus.pending, odoo_db=db_name)
                row.odoo_db = db_name

            # ── Step 2: Authenticate against the customer's DB ─────────
            client = OdooClient(db=row.odoo_db)

            # ── Step 3: Run the action ─────────────────────────────────
            action_class = ACTION_MAP.get(row.action)
            if not action_class:
                raise ValueError(f"Unknown action: {row.action}")

            action = action_class(client=client, row=row)
            record_id = action.run()

            source.update_row(row, status=RowStatus.success, record_id=str(record_id))
            results["success"] += 1

        except Exception as e:
            source.update_row(row, status=RowStatus.failed, error=str(e))
            results["failed"] += 1

    return results