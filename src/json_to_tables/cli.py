"""Command line: j2t flatten export.json -o tables.xlsx"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from json_to_tables.flatten import flatten, load_records
from json_to_tables.write import write


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="j2t", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    fl = sub.add_parser("flatten", help="turn a JSON or JSON Lines file into related tables")
    fl.add_argument("input", type=Path)
    fl.add_argument("-o", "--out", type=Path, default=Path("tables.xlsx"),
                    help=".xlsx workbook, .db/.sqlite database, or a folder for CSV files")
    fl.add_argument("--root", help="dotted path to the record list, like data.items")
    fl.add_argument("--name", help="name of the top table (default: last part of --root or 'root')")
    args = ap.parse_args(argv)

    try:
        records = load_records(args.input, args.root)
    except (OSError, json.JSONDecodeError, KeyError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    name = args.name or (args.root.split(".")[-1] if args.root else "root")
    tables = flatten(records, name)
    kind = write(tables, args.out)
    rows = sum(len(t.rows) for t in tables.values())
    print(f"{len(records)} records: {len(tables)} tables, {rows} rows")
    print(f"Wrote {args.out} ({kind})")
    return 0
