#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect PP MXL header and first rows."""

import re
from pathlib import Path

REG = Path(__file__).resolve().parent

def cells(path):
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)

v1 = cells(REG / "0106__0506__ПП_Оригинал4.mxl")
v2 = cells(REG / "0106__0506__ПП_стало_после_испр4.mxl")

start = next(i for i, x in enumerate(v1) if x == "N" and v1[i + 1] == "Операция")
width = 33
cols = v1[start : start + width]
print("HEADER:")
for i, c in enumerate(cols):
    print(f"  {i:2d}: {c}")

print("\nFirst 3 rows BYLO (aligned):")
for row in range(3):
    base = start + width + row * width
    chunk = v1[base : base + width]
    print(f"--- row {row+1} ---")
    for col, val in zip(cols, chunk):
        print(f"  {col}: {val[:80]}")

print("\nCompare row1 BYLO vs STALO field by field:")
b1 = v1[start + width : start + 2 * width]
s1 = v2[start + width : start + 2 * width]
for col, a, b in zip(cols, b1, s1):
    mark = " !" if a != b else ""
    print(f"{mark} {col}: BYLO={a[:60]!r} | STALO={b[:60]!r}")
