import csv
import json
import sqlite3
from pathlib import Path

from openpyxl import load_workbook

from json_to_tables.cli import main

DOC = {"data": {"items": [
    {"id": 1, "note": "=1+1", "paid": True, "lines": [{"sku": "A", "price": 2.5}]},
    {"id": 2, "extra": {"k": None}, "lines": [{"sku": "B"}, {"sku": "C", "price": 1}]},
]}}


def _src(tmp_path: Path) -> Path:
    p = tmp_path / "export.json"
    p.write_text(json.dumps(DOC), encoding="utf-8")
    return p


def test_xlsx(tmp_path: Path, capsys: object) -> None:
    out = tmp_path / "t.xlsx"
    assert main(["flatten", str(_src(tmp_path)), "-o", str(out), "--root", "data.items"]) == 0
    wb = load_workbook(out)
    assert wb.sheetnames == ["items", "items.lines", "Schema"]
    rows = list(wb["items"].values)
    assert rows[0] == ("_id", "id", "note", "paid", "extra.k")
    assert rows[1] == (1, 1, "=1+1", True, None)
    lines = list(wb["items.lines"].values)
    assert lines[3] == (3, 2, 1, "C", 1)
    schema = list(wb["Schema"].values)
    assert ("items.lines", "items.lines", "price", "lines[].price", "number", 2) in schema


def test_csv_and_sqlite(tmp_path: Path) -> None:
    src = _src(tmp_path)
    assert main(["flatten", str(src), "-o", str(tmp_path / "out"), "--root", "data.items"]) == 0
    with (tmp_path / "out" / "items.csv").open(encoding="utf-8") as fh:
        assert list(csv.reader(fh))[1] == ["1", "1", "=1+1", "true", ""]
    assert (tmp_path / "out" / "_schema.csv").exists()
    db = tmp_path / "t.db"
    assert main(["flatten", str(src), "-o", str(db), "--root", "data.items", "--name", "o"]) == 0
    con = sqlite3.connect(db)
    got = con.execute('SELECT o.id, l.sku FROM "o_lines" l JOIN o ON o._id = l._parent_id '
                      "ORDER BY l._id").fetchall()
    con.close()
    assert got == [(1, "A"), (2, "B"), (2, "C")]


def test_errors(tmp_path: Path) -> None:
    assert main(["flatten", str(tmp_path / "missing.json")]) == 2
    assert main(["flatten", str(_src(tmp_path)), "--root", "nope"]) == 2


def test_long_sheet_names(tmp_path: Path) -> None:
    deep = {"a" * 40: [{"b" * 40: [1]}]}
    p = tmp_path / "d.json"
    p.write_text(json.dumps([deep]), encoding="utf-8")
    out = tmp_path / "d.xlsx"
    assert main(["flatten", str(p), "-o", str(out)]) == 0
    names = load_workbook(out).sheetnames
    assert len(names) == 4 and len(set(names)) == 4 and all(len(n) <= 31 for n in names)
