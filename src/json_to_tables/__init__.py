"""Turn nested JSON and JSON Lines into tidy related tables."""

from json_to_tables.flatten import Table, flatten, leaves, load_records, pick_root, table_leaves

__all__ = ["Table", "flatten", "leaves", "load_records", "pick_root", "table_leaves"]
__version__ = "0.1.0"
