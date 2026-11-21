"""Flatten records into related tables.

Each list inside a record becomes its own table. Every row has `_id`. Child rows also have
`_parent_id` (the `_id` of the row that held the list) and `_index` (position in that list).
Nested objects become dotted columns in the same table. A list item that is a plain value goes
in a column named `value`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Leaf = tuple[int, tuple[str | int, ...], Any]


@dataclass
class Table:
    name: str
    parent: str | None
    rel_path: tuple[str, ...]
    columns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    types: dict[str, set[str]] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)

    def header(self) -> list[str]:
        keys = ["_id", "_parent_id", "_index"] if self.parent else ["_id"]
        return keys + list(self.columns)

    def matrix(self) -> list[list[Any]]:
        head = self.header()
        return [[row.get(c) for c in head] for row in self.rows]


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


def load_records(path: Path, root: str | None = None) -> list[Any]:
    """Read a .json or JSON Lines file and return the list of records."""
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        docs = [json.loads(line) for line in text.splitlines() if line.strip()]
        lines = True
    else:
        docs = [json.loads(text)]
        lines = False
    out: list[Any] = []
    for doc in docs:
        picked = pick_root(doc, root) if root else doc
        if isinstance(picked, list) and (root or not lines):
            out.extend(picked)
        else:
            out.append(picked)
    return out


def pick_root(doc: Any, root: str) -> Any:
    """Follow a dotted path like `data.items` into a document."""
    node = doc
    for part in root.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise KeyError(f"--root {root!r}: no key {part!r}")
    return node


def flatten(records: list[Any], name: str = "root") -> dict[str, Table]:
    """Flatten records into tables keyed by name. The first table is the root table."""
    tables: dict[str, Table] = {name: Table(name, None, ())}
    for i, rec in enumerate(records, 1):
        _add_row(tables, tables[name], rec, {"_id": i})
    return tables


def _add_row(tables: dict[str, Table], table: Table, item: Any, row: dict[str, Any]) -> None:
    table.rows.append(row)
    if isinstance(item, dict):
        _walk(tables, table, row, item, ())
    elif isinstance(item, list):
        _child(tables, table, row, ("value",), item)
    else:
        _set(table, row, ("value",), item)


def _walk(tables: dict[str, Table], table: Table, row: dict[str, Any], obj: dict[str, Any],
          prefix: tuple[str, ...]) -> None:
    for key, value in obj.items():
        path = (*prefix, str(key))
        if isinstance(value, dict):
            _walk(tables, table, row, value, path)
        elif isinstance(value, list):
            _child(tables, table, row, path, value)
        else:
            _set(table, row, path, value)


def _child(tables: dict[str, Table], parent: Table, prow: dict[str, Any], path: tuple[str, ...],
           items: list[Any]) -> None:
    name = f"{parent.name}.{'.'.join(path)}"
    child = tables.get(name)
    if child is None:
        child = tables[name] = Table(name, parent.name, path)
    for idx, item in enumerate(items):
        crow = {"_id": len(child.rows) + 1, "_parent_id": prow["_id"], "_index": idx}
        _add_row(tables, child, item, crow)


def _set(table: Table, row: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    col = ".".join(path)
    table.columns.setdefault(col, path)
    table.types.setdefault(col, set()).add(type_name(value))
    row[col] = value


def leaves(records: list[Any]) -> Iterator[Leaf]:
    """Every value in the input as (record number, path, value), using the table path rules."""

    def walk(node: Any, path: tuple[str | int, ...]) -> Iterator[tuple[tuple[str | int, ...], Any]]:
        if isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, (*path, str(k)))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, (*path, i) if isinstance(v, dict) else (*path, i, "value"))
        else:
            yield path, node

    for n, rec in enumerate(records, 1):
        for path, value in walk(rec, () if isinstance(rec, dict) else ("value",)):
            yield n, path, value


def table_leaves(tables: dict[str, Table]) -> Iterator[Leaf]:
    """Every filled cell rebuilt to (record number, path, value) by following the parent keys."""
    cache: dict[tuple[str, int], tuple[int, tuple[str | int, ...]]] = {}

    def locate(table: Table, row: dict[str, Any]) -> tuple[int, tuple[str | int, ...]]:
        key = (table.name, row["_id"])
        if key not in cache:
            if table.parent is None:
                cache[key] = (row["_id"], ())
            else:
                ptable = tables[table.parent]
                rec, ppath = locate(ptable, ptable.rows[row["_parent_id"] - 1])
                cache[key] = (rec, (*ppath, *table.rel_path, row["_index"]))
        return cache[key]

    for table in tables.values():
        for row in table.rows:
            rec, base = locate(table, row)
            for col, path in table.columns.items():
                if col in row:
                    yield rec, (*base, *path), row[col]
