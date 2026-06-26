#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect 4 diff blocks and contract 7730."""

import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows
from compare_0106_0506_ers import PATH_BYLO, PATH_STALO, propagate_accounts

TARGET = "ДУ 7730"
DIFF_BLOCKS = [
    ("03.06.2026 0:00:00", "40701156603801000004", "р/с_ВТБ_ДС_CNY_ЕРС"),
    ("04.06.2026 0:00:00", "40701810000030000413", "р/с_ВТБ_ДС_RUR_ЕРС"),
    ("02.06.2026 0:00:00", "40701810000030000413", "р/с_ВТБ_ДС_RUR_ЕРС"),
    ("02.06.2026 0:00:00", "40701810977100000564", ""),
]


def dump_block(rows, key):
    data, schet, bank = key
    out = []
    for r in rows:
        if (
            r.get("Data") == data
            and r.get("NomerScheta") == schet
            and (not bank or r.get("BankSchet") == bank)
        ):
            out.append(r)
    return out


def main():
    rb = propagate_accounts(parse_rows(extract_hash_cells(PATH_BYLO)))
    rs = propagate_accounts(parse_rows(extract_hash_cells(PATH_STALO)))

    print("=== Contract 7730 counts ===")
    for label, rows in [("BYLO", rb), ("STALO", rs)]:
        c = Counter(
            (r.get("Data", "")[:10], r.get("NomerScheta", ""), r.get("Dogovor", ""))
            for r in rows
            if TARGET in r.get("Dogovor", "")
        )
        print(label, dict(c))
    print()

    for key in DIFF_BLOCKS:
        print("=" * 60)
        print("BLOCK", key)
        bb = dump_block(rb, key)
        bs = dump_block(rs, key)
        print(f"rows BYLO={len(bb)} STALO={len(bs)}")

        def summary(rows):
            return Counter(
                (r.get("Dogovor", "") or "<empty>", tuple(r.get("balances", [])))
                for r in rows
            )

        cb, cs = summary(bb), summary(bs)
        print("only BYLO:", dict(cb - cs))
        print("only STALO:", dict(cs - cb))
        print("BYLO contracts:", [r.get("Dogovor", "") or "<empty>" for r in bb])
        print("STALO contracts:", [r.get("Dogovor", "") or "<empty>" for r in bs])
        print()


if __name__ == "__main__":
    main()
