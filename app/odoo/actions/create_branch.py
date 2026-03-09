from app.odoo.actions.base import BaseAction


class CreateBranchAction(BaseAction):

    def validate(self) -> None:
        if not self.row.name:
            raise ValueError("'name' is required for create_branch")
        if not self.row.parent_company:
            raise ValueError("'parent_company' is required for create_branch")

    def execute(self) -> int:
        # Look up parent company in res.company (not res.partner)
        parent_ids = self.client.execute(
            "res.company", "search",
            [[["name", "=", self.row.parent_company]]]
        )
        if not parent_ids:
            raise ValueError(f"Parent company '{self.row.parent_company}' not found in Odoo")

        payload = {
            "name": self.row.name,
            "parent_id": parent_ids[0],
        }
        if self.row.email:
            payload["email"] = self.row.email
        if self.row.phone:
            payload["phone"] = self.row.phone
        if self.row.country:
            country_ids = self.client.execute(
                "res.country", "search", [[["code", "=", self.row.country.upper()]]]
            )
            if country_ids:
                payload["country_id"] = country_ids[0]

        return self.client.execute("res.company", "create", [payload])