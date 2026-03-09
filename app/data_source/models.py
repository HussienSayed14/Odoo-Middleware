from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ActionType(str, Enum):
    create_company = "create_company"
    create_branch = "create_branch"
    create_user = "create_user"


class RowStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class Row(BaseModel):
    """Represents one action row from the data source."""
    row_index: int                        # needed to write back to the correct row
    customer_name: str
    odoo_db: Optional[str] = None         # empty = DB needs to be created first
    action: ActionType
    name: str
    parent_company: Optional[str] = None  # create_branch
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    status: RowStatus = RowStatus.pending
    record_id: Optional[str] = None
    error: Optional[str] = None
    role: Optional[str] = "user"