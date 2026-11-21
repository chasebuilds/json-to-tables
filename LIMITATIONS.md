# Limitations

What json-to-tables does not do, or does poorly. Read this before trusting the output.

## Shape

- **Keys that contain a dot can collide.** A key `"a.b"` and a nested `{"a": {"b": ...}}` both
  become column `a.b`, and the later one wins in that row. Rename such keys first.
- **A key that is an object in one record and a list in another** gives dotted columns in the
  parent table and also a child table. Nothing is lost, but the data is split across two places.
- **A key that is a value in one record and an object in another** (`"tags": "x"` and
  `"tags": {"a": 1}`) gives column `tags` and column `tags.a`. Nothing is lost.
- **Empty objects and empty lists leave no trace.** `{}` and `[]` make no cell and no row.
- **Lists of lists** become a chain of tables ending in `.value`. They are correct but awkward.

## Values

- **Missing and `null` look the same in files.** Both are an empty cell in Excel and CSV and
  `NULL` in SQLite. The Schema sheet `filled` count treats both as empty.
- **CSV has no types.** Numbers and `true`/`false` are written as text, as CSV always does.
- **Excel limits apply.** Over 1,048,576 rows in one table will fail. Very long text (over 32,767
  characters) is cut by Excel when opened. Large integers above 15 digits lose precision in Excel,
  not in SQLite or CSV.
- **Dates stay text.** `"2026-03-01T10:00:00Z"` is not turned into a date.
- **No cleaning.** Spelling, trimming, de-duplication and type fixes are out of scope.

## Size

- **The whole file is read into memory**, and all tables are built before writing. Files of a few
  hundred MB need several times that in RAM.
- **One file per run.** To combine many exports, concatenate them into one JSON Lines file.

## Names

- **Sheet names are cut to 31 characters** (Excel's limit) and given a `~2` style suffix when two
  cut names clash. SQLite table names replace anything that is not a letter, digit or underscore
  with `_`. The Schema sheet (or `_schema` table or file) lists the full name for each.
- **`_parent_id` is a row number in the parent table, not an ID from the data.** Keep the data's
  own ID column (it is still there) if the tables will be loaded somewhere else in pieces.
