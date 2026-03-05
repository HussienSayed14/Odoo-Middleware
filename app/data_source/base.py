from abc import ABC, abstractmethod
from app.data_source.models import Row, RowStatus


class DataSource(ABC):
    """
    Abstract interface for the data source.
    Swap Google Sheets for a database or API by implementing this class.
    """

    @abstractmethod
    def get_pending_rows(self) -> list[Row]:
        """Fetch all rows where status == pending."""
        pass

    @abstractmethod
    def update_row(
        self,
        row: Row,
        status: RowStatus,
        odoo_db: str | None = None,
        record_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Write result back to the data source for a given row."""
        pass