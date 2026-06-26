#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep functional compare: contracts and balances per date+account."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows  # noqa: E402

PATH_BYLO = SCRIPT_DIR / "0106__0506___было.mxl"
PATH_STALO = SCRIPT_DIR / "0106__0506___стало.mxl"


def business_key(row: dict) -> tuple:
    """Key without row index N - stable for ERS splits."""
    return (
        row.get("Data", ""),
        row.get("NomerScheta", ""),
        row.get("Dogovor", ""),
        row.get("BankSchet", ""),
    )


def balance_key(row: dict) -> tuple:
    return business_key(row) + (tuple(row.get("balances", [])),)


def group_by_date_account(rows: list[dict]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        data = row.get("Data", "")
        schet = row.get("NomerScheta", "")
        if data and schet:
            groups[(data, schet)].append(row)
    return groups


def main() -> int:
    rows_bylo = parse_rows(extract_hash_cells(PATH_BYLO))
    rows_stalo = parse_rows(extract_hash_cells(PATH_STALO))

    # 1. Multiset without N
    cnt_b = Counter(business_key(r) for r in rows_bylo)
    cnt_s = Counter(business_key(r) for r in rows_stalo)
    biz_diff = (cnt_b - cnt_s) + (cnt_s - cnt_b)

    only_b = cnt_b - cnt_s
    only_s = cnt_s - cnt_b

    # 2. Balances included
    bal_b = Counter(balance_key(r) for r in rows_bylo)
    bal_s = Counter(balance_key(r) for r in rows_stalo)
    bal_diff = (bal_b - bal_s) + (bal_s - bal_b)

    # 3. Per block: contract sets + balance map
    gb = group_by_date_account(rows_bylo)
    gs = group_by_date_account(rows_stalo)

    contract_set_diffs = []
    balance_diffs = []
    order_only_blocks = []

    for key in sorted(set(gb) | set(gs)):
        b_rows = gb.get(key, [])
        s_rows = gs.get(key, [])

        contracts_b = Counter(
            r.get("Dogovor", "") or "<empty>"
            for r in b_rows
        )
        contracts_s = Counter(
            r.get("Dogovor", "") or "<empty>"
            for r in s_rows
        )

        if contracts_b != contracts_s:
            contract_set_diffs.append(
                {
                    "data": key[0],
                    "schet": key[1],
                    "only_bylo": dict(contracts_b - contracts_s),
                    "only_stalo": dict(contracts_s - contracts_b),
                }
            )

        # balances per contract
        def bal_map(rows: list[dict]) -> dict[str, Counter]:
            m: dict[str, Counter] = defaultdict(Counter)
            for r in rows:
                dog = r.get("Dogovor", "") or "<empty>"
                m[dog][tuple(r.get("balances", []))] += 1
            return m

        bm_b = bal_map(b_rows)
        bm_s = bal_map(s_rows)
        all_dogs = set(bm_b) | set(bm_s)
        for dog in all_dogs:
            cb = bm_b.get(dog, Counter())
            cs = bm_s.get(dog, Counter())
            if cb != cs:
                balance_diffs.append(
                    {
                        "data": key[0],
                        "schet": key[1],
                        "dogovor": dog,
                        "only_bylo": dict(cb - cs),
                        "only_stalo": dict(cs - cb),
                    }
                )

        order_b = [r.get("Dogovor", "") or "<empty>" for r in b_rows]
        order_s = [r.get("Dogovor", "") or "<empty>" for r in s_rows]
        if contracts_b == contracts_s and order_b != order_s:
            order_only_blocks.append(
                {
                    "data": key[0],
                    "schet": key[1],
                    "rows": len(b_rows),
                }
            )

    # 4. Rows with contract in bylo but different in stalo at same position - skip
    # Count positional reorder within blocks
    total_reorder_rows = 0
    for key in sorted(set(gb) & set(gs)):
        b_rows = gb[key]
        s_rows = gs[key]
        if len(b_rows) != len(s_rows):
            continue
        contracts_b = [r.get("Dogovor", "") or "<empty>" for r in b_rows]
        contracts_s = [r.get("Dogovor", "") or "<empty>" for r in s_rows]
        if Counter(contracts_b) == Counter(contracts_s):
            for cb, cs in zip(contracts_b, contracts_s):
                if cb != cs:
                    total_reorder_rows += 1

    report = {
        "rows": len(rows_bylo),
        "business_key_diff_count": len(biz_diff),
        "balance_key_diff_count": len(bal_diff),
        "contract_set_diff_blocks": len(contract_set_diffs),
        "balance_diff_entries": len(balance_diffs),
        "order_only_blocks": len(order_only_blocks),
        "reordered_rows_in_equal_blocks": total_reorder_rows,
    }

    print("=== DEEP FUNCTIONAL COMPARE 01.06-05.06 ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print()

    print(f"Business key (Data, Schet, Dogovor, Bank) - NO row N:")
    print(f"  diff types: {len(biz_diff)}")
    if only_b:
        print("  only in BYLO (top 15):")
        for k, d in only_b.most_common(15):
            print(f"    x{d} | {k}")
    if only_s:
        print("  only in STALO (top 15):")
        for k, d in only_s.most_common(15):
            print(f"    x{d} | {k}")
    print()

    print(f"Balance+contract diff types: {len(bal_diff)}")
    if balance_diffs:
        print("  balance mismatches (first 20):")
        for item in balance_diffs[:20]:
            print(
                f"    {item['data'][:10]} | {item['schet']} | {item['dogovor'][:40]}"
            )
            if item["only_bylo"]:
                print(f"      BYLO: {item['only_bylo']}")
            if item["only_stalo"]:
                print(f"      STALO: {item['only_stalo']}")
    print()

    print(f"Contract SET diffs per date+account: {len(contract_set_diffs)}")
    for item in contract_set_diffs[:20]:
        print(f"  {item['data'][:10]} | {item['schet']}")
        print(f"    only BYLO: {item['only_bylo']}")
        print(f"    only STALO: {item['only_stalo']}")
    print()

    print(f"Blocks with SAME contract set but different ORDER: {len(order_only_blocks)}")
    for item in order_only_blocks[:10]:
        print(f"  {item['data'][:10]} | {item['schet']} | {item['rows']} rows")
    print(f"Total row positions reordered (within equal blocks): {total_reorder_rows}")

    functional_ok = (
        len(contract_set_diffs) == 0
        and len(balance_diffs) == 0
        and len(biz_diff) == 0
    )
    print()
    print(
        "FUNCTIONAL VERDICT:",
        "OK (only order may differ)" if functional_ok else "FAIL (real data diffs)",
    )

    out = SCRIPT_DIR / "0106__0506___deep_compare.json"
    out.write_text(
        json.dumps(
            {
                "report": report,
                "contract_set_diffs": contract_set_diffs,
                "balance_diffs": balance_diffs,
                "business_only_bylo": [
                    {"key": k, "count": d} for k, d in only_b.most_common(50)
                ],
                "business_only_stalo": [
                    {"key": k, "count": d} for k, d in only_s.most_common(50)
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
