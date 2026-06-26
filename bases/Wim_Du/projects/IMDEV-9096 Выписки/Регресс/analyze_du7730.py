#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detailed analysis of DU 7730 in 0106__0506 regression files."""

import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows
from compare_0106_0506_ers import PATH_BYLO, PATH_STALO, propagate_accounts

CONTRACT = "ДУ 7730 (Михедько Р.Ю.)"
CNY_ERS = "40701156603801000004"
RUR_IND = "40701810725602000078"


def find_rows(rows: list[dict], label: str) -> list[dict]:
    hits = []
    for idx, row in enumerate(rows, start=1):
        if CONTRACT in row.get("Dogovor", ""):
            hits.append(
                {
                    "file": label,
                    "index": idx,
                    "N": row.get("N", ""),
                    "Zagruzhat": row.get("Zagruzhat", ""),
                    "Zagruzhena": row.get("Zagruzhena", ""),
                    "Data": row.get("Data", ""),
                    "Dogovor": row.get("Dogovor", ""),
                    "BankSchet": row.get("BankSchet", ""),
                    "NomerScheta": row.get("NomerScheta", ""),
                    "balances": row.get("balances", []),
                    "raw_len": len(row.get("raw", [])),
                }
            )
    return hits


def context_rows(rows: list[dict], hit_index: int, before: int = 2, after: int = 2) -> list[dict]:
    """hit_index is 1-based row number in parsed list."""
    i = hit_index - 1
    start = max(0, i - before)
    end = min(len(rows), i + after + 1)
    out = []
    for j in range(start, end):
        r = rows[j]
        out.append(
            {
                "pos": j + 1,
                "marker": ">>>" if j == i else "   ",
                "Dogovor": r.get("Dogovor", "") or "<empty>",
                "BankSchet": r.get("BankSchet", ""),
                "NomerScheta": r.get("NomerScheta", ""),
                "balances": r.get("balances", [])[:4],
            }
        )
    return out


def block_rows(rows: list[dict], data: str, schet: str) -> list[dict]:
    return [
        r
        for r in rows
        if r.get("Data", "")[:10] == data[:10] and r.get("NomerScheta") == schet
    ]


def main() -> int:
    rb = propagate_accounts(parse_rows(extract_hash_cells(PATH_BYLO)))
    rs = propagate_accounts(parse_rows(extract_hash_cells(PATH_STALO)))

    hits_b = find_rows(rb, "BYLO")
    hits_s = find_rows(rs, "STALO")

    print("=== ALL DU 7730 OCCURRENCES ===")
    print(f"BYLO: {len(hits_b)} rows")
    for h in hits_b:
        bal = " / ".join(h["balances"]) if h["balances"] else "(no balances)"
        print(
            f"  #{h['index']:4d} | {h['Data'][:10]} | {h['NomerScheta']} | "
            f"{h['BankSchet']} | {bal}"
        )
    print()
    print(f"STALO: {len(hits_s)} rows")
    for h in hits_s:
        bal = " / ".join(h["balances"]) if h["balances"] else "(no balances)"
        print(
            f"  #{h['index']:4d} | {h['Data'][:10]} | {h['NomerScheta']} | "
            f"{h['BankSchet']} | {bal}"
        )
    print()

    # Focus: 03.06 CNY ERS block
    print("=== BLOCK 03.06.2026 CNY ERS (40701156603801000004) ===")
    bb = block_rows(rb, "03.06.2026", CNY_ERS)
    bs = block_rows(rs, "03.06.2026", CNY_ERS)
    print(f"Rows in block: BYLO={len(bb)}, STALO={len(bs)}")
    print()

    def dump_block(label, block):
        print(f"--- {label} ({len(block)} rows) ---")
        for i, r in enumerate(block, 1):
            dog = r.get("Dogovor", "") or "<empty>"
            bal = " | ".join(r.get("balances", [])[:4]) or "-"
            mark = " *** 7730 ***" if CONTRACT in dog else ""
            print(f"  {i:2d}. {dog[:45]:45s} | {bal}{mark}")
        print()

    dump_block("BYLO", bb)
    dump_block("STALO", bs)

    # Context around each 7730 in 03.06 block
    print("=== CONTEXT around 7730 in 03.06 CNY block ===")
    for label, rows_all, block in [("BYLO", rb, bb), ("STALO", rs, bs)]:
        positions = [i for i, r in enumerate(block) if CONTRACT in r.get("Dogovor", "")]
        print(f"{label}: 7730 at positions {positions} in block (1-based: {[p+1 for p in positions]})")
        for p in positions:
            # find global index
            global_idx = None
            for gi, r in enumerate(rows_all):
                if r is block[p]:
                    global_idx = gi + 1
                    break
            print(f"  Block pos {p+1}, global row #{global_idx}")
            for ctx in context_rows(rows_all, global_idx, 1, 1):
                print(
                    f"    {ctx['marker']} #{ctx['pos']} {ctx['Dogovor'][:40]} | "
                    f"{ctx['balances']}"
                )
        print()

    # Compare balances for 7730 rows on 03.06
    b7730 = [r for r in bb if CONTRACT in r.get("Dogovor", "")]
    s7730 = [r for r in bs if CONTRACT in r.get("Dogovor", "")]
    print("=== 7730 balances on 03.06 CNY ===")
    for i, r in enumerate(b7730, 1):
        print(f"BYLO #{i}: {r.get('balances')}")
    for i, r in enumerate(s7730, 1):
        print(f"STALO #{i}: {r.get('balances')}")
    print()

    # Other dates with 7730
    print("=== 7730 on other dates ===")
    for label, hits in [("BYLO", hits_b), ("STALO", hits_s)]:
        for h in hits:
            if h["Data"][:10] != "03.06.2026":
                print(
                    f"{label} #{h['index']} | {h['Data'][:10]} | "
                    f"{h['NomerScheta']} | {h['BankSchet']} | {h['balances']}"
                )

    report = {
        "contract": CONTRACT,
        "total_bylo": len(hits_b),
        "total_stalo": len(hits_s),
        "hits_bylo": hits_b,
        "hits_stalo": hits_s,
        "block_0306_bylo_count": len(bb),
        "block_0306_stalo_count": len(bs),
        "block_0306_7730_bylo": [r.get("balances") for r in b7730],
        "block_0306_7730_stalo": [r.get("balances") for r in s7730],
    }
    out = SCRIPT_DIR / "du7730_analysis.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
