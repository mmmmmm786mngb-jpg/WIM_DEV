#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import Counter
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows
from compare_0106_0506_ers import PATH_BYLO, PATH_STALO, propagate_accounts

rb = propagate_accounts(parse_rows(extract_hash_cells(PATH_BYLO)))
rs = propagate_accounts(parse_rows(extract_hash_cells(PATH_STALO)))


def contract_multiset(rows, data_prefix, schet):
    c = Counter()
    for r in rows:
        if r.get("Data", "")[:10] == data_prefix and r.get("NomerScheta") == schet:
            dog = r.get("Dogovor", "")
            if dog:
                c[dog] += 1
    return c


cb = contract_multiset(rb, "03.06.2026", "40701156603801000004")
cs = contract_multiset(rs, "03.06.2026", "40701156603801000004")
print("03.06 CNY contract multiset equal:", cb == cs)
print("7730 count BYLO:", cb.get("ДУ 7730 (Михедько Р.Ю.)", 0))
print("7730 count STALO:", cs.get("ДУ 7730 (Михедько Р.Ю.)", 0))
if cb != cs:
    print("only BYLO:", dict(cb - cs))
    print("only STALO:", dict(cs - cb))

all_b = Counter(
    (r.get("Data", "")[:10], r.get("NomerScheta", ""), r.get("Dogovor", ""))
    for r in rb
    if r.get("Dogovor")
)
all_s = Counter(
    (r.get("Data", "")[:10], r.get("NomerScheta", ""), r.get("Dogovor", ""))
    for r in rs
    if r.get("Dogovor")
)
diff = (all_b - all_s) + (all_s - all_b)
print()
print("Global contract multiset (with duplicates), diffs:", len(diff))
for k, d in sorted(diff.items(), key=lambda x: -abs(x[1])):
    print(f"  delta={d:+d} | {k[0]} | {k[1]} | {k[2][:40]}")
