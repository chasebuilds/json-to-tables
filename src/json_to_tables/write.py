"""Write tables to an Excel workbook, a folder of CSV files or a SQLite database."""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

from json_to_tables.flatten import Table

SQL_TYPES = {"integer": "INTEGER", "boolean": "INTEGER", "number": "REAL", "string": "TEXT"}


def safe_names(tables: dict[str, Table], limit: int, pattern: str) -> dict[str, str]:
    """Short unique names for sheets or files, kept readable."""
    out: dict[str, str] = {}
    used: set[str] = {"schema"}
    for name in tables:
        base = re.sub(pattern, "_", name)[:limit] or "table"
        cand, n = base, 2
        while cand.lower() in used:
            tail = f"~{n}"
            cand, n = base[: limit - len(tail)] + tail, n + 1
        used.add(cand.lower())
        out[name] = cand
    return out


def column_type(types: set[str]) -> str:
    real = types - {"null"}
    if not real:
        return "null"
    if real <= {"integer", "number"} and "number" in real:
        return "number"
    return real.pop() if len(real) == 1 else "mixed"


def schema_rows(tables: dict[str, Table], names: dict[str, str]) -> list[list[Any]]:
    """One line per column: where it sits, its path in the JSON (`[]` marks a list), type, fill."""

    def base(t: Table) -> str:
        if t.parent is None:
            return ""
        up = base(tables[t.parent])
        return f"{up}.{'.'.join(t.rel_path)}[]" if up else f"{'.'.join(t.rel_path)}[]"

    def json_path(t: Table, path: tuple[str, ...]) -> str:
        b = base(t)
        if path == ("value",) and t.parent:
            return b
        return f"{b}.{'.'.join(path)}" if b else ".".join(path)

    rows: list[list[Any]] = []
    for t in tables.values():
        if t.parent:
            rows.append([names[t.name], t.name, "_parent_id", f"_id in {names[t.parent]}",
                         "integer", len(t.rows)])
        for col, path in t.columns.items():
            nulls = sum(1 for r in t.rows if r.get(col) is None)
            rows.append([names[t.name], t.name, col, json_path(t, path),
                         column_type(t.types[col]), len(t.rows) - nulls])
    return rows


SCHEMA_HEAD = ["table", "full_name", "column", "json_path", "type", "filled"]


def _cell(ws: Any, value: Any) -> Any:
    """Text that starts with = stays text instead of turning into a formula."""
    if isinstance(value, str) and value.startswith("="):
        cell = WriteOnlyCell(ws, value=value)
        cell.data_type = "s"
        return cell
    return value


def write_xlsx(tables: dict[str, Table], out: Path) -> None:
    names = safe_names(tables, 31, r"[\[\]:*?/\\]")
    wb = Workbook(write_only=True)
    for t in tables.values():
        ws = wb.create_sheet(names[t.name])
        ws.append(t.header())
        for row in t.matrix():
            ws.append([_cell(ws, v) for v in row])
    ws = wb.create_sheet("Schema")
    ws.append(SCHEMA_HEAD)
    for srow in schema_rows(tables, names):
        ws.append(srow)
    wb.save(out)


def write_csv(tables: dict[str, Table], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    names = safe_names(tables, 100, r"[^\w.-]")
    for t in tables.values():
        with (out / f"{names[t.name]}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(t.header())
            for row in t.matrix():
                w.writerow(["true" if v is True else "false" if v is False else v for v in row])
    with (out / "_schema.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(SCHEMA_HEAD)
        w.writerows(schema_rows(tables, names))


def write_sqlite(tables: dict[str, Table], out: Path) -> None:
    out.unlink(missing_ok=True)
    names = safe_names(tables, 60, r"[^\w]")
    con = sqlite3.connect(out)
    try:
        for t in tables.values():
            cols = ['"_id" INTEGER PRIMARY KEY']
            if t.parent:
                cols += [f'"_parent_id" INTEGER REFERENCES "{names[t.parent]}"("_id")',
                         '"_index" INTEGER']
            for col in t.columns:
                sql = SQL_TYPES.get(column_type(t.types[col]), "")
                cols.append(f'"{col.replace(chr(34), chr(34) * 2)}" {sql}'.rstrip())
            con.execute(f'CREATE TABLE "{names[t.name]}" ({", ".join(cols)})')
            marks = ", ".join("?" * len(t.header()))
            con.executemany(f'INSERT INTO "{names[t.name]}" VALUES ({marks})', t.matrix())
        con.execute('CREATE TABLE "_schema" (' + ", ".join(f'"{h}"' for h in SCHEMA_HEAD) + ")")
        con.executemany('INSERT INTO "_schema" VALUES (?, ?, ?, ?, ?, ?)',
                        schema_rows(tables, names))
        con.commit()
    finally:
        con.close()


def write(tables: dict[str, Table], out: Path) -> str:
    suffix = out.suffix.lower()
    if suffix == ".xlsx":
        write_xlsx(tables, out)
        return "xlsx"
    if suffix in {".db", ".sqlite", ".sqlite3"}:
        write_sqlite(tables, out)
        return "sqlite"
    write_csv(tables, out)
    return "csv"
