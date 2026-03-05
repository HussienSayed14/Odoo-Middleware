from abc import ABC, abstractmethod
from app.data_source.models import Row
from app.odoo.client import OdooClient


class BaseAction(ABC):
    """All actions must implement validate() and execute()."""

    def __init__(self, client: OdooClient, row: Row):
        self.client = client
        self.row = row

    @abstractmethod
    def validate(self) -> None:
        """Raise ValueError with a clear message if required fields are missing."""
        pass

    @abstractmethod
    def execute(self) -> int:
        """Run the action against Odoo. Returns the created record ID."""
        pass

    def run(self) -> int:
        self.validate()
        return self.execute()