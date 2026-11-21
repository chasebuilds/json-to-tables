import json
from collections import Counter
from pathlib import Path

import pytest

from json_to_tables import flatten, leaves, load_records, pick_root, table_leaves

ORDERS = [
    {"id": 1, "customer": {"name": "Ana", "vip": True}, "total": 9.5,
     "items": [{"sku": "A", "qty": 2, "tags": ["red", "big"]}, {"sku": "B", "qty": 1}]},
    {"id": 2, "customer": {"name": "Bo", "phone": None}, "coupon": "SAVE",
     "items": [], "grid": [[1, 2], [3]]},
]


def test_tables_and_parent_keys() -> None:
    t = flatten(ORDERS, "orders")
    assert list(t) == ["orders", "orders.items", "orders.items.tags", "orders.grid",
                       "orders.grid.value"]
    assert t["orders"].header() == ["_id", "id", "customer.name", "customer.vip", "total",
                                    "customer.phone", "coupon"]
    items = t["orders.items"]
    assert items.header()[:3] == ["_id", "_parent_id", "_index"]
    assert [(r["_parent_id"], r["sku"]) for r in items.rows] == [(1, "A"), (1, "B")]
    tags = t["orders.items.tags"]
    assert [(r["_parent_id"], r["_index"], r["value"]) for r in tags.rows] == [
        (1, 0, "red"), (1, 1, "big")]


def test_consistent_columns_and_types() -> None:
    t = flatten(ORDERS)["root"]
    m = t.matrix()
    assert len({len(r) for r in m}) == 1
    assert m[0][3] is True and m[0][4] == 9.5 and m[1][4] is None
    assert t.types["customer.phone"] == {"null"}


def test_round_trip_every_leaf_once() -> None:
    data = [*ORDERS, "loose", [1, {"a": 2}], {"e": {}, "f": []}]
    assert Counter(map(repr, leaves(data))) == Counter(map(repr, table_leaves(flatten(data))))


def test_pick_root_and_load(tmp_path: Path) -> None:
    doc = {"data": {"items": ORDERS}, "meta": {"page": 1}}
    assert pick_root(doc, "data.items.0.id") == 1
    with pytest.raises(KeyError):
        pick_root(doc, "data.nope")
    p = tmp_path / "x.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert load_records(p, "data.items") == ORDERS
    assert load_records(p) == [doc]
    jl = tmp_path / "x.jsonl"
    jl.write_text("\n".join(json.dumps(o) for o in ORDERS) + "\n\n", encoding="utf-8")
    assert load_records(jl) == ORDERS
    jl.write_text(json.dumps(doc) + "\n" + json.dumps(doc), encoding="utf-8")
    assert len(load_records(jl, "data.items")) == 4
