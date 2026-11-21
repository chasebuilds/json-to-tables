"""Round-trip check and speed on generated orders. Writes BENCHMARK.md and the README table."""

from __future__ import annotations

import argparse
import datetime as dt
import platform
import re
import sqlite3
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from benchmark.generate import generate
from json_to_tables import flatten, leaves, table_leaves
from json_to_tables.write import write_sqlite

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Score:
    records: int
    leaves: int
    found_once: int
    missing: int
    extra: int
    tables: int
    rows: int
    orphans: int
    seconds: float
    sqlite_rows_match: bool


def score(seed: int, count: int) -> Score:
    records = generate(seed, count)
    start = time.perf_counter()
    tables = flatten(records, "orders")
    seconds = time.perf_counter() - start
    want = Counter(map(repr, leaves(records)))
    got = Counter(map(repr, table_leaves(tables)))
    orphans = 0
    for t in tables.values():
        if t.parent:
            ids = len(tables[t.parent].rows)
            orphans += sum(1 for r in t.rows if not 1 <= r["_parent_id"] <= ids)
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "b.db"
        write_sqlite(tables, db)
        con = sqlite3.connect(db)
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != '_schema' "
            "ORDER BY rowid")]
        counts = [con.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in names]
        con.close()
    return Score(
        records=count, leaves=sum(want.values()),
        found_once=sum(min(n, got[k]) for k, n in want.items() if got[k] == n),
        missing=sum(max(0, n - got[k]) for k, n in want.items()),
        extra=sum(max(0, n - want[k]) for k, n in got.items()),
        tables=len(tables), rows=sum(len(t.rows) for t in tables.values()), orphans=orphans,
        seconds=seconds,
        sqlite_rows_match=counts == [len(t.rows) for t in tables.values()],
    )


def table(s: Score) -> str:
    pct = 100 * s.found_once / s.leaves
    return "\n".join([
        "| Measure | Result |",
        "|---|---:|",
        f"| Records (invented orders) | {s.records:,} |",
        f"| Values in the input | {s.leaves:,} |",
        f"| Values found exactly once, at the right place | **{pct:.1f}%** "
        f"({s.found_once:,} of {s.leaves:,}) |",
        f"| Values missing / extra | {s.missing:,} / {s.extra:,} |",
        f"| Child rows whose parent key points nowhere | {s.orphans:,} |",
        f"| Tables / rows made | {s.tables} / {s.rows:,} |",
        f"| SQLite row counts match the tables | {'yes' if s.sqlite_rows_match else 'no'} |",
        f"| Speed (flatten only) | **{s.records / s.seconds:,.0f} records/sec** |",
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261121)
    ap.add_argument("--count", type=int, default=20000)
    args = ap.parse_args()
    s = score(args.seed, args.count)
    tbl = table(s)
    today = dt.date.today().isoformat()
    doc = f"""# Benchmark

Written by `benchmark/run_benchmark.py` on {today} from a real run.
No number on this page was typed by hand.

Command: `python -m benchmark.run_benchmark --seed {args.seed} --count {args.count}`
Python {platform.python_version()} on {platform.system()}.
Flattening all {s.records:,} records took {s.seconds:.2f} s.

## Method

1. Invent {s.records:,} order records like an API export: an order with a customer object
   (nested address, sometimes a loyalty object, sometimes a null phone), 0 to 5 line items, each
   with optional tag lists and discount lists, optional payments, notes and gift flag. Keys differ
   from record to record on purpose. No real person, address or product is used.
2. Flatten them into tables.
3. List every value in the input (every string, number, true/false and null) with its record and
   full path, list indexes included.
4. Rebuild the same list from the tables: start at each cell, follow `_parent_id` up to the top
   table and use `_index` for list positions. A value counts only when it shows up exactly once
   at the same record and path with the same value and type.
5. Check that every `_parent_id` points at a real row, and that the SQLite file has the same row
   counts as the tables.

## Result

{tbl}

## What this does not show

- The round-trip check runs on the tables in memory. The Excel and CSV writers are covered by the
  tests, not this run.
- In the written files, a missing key and a `null` both become an empty cell. In memory they are
  different, and the check counts nulls.
- The data is invented and regular. Real exports with keys that contain dots, or one key that is
  an object in some records and a list in others, are covered in
  [LIMITATIONS.md](LIMITATIONS.md).
"""
    (ROOT / "BENCHMARK.md").write_text(doc, encoding="utf-8")
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = re.sub(r"<!-- benchmark:start -->.*<!-- benchmark:end -->",
                  f"<!-- benchmark:start -->\n{tbl}\n<!-- benchmark:end -->", text, flags=re.S)
    readme.write_text(text, encoding="utf-8")
    print(tbl)


if __name__ == "__main__":
    main()
