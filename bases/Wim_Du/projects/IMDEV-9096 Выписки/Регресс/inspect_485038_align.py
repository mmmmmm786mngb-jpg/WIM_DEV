#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect raw row alignment around 485038 in STALO file."""

import re
from pathlib import Path

REG = Path(__file__).resolve().parent / "Регресс2105"
WIDTH = 33
PROBE = "485038"


def extract_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def header_start(vals: list[str]) -> int:
    return next(i for i, v in enumerate(vals) if v == "N" and vals[i + 1] == "Операция")


for tag, name in [("BYLO", "2105_2105_ПП_было.mxl"), ("STALO", "2105_2105_ПП_стало.mxl")]:
    vals = extract_cells(REG / name)
    start = header_start(vals)
    cols = vals[start : start + WIDTH]
    idx = next(i for i, v in enumerate(vals) if v == PROBE)
    print(f"=== {tag}: {PROBE} at raw index {idx} ===")
    # find row start: nearest index where vals[i].isdigit() and i <= idx and (idx-i) < WIDTH*2
    row_start = None
    for i in range(max(start + WIDTH, idx - WIDTH * 3), idx + 1):
        if vals[i].isdigit() and i + 1 < len(vals) and vals[i + 1] == "Платежное поручение":
            row_start = i
    if row_start is None:
        # fallback: align to WIDTH grid from first data row
        first_data = start + WIDTH
        offset = (idx - first_data) % WIDTH
        row_start = idx - offset
    print(f"row_start={row_start}, offset in row={idx - row_start}")
    chunk = vals[row_start : row_start + WIDTH]
    for col, val in zip(cols, chunk):
        mark = ">>" if val == PROBE else "  "
        print(f"{mark} {col}: {val[:90]!r}")
    print()

# Count misaligned rows in STALO: rows where col[1] != Платежное поручение but col[0] is digit
vals = extract_cells(REG / "2105_2105_ПП_стало.mxl")
start = header_start(vals)
cols = vals[start : start + WIDTH]
bad = good = 0
i = start + WIDTH
while i + WIDTH <= len(vals):
    if vals[i].isdigit():
        if vals[i + 1] == "Платежное поручение":
            good += 1
            i += WIDTH
        else:
            bad += 1
            i += 1
    else:
        i += 1
print(f"STALO aligned PP rows: {good}, misaligned digit-starts: {bad}")

vals_b = extract_cells(REG / "2105_2105_ПП_было.mxl")
start = header_start(vals_b)
bad = good = 0
i = start + WIDTH
while i + WIDTH <= len(vals_b):
    if vals_b[i].isdigit():
        if vals_b[i + 1] == "Платежное поручение":
            good += 1
            i += WIDTH
        else:
            bad += 1
            i += 1
    else:
        i += 1
print(f"BYLO aligned PP rows: {good}, misaligned digit-starts: {bad}")

# Find 485038 in STALO by scanning all WIDTH windows
vals = extract_cells(REG / "2105_2105_ПП_стало.mxl")
start = header_start(vals)
cols = vals[start : start + WIDTH]
for i in range(start + WIDTH, len(vals) - WIDTH):
    if PROBE not in vals[i : i + WIDTH]:
        continue
    chunk = vals[i : i + WIDTH]
    if chunk[0].isdigit() and chunk[1] == "Платежное поручение":
        print("STALO aligned window containing 485038:")
        for col, val in zip(cols, chunk):
            print(f"  {col}: {val[:90]!r}")
        break
else:
    print("STALO: no aligned WIDTH window with 485038 as proper PP row")
    for i in range(start + WIDTH, len(vals) - WIDTH):
        if PROBE in vals[i : i + WIDTH]:
            pos = vals[i : i + WIDTH].index(PROBE)
            print(f"  found in window row_start={i}, column={cols[pos] if pos < len(cols) else pos}")
