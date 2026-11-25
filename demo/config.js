window.DEMO = {
  repo: "json-to-tables",
  title: "json-to-tables",
  tagline: "Drop in a nested JSON or JSON Lines file. Get flat, related tables (one per nested list, linked by id columns) plus a schema sheet.",
  pkg: "json_to_tables",
  packages: ["openpyxl", "sqlite3"],
  inputs: [
    { id: "input", label: "JSON or JSON Lines file", accept: ".json,.jsonl,.ndjson,.txt", sample: "samples/orders.json" },
  ],
  options: [
    { id: "root", label: "Path to the record list", type: "text", value: "data.items", placeholder: "data.items" },
    { id: "name", label: "Top table name", type: "text", value: "orders", placeholder: "root" },
  ],
  sampleNote: 'The sample is <a href="samples/orders.json">orders.json</a>: 20 synthetic orders with nested items, payments, tags and discounts. For your own file, clear the boxes above or set the path to its record list.',
  python: `
from pathlib import Path
from json_to_tables.cli import main as cli_main

def run(paths, opts):
    src = paths["input"][0]
    out = "/work/" + Path(src).stem + "-tables.xlsx"
    argv = ["flatten", src, "-o", out]
    for k in ("root", "name"):
        if opts.get(k, "").strip():
            argv += ["--" + k, opts[k].strip()]
    code, log = run_cli(cli_main, argv)
    if code != 0 or not Path(out).exists():
        return {"ok": False, "log": log, "sheets": [], "download": None}
    return {"ok": True, "log": log, "sheets": sheets_from_xlsx(out), "download": out}
`,
};
