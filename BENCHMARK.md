# Benchmark

Written by `benchmark/run_benchmark.py` on 2026-11-21 from a real run.
No number on this page was typed by hand.

Command: `python -m benchmark.run_benchmark --seed 20261121 --count 20000`
Python 3.11.15 on Windows.
Flattening all 20,000 records took 0.48 s.

## Method

1. Invent 20,000 order records like an API export: an order with a customer object
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

| Measure | Result |
|---|---:|
| Records (invented orders) | 20,000 |
| Values in the input | 426,604 |
| Values found exactly once, at the right place | **100.0%** (426,604 of 426,604) |
| Values missing / extra | 0 / 0 |
| Child rows whose parent key points nowhere | 0 |
| Tables / rows made | 5 / 123,829 |
| SQLite row counts match the tables | yes |
| Speed (flatten only) | **41,694 records/sec** |

## What this does not show

- The round-trip check runs on the tables in memory. The Excel and CSV writers are covered by the
  tests, not this run.
- In the written files, a missing key and a `null` both become an empty cell. In memory they are
  different, and the check counts nulls.
- The data is invented and regular. Real exports with keys that contain dots, or one key that is
  an object in some records and a list in others, are covered in
  [LIMITATIONS.md](LIMITATIONS.md).
