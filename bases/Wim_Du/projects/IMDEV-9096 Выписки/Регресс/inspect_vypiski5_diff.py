#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent
sys.path.insert(0, str(REG))
from compare_mxl import extract_hash_cells, parse_rows

def biz_key(row):
    return (
        row.get("Data", ""),
        row.get("NomerScheta", ""),
        row.get("Dogovor", "") or "<empty>",
        row.get("BankSchet", ""),
        tuple(row.get("balances", [])),
    )

left = parse_rows(extract_hash_cells(REG / "0106__0506___стало.mxl"))
right = parse_rows(extract_hash_cells(REG / "0106__0506__Выписки_стало_после_испр5.mxl"))
cl = Counter(biz_key(r) for r in left)
cr = Counter(biz_key(r) for r in right)
only_l = cl - cr
only_r = cr - cl
print("rows", len(left), len(right))
print("only in stalo:", sum(only_l.values()), "types", len(only_l))
print("only in vypiski5:", sum(only_r.values()), "types", len(only_r))
for key, delta in (only_l + only_r).most_common(10):
    print(" delta", delta, "|", key[0][:19], key[1], key[2][:40], key[3][:25])
