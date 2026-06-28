#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent / "Регресс2105"
WIDTH = 33
CORE = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")


def extract_cells(path):
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def parse_primary(vals):
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
    return rows


def ck(row):
    return tuple(row.get(c, "").strip() for c in CORE)


rb = parse_primary(extract_cells(REG / "2105_2105_ПП_было.mxl"))
rs = parse_primary(extract_cells(REG / "2105_2105_ПП_стало.mxl"))
cb, cs = Counter(ck(r) for r in rb), Counter(ck(r) for r in rs)

by_date_b = Counter(r.get("Дата", "") for r in rb)
by_date_s = Counter(r.get("Дата", "") for r in rs)
print("Payments per date:")
for d in sorted(set(by_date_b) | set(by_date_s)):
    print(f"  {d}: BYLO={by_date_b[d]} STALO={by_date_s[d]}")

only_b = cb - cs
only_s = cs - cb
dates_b = Counter(k[0] for k in only_b.elements())
dates_s = Counter(k[0] for k in only_s.elements())
print("Only BYLO by date:", dict(dates_b))
print("Only STALO by date:", dict(dates_s))

print("ONLY STALO samples:")
for k in list(only_s.elements())[:5]:
    print(" ", k[0], k[1], k[2], k[5][:60])

# Sum amounts only BYLO vs only STALO on 21.05
def parse_sum(s):
    return float(s.replace(" ", "").replace(",", "."))

sum_b = sum(parse_sum(k[2]) for k in only_b.elements() if k[0].startswith("21.05"))
sum_s = sum(parse_sum(k[2]) for k in only_s.elements() if k[0].startswith("21.05"))
print(f"21.05 only BYLO total sum: {sum_b:,.2f}")
print(f"21.05 only STALO total sum: {sum_s:,.2f}")
