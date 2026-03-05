from app.odoo.actions.base import BaseAction


class CreateUserAction(BaseAction):

    def validate(self) -> None:
        if not self.row.name:
            raise ValueError("'name' is required for create_user")
        if not self.row.email:
            raise ValueError("'email' is required for create_user (used as login)")

    def execute(self) -> int:
        payload = {
            "name": self.row.name,
            "login": self.row.email,
            "email": self.row.email,
        }
        return self.client.execute("res.users", "create", [payload])