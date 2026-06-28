#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare PP by Date+Number using grid scan (not drift-prone parser)."""

import re
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent / "Регресс2105"
WIDTH = 33


def extract_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def header_start(vals: list[str]) -> int:
    return next(i for i, v in enumerate(vals) if v == "N" and vals[i + 1] == "Операция")


def parse_pp_grid(vals: list[str]) -> list[dict]:
    start = header_start(vals)
    cols = vals[start : start + WIDTH]
    rows = []
    i = start + WIDTH
    while i + WIDTH <= len(vals):
        chunk = vals[i : i + WIDTH]
        if chunk[0].isdigit() and chunk[1] == "Платежное поручение":
            rows.append(dict(zip(cols, chunk)))
            i += WIDTH
        else:
            i += 1
    return rows


def parse_pp_stream(vals: list[str]) -> list[dict]:
    """Old parser: digit + PP at i and i+1 only."""
    start = header_start(vals)
    cols = vals[start : start + WIDTH]
    rows = []
    i = start + WIDTH
    while i + WIDTH <= len(vals):
        if vals[i].isdigit() and vals[i + 1] == "Платежное поручение":
            rows.append(dict(zip(cols, vals[i : i + WIDTH])))
            i += WIDTH
        else:
            i += 1
    return rows


for tag, name in [("BYLO", "2105_2105_ПП_было.mxl"), ("STALO", "2105_2105_ПП_стало.mxl")]:
    vals = extract_cells(REG / name)
    grid = parse_pp_grid(vals)
    stream = parse_pp_stream(vals)
    dn_grid = Counter((r.get("Дата", ""), r.get("Номер", "")) for r in grid)
    print(f"{tag}: grid rows={len(grid)}, stream rows={len(stream)}")
    print(f"  485038 in grid: {dn_grid.get(('21.05.2026', '485038'), 0)}")

grid_b = parse_pp_grid(extract_cells(REG / "2105_2105_ПП_было.mxl"))
grid_s = parse_pp_grid(extract_cells(REG / "2105_2105_ПП_стало.mxl"))

dn_b = Counter((r.get("Дата", ""), r.get("Номер", "")) for r in grid_b)
dn_s = Counter((r.get("Дата", ""), r.get("Номер", "")) for r in grid_s)
dn_diff = (dn_b - dn_s) + (dn_s - dn_b)

CORE = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")


def core(row):
    return tuple(row.get(c, "").strip() for c in CORE)


cb = Counter(core(r) for r in grid_b)
cs = Counter(core(r) for r in grid_s)
core_diff = (cb - cs) + (cs - cb)

print()
print("Compare via GRID parser (fixed WIDTH alignment):")
print(f"  Date+Number diff types: {len(dn_diff)} only_b={sum((dn_b-dn_s).values())} only_s={sum((dn_s-dn_b).values())}")
print(f"  Core diff types: {len(core_diff)} only_b={sum((cb-cs).values())} only_s={sum((cs-cb).values())}")

row_b = next(r for r in grid_b if r.get("Номер") == "485038")
row_s = next(r for r in grid_s if r.get("Номер") == "485038")
print()
print("485038 core identical:", core(row_b) == core(row_s))
print("485038 field diffs:")
for c in row_b:
    if row_b.get(c) != row_s.get(c):
        print(f"  {c}: BYLO={row_b.get(c)!r}"[:100])
        print(f"         STALO={row_s.get(c)!r}"[:100])
