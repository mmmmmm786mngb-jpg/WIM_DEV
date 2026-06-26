#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare 0306_bylo vs 0306_stalo and vs 0106 pack slice for 03.06."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows
from compare_0106_0506_ers import propagate_accounts

PATH_BYLO = SCRIPT_DIR / "0306_bylo.mxl"
PATH_STALO = SCRIPT_DIR / "0306_stalo.mxl"
PACK_BYLO = SCRIPT_DIR / "0106__0506___было.mxl"
PACK_STALO = SCRIPT_DIR / "0106__0506___стало.mxl"
TARGET_DATE = "03.06.2026"
CNY_ERS = "40701156603801000004"


def business_key(row: dict) -> tuple:
    return (
        row.get("Data", "")[:10],
        row.get("NomerScheta", ""),
        row.get("Dogovor", "") or "<empty>",
        row.get("BankSchet", ""),
    )


def contract_key(row: dict) -> tuple:
    if not row.get("Dogovor"):
        return ()
    return (
        row.get("Data", "")[:10],
        row.get("NomerScheta", ""),
        row.get("Dogovor", ""),
    )


def load_rows(path: Path) -> list[dict]:
    return propagate_accounts(parse_rows(extract_hash_cells(path)))


def filter_date(rows: list[dict], date_prefix: str) -> list[dict]:
    return [r for r in rows if r.get("Data", "")[:10] == date_prefix[:10]]


def compare_pair(label: str, rows_a: list[dict], rows_b: list[dict]) -> dict:
    cnt_a = Counter(business_key(r) for r in rows_a)
    cnt_b = Counter(business_key(r) for r in rows_b)
    diff = (cnt_a - cnt_b) + (cnt_b - cnt_a)

    cnt_ca = Counter(contract_key(r) for r in rows_a if r.get("Dogovor"))
    cnt_cb = Counter(contract_key(r) for r in rows_b if r.get("Dogovor"))
    contract_diff = (cnt_ca - cnt_cb) + (cnt_cb - cnt_ca)

    positional = 0
    for ra, rb in zip(rows_a, rows_b):
        if business_key(ra) != business_key(rb):
            positional += 1

    return {
        "label": label,
        "rows_a": len(rows_a),
        "rows_b": len(rows_b),
        "multiset_diff": len(diff),
        "contract_multiset_diff": len(contract_diff),
        "positional": positional,
        "only_a_contracts": dict(cnt_ca - cnt_cb),
        "only_b_contracts": dict(cnt_cb - cnt_ca),
        "multiset_sample": [
            {"delta": d, "key": str(k)}
            for k, d in sorted(diff.items(), key=lambda x: -abs(x[1]))[:15]
        ],
    }


def block_contract_counts(rows: list[dict], schet: str) -> Counter:
    c = Counter()
    for r in rows:
        if r.get("Data", "")[:10] == TARGET_DATE[:10] and r.get("NomerScheta") == schet:
            dog = r.get("Dogovor", "") or "<empty>"
            c[dog] += 1
    return c


def main() -> int:
    rb = load_rows(PATH_BYLO)
    rs = load_rows(PATH_STALO)

    print("=== 0306 SINGLE DAY: bylo vs stalo ===")
    r1 = compare_pair("0306_bylo vs 0306_stalo", rb, rs)
    print(json.dumps(r1, ensure_ascii=False, indent=2))
    print()

    print("=== CNY ERS block contract counts ===")
    cb = block_contract_counts(rb, CNY_ERS)
    cs = block_contract_counts(rs, CNY_ERS)
    print(f"BYLO rows in block: {sum(cb.values())}, STALO: {sum(cs.values())}")
    all_dogs = sorted(set(cb) | set(cs), key=lambda x: (-max(cb[x], cs[x]), x))
    print(f"{'Dogovor':<45} BYLO  STALO")
    for dog in all_dogs:
        b, s = cb[dog], cs[dog]
        mark = " ***" if b != s else ""
        print(f"{dog[:45]:<45} {b:4d}  {s:4d}{mark}")
    print()

    # 7730 detail
    contract = "ДУ 7730 (Михедько Р.Ю.)"
    print("=== DU 7730 all rows ===")
    for label, rows in [("BYLO", rb), ("STALO", rs)]:
        hits = [r for r in rows if contract in r.get("Dogovor", "")]
        print(f"{label}: {len(hits)}")
        for i, r in enumerate(hits, 1):
            print(
                f"  #{i} | {r.get('Data','')[:10]} | {r.get('NomerScheta')} | "
                f"{r.get('balances', [])[:2]}"
            )
    print()

    # Pack vs single day
    if PACK_BYLO.exists() and PACK_STALO.exists():
        print("=== PACK 01-05 vs SINGLE 0306 (same version) ===")
        pb = filter_date(load_rows(PACK_BYLO), TARGET_DATE)
        ps = filter_date(load_rows(PACK_STALO), TARGET_DATE)
        rb_d = filter_date(rb, TARGET_DATE)
        rs_d = filter_date(rs, TARGET_DATE)

        r_pack_b = compare_pair("pack_bylo[03.06] vs 0306_bylo", pb, rb_d)
        r_pack_s = compare_pair("pack_stalo[03.06] vs 0306_stalo", ps, rs_d)
        print("BYLO pack vs single:")
        print(f"  rows {r_pack_b['rows_a']} vs {r_pack_b['rows_b']}, "
              f"contract_diff={r_pack_b['contract_multiset_diff']}")
        print("STALO pack vs single:")
        print(f"  rows {r_pack_s['rows_a']} vs {r_pack_s['rows_b']}, "
              f"contract_diff={r_pack_s['contract_multiset_diff']}")

        if r_pack_b["contract_multiset_diff"]:
            print("  pack-only BYLO:", r_pack_b["only_a_contracts"])
            print("  single-only BYLO:", r_pack_b["only_b_contracts"])
        if r_pack_s["contract_multiset_diff"]:
            print("  pack-only STALO:", r_pack_s["only_a_contracts"])
            print("  single-only STALO:", r_pack_s["only_b_contracts"])

        cny_pack_b = block_contract_counts(pb, CNY_ERS)
        cny_pack_s = block_contract_counts(ps, CNY_ERS)
        print()
        print("CNY ERS 7730: single bylo", cb.get(contract, 0), "pack", cny_pack_b.get(contract, 0))
        print("CNY ERS 7730: single stalo", cs.get(contract, 0), "pack", cny_pack_s.get(contract, 0))

    report = {
        "single_day": r1,
        "cny_bylo": dict(cb),
        "cny_stalo": dict(cs),
    }
    out = SCRIPT_DIR / "0306_compare_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
