#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Show duplicate contract rows detail in 03.06 CNY block."""

import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows
from compare_0106_0506_ers import PATH_STALO, propagate_accounts

CONTRACT = "ДУ 7231 (Тонковидов И.В.)"
SC = "40701156603801000004"


def main():
    rows = propagate_accounts(parse_rows(extract_hash_cells(PATH_STALO)))
    block = [
        r
        for r in rows
        if r.get("Data", "")[:10] == "03.06.2026" and r.get("NomerScheta") == SC
    ]

    print(f"STALO 03.06 CNY block: {len(block)} rows")
    print()
    positions = []
    for i, r in enumerate(block, 1):
        dog = r.get("Dogovor", "") or "<empty>"
        if CONTRACT in dog:
            positions.append(i)
            print(f"--- 7231 occurrence #{len(positions)} (block pos {i}) ---")
            print(f"  N row field: {r.get('N','')}")
            print(f"  Zagruzhat: {r.get('Zagruzhat','')}")
            print(f"  balances (all): {r.get('balances', [])}")
            print(f"  raw fields ({len(r.get('raw',[]))}): ")
            for v in r.get("raw", [])[:20]:
                print(f"    | {v[:80]}")
            if len(r.get("raw", [])) > 20:
                print(f"    ... +{len(r.get('raw', [])) - 20} more")
            print()

    # all duplicates in block
    print("=== All contracts with count > 1 in STALO 03.06 CNY ===")
    from collections import Counter
    c = Counter((r.get("Dogovor", "") or "<empty>") for r in block)
    for dog, cnt in sorted(c.items(), key=lambda x: (-x[1], x[0])):
        if cnt > 1:
            print(f"  x{cnt}  {dog[:50]}")


if __name__ == "__main__":
    main()
