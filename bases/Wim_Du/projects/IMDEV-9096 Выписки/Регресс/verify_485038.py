#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify payment 485038 in both PP files."""

import re
from pathlib import Path

REG = Path(__file__).resolve().parent / "Регресс2105"
WIDTH = 33
PROBE = "485038"


def extract_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def parse_primary(vals: list[str]) -> tuple[list[str], list[dict]]:
    start = next(i for i, v in enumerate(vals) if v == "N" and vals[i + 1] == "Операция")
    cols = vals[start : start + WIDTH]
    rows = []
    i = start + WIDTH
    while i + WIDTH <= len(vals):
        if vals[i].isdigit() and vals[i + 1] == "Платежное поручение":
            rows.append(dict(zip(cols, vals[i : i + WIDTH])))
            i += WIDTH
        else:
            i += 1
    return cols, rows


def find_raw_context(vals: list[str], needle: str) -> list[int]:
    return [i for i, v in enumerate(vals) if needle in v]


for tag, name in [("BYLO", "2105_2105_ПП_было.mxl"), ("STALO", "2105_2105_ПП_стало.mxl")]:
    vals = extract_cells(REG / name)
    cols, rows = parse_primary(vals)
    hits = [r for r in rows if r.get("Номер", "").strip() == PROBE]
    raw_idx = find_raw_context(vals, PROBE)
    print(f"=== {tag} {name} ===")
    print(f"raw cell hits: {len(raw_idx)} at indices {raw_idx[:5]}")
    print(f"parsed PP rows with Nomer={PROBE}: {len(hits)}")
    for row in hits:
        for c in ("N", "Операция", "Дата", "Номер", "Сумма", "Ключ выписки", "Загружен", "Назначение платежа"):
            v = row.get(c, "")
            if c == "Назначение платежа":
                v = v[:80]
            print(f"  {c}: {v!r}")
    print()

# Compare full row for 485038
_, rb = parse_primary(extract_cells(REG / "2105_2105_ПП_было.mxl"))
_, rs = parse_primary(extract_cells(REG / "2105_2105_ПП_стало.mxl"))
row_b = next(r for r in rb if r.get("Номер") == PROBE)
row_s = next(r for r in rs if r.get("Номер") == PROBE)
print("=== FIELD DIFF for 485038 ===")
for c in row_b:
    if row_b.get(c) != row_s.get(c):
        print(f"  {c}:")
        print(f"    BYLO:  {row_b.get(c)!r}"[:120])
        print(f"    STALO: {row_s.get(c)!r}"[:120])

CORE = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")
print("core identical:", tuple(row_b.get(c, "") for c in CORE) == tuple(row_s.get(c, "") for c in CORE))
