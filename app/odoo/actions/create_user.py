from app.odoo.actions.base import BaseAction

ROLE_GROUPS = {
    "user":    "base.group_user",
    "manager": "base.group_user",
    "admin":   "base.group_erp_manager"
}

class CreateUserAction(BaseAction):

    def validate(self) -> None:
        if not self.row.name:
            raise ValueError("'name' is required for create_user")
        if not self.row.email:
            raise ValueError("'email' is required for create_user (used as login)")

    def execute(self) -> int:
        role = getattr(self.row, 'role', 'user') or 'user'
        group_xml_id = ROLE_GROUPS.get(role, "base.group_user")
        module, name = group_xml_id.split(".")

        group_ids = self.client.execute(
            "ir.model.data", "search",
            [[["module", "=", module], ["name", "=", name]]]
        )
        group_ref = self.client.execute(
            "ir.model.data", "read",
            [group_ids], {"fields": ["res_id"]}
        )
        group_id = group_ref[0]["res_id"]

        payload = {
            "name": self.row.name,
            "login": self.row.email,
            "email": self.row.email,
            "groups_ids": [(4, group_id)],
        }
        return self.client.execute("res.users", "create", [payload])