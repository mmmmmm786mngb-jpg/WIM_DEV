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

# Date+Number match
dn_b = Counter((r.get("Дата", ""), r.get("Номер", "")) for r in rb)
dn_s = Counter((r.get("Дата", ""), r.get("Номер", "")) for r in rs)
dn_diff = (dn_b - dn_s) + (dn_s - dn_b)
print("Date+Number multiset identical:", not dn_diff)
print("DN only BYLO", sum((dn_b - dn_s).values()), "only STALO", sum((dn_s - dn_b).values()))

# sorted core compare
sb = sorted(rb, key=ck)
ss = sorted(rs, key=ck)
match = sum(1 for a, b in zip(sb, ss) if ck(a) == ck(b))
print("Sorted core positional match:", match, "of", len(sb))

only_b = list((cb - cs).elements())[:5]
print("ONLY BYLO samples:")
for k in only_b:
    print(" ", k[0], k[1], k[2], k[5][:60])

# Vypiski positional 14
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_mxl import extract_hash_cells, parse_rows, row_signature

rbv = parse_rows(extract_hash_cells(REG / "2105_2105_ВЫПИСКИ_было.mxl"))
rsv = parse_rows(extract_hash_cells(REG / "2105_2105_ВЫПИСКИ_стало.mxl"))
print()
print("VYPISKI positional diffs detail:")
for i, (a, b) in enumerate(zip(rbv, rsv)):
    if row_signature(a) != row_signature(b):
        print(
            f" idx={i} BYLO N={a.get('N')} {a.get('Dogovor','')[:40]} | "
            f"STALO N={b.get('N')} {b.get('Dogovor','')[:40]} | "
            f"{a.get('Data','')[:10]} {a.get('BankSchet','')}"
        )
