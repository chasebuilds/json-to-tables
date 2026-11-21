"""Make invented order API records. Seeded, so the same seed gives the same file.

Nothing here is real: names are built from syllables, emails use example.com, SKUs are random.
Records differ on purpose: optional keys, nulls, empty lists, mixed nesting.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

SYL = ["ka", "lo", "mir", "ten", "va", "dro", "sel", "an", "bri", "cor", "eth", "lun"]
STATUS = ["paid", "pending", "shipped", "refunded"]
TAGS = ["gift", "fragile", "promo", "bulk", "rush"]


def _word(rng: random.Random, n: int = 2) -> str:
    return "".join(rng.choice(SYL) for _ in range(n)).capitalize()


def order(rng: random.Random, n: int) -> dict[str, Any]:
    first, last = _word(rng), _word(rng, 3)
    customer: dict[str, Any] = {
        "id": f"C{rng.randint(1000, 9999)}",
        "name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}@example.com",
        "address": {"city": _word(rng, 3) + " City", "zip": f"{rng.randint(0, 99999):05d}"},
    }
    if rng.random() < 0.3:
        customer["phone"] = None
    if rng.random() < 0.2:
        tier = rng.choice(["gold", "silver"])
        customer["loyalty"] = {"tier": tier, "points": rng.randint(0, 900)}
    items = []
    for _ in range(rng.randint(0, 5)):
        item: dict[str, Any] = {"sku": f"SKU-{rng.randint(100, 999)}", "qty": rng.randint(1, 4),
                                "price": round(rng.uniform(2, 120), 2)}
        if rng.random() < 0.4:
            item["tags"] = rng.sample(TAGS, rng.randint(0, 3))
        if rng.random() < 0.25:
            item["discounts"] = [{"code": _word(rng).upper(), "amount": round(rng.uniform(1, 9), 2)}
                                 for _ in range(rng.randint(1, 2))]
        items.append(item)
    rec: dict[str, Any] = {
        "order_id": n,
        "created_at": f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}T10:00:00Z",
        "status": rng.choice(STATUS),
        "customer": customer,
        "items": items,
        "total": round(sum(i["price"] * i["qty"] for i in items), 2),
    }
    if rng.random() < 0.3:
        rec["payments"] = [{"method": rng.choice(["card", "wallet"]), "ok": rng.random() < 0.9}]
    if rng.random() < 0.15:
        rec["notes"] = rng.choice(["leave at door", "", "=call first", None])
    if rng.random() < 0.1:
        rec["gift"] = True
    return rec


def generate(seed: int, count: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    return [order(rng, n) for n in range(1, count + 1)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--out", type=Path, default=Path("samples/orders.json"))
    args = ap.parse_args()
    data = {"data": {"items": generate(args.seed, args.count)}, "meta": {"page": 1}}
    args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
