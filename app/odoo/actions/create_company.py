from app.odoo.actions.base import BaseAction


class CreateCompanyAction(BaseAction):

    def validate(self) -> None:
        if not self.row.name:
            raise ValueError("'name' is required for create_company")

    def execute(self) -> int:
        payload = {
            "name": self.row.name,
            "is_company": True,
        }
        if self.row.email:
            payload["email"] = self.row.email
        if self.row.phone:
            payload["phone"] = self.row.phone
        if self.row.country:
            # Look up country ID by code
            country_ids = self.client.execute(
                "res.country", "search", [[["code", "=", self.row.country.upper()]]]
            )
            if country_ids:
                payload["country_id"] = country_ids[0]

        return self.client.execute("res.partner", "create", [payload])