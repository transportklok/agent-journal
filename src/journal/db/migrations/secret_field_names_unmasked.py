import json
from typing import ClassVar

from journal.db.connection import Connection
from journal.db.migration import Migration
from journal.support.unmasked import Unmasked

MASK_MARK = "[secret "


class SecretFieldNamesUnmasked(Migration):
    """A secret's field name a mask rewrote when another secret's value was the same word is its name again, read from the field's variable."""

    number: ClassVar[int] = 87

    def apply(self, connection: Connection) -> None:
        if not self.has_table(connection, "secrets"):
            return
        for row in connection.all("SELECT id, fields, filled FROM secrets WHERE fields LIKE ?", (f"%{MASK_MARK}%",)):
            fields = json.loads(row["fields"])
            names = {field["name"]: self.name(field, fields) for field in fields if MASK_MARK in field["name"]}
            restored = [{**field, "name": names.get(field["name"], field["name"])} for field in fields]
            filled = [names.get(name, name) for name in json.loads(row["filled"] or "[]")]
            connection.execute("UPDATE secrets SET fields = ?, filled = ? WHERE id = ?", (Unmasked(json.dumps(restored)), Unmasked(json.dumps(filled)), row["id"]))

    @staticmethod
    def name(field: dict, fields: list[dict]) -> str:
        """The field's own name: its variable past the stem its intact siblings share, or the variable's last word."""
        stems = [sibling["variable"].removesuffix(f"_{sibling['name'].upper()}") for sibling in fields if MASK_MARK not in sibling["name"] and sibling["variable"].endswith(f"_{sibling['name'].upper()}")]
        stem = next((stem for stem in stems if field["variable"].startswith(f"{stem}_")), None)
        return field["variable"].removeprefix(f"{stem}_").lower() if stem else field["variable"].rsplit("_", 1)[-1].lower()
