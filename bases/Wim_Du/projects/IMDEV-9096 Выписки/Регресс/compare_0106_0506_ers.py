#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ERS-aware compare: propagate account, group by date+bank block."""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, is_account, parse_rows  # noqa: E402

PATH_BYLO = SCRIPT_DIR / "0106__0506___было.mxl"
PATH_STALO = SCRIPT_DIR / "0106__0506___стало.mxl"


def propagate_accounts(rows: list[dict]) -> list[dict]:
    """Fill NomerScheta from previous row in same ERS block."""
    current_date = ""
    current_schet = ""
    result = []
    for row in rows:
        r = dict(row)
        if r.get("Data"):
            current_date = r["Data"]
        if r.get("NomerScheta"):
            current_schet = r["NomerScheta"]
        elif r.get("N") and is_account(r["N"].replace(" ", "")):
            current_schet = r["N"].replace(" ", "")
            r["NomerScheta"] = current_schet
        elif not r.get("NomerScheta") and current_schet:
            r["NomerScheta"] = current_schet
        if not r.get("Data") and current_date:
            r["Data"] = current_date
        result.append(r)
    return result


def block_key(row: dict) -> tuple:
    return (
        row.get("Data", ""),
        row.get("NomerScheta", ""),
        row.get("BankSchet", ""),
    )


def contract_balance_sig(row: dict) -> tuple:
    return (
        row.get("Dogovor", "") or "<empty>",
        tuple(row.get("balances", [])),
    )


def main() -> int:
    rows_bylo = propagate_accounts(parse_rows(extract_hash_cells(PATH_BYLO)))
    rows_stalo = propagate_accounts(parse_rows(extract_hash_cells(PATH_STALO)))

    # Global multiset: date + account + contract + balances
    sig_b = Counter(
        (
            row.get("Data", ""),
            row.get("NomerScheta", ""),
            row.get("Dogovor", "") or "<empty>",
            tuple(row.get("balances", [])),
        )
        for row in rows_bylo
        if row.get("Data") and row.get("NomerScheta")
    )
    sig_s = Counter(
        (
            row.get("Data", ""),
            row.get("NomerScheta", ""),
            row.get("Dogovor", "") or "<empty>",
            tuple(row.get("balances", [])),
        )
        for row in rows_stalo
        if row.get("Data") and row.get("NomerScheta")
    )
    global_diff = (sig_b - sig_s) + (sig_s - sig_b)

    # Per block
    gb: dict[tuple, list[dict]] = defaultdict(list)
    gs: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows_bylo:
        k = block_key(row)
        if k[0] and k[1]:
            gb[k].append(row)
    for row in rows_stalo:
        k = block_key(row)
        if k[0] and k[1]:
            gs[k].append(row)

    contract_diffs = []
    order_diffs = []
    balance_diffs = []

    for key in sorted(set(gb) | set(gs)):
        br = gb.get(key, [])
        sr = gs.get(key, [])

        cb = Counter(contract_balance_sig(r) for r in br)
        cs = Counter(contract_balance_sig(r) for r in sr)
        if cb != cs:
            balance_diffs.append(
                {
                    "block": key,
                    "only_bylo": dict(cb - cs),
                    "only_stalo": dict(cs - cb),
                }
            )

        contracts_b = Counter(r.get("Dogovor", "") or "<empty>" for r in br)
        contracts_s = Counter(r.get("Dogovor", "") or "<empty>" for r in sr)
        if contracts_b != contracts_s:
            contract_diffs.append(
                {
                    "block": key,
                    "only_bylo": dict(contracts_b - contracts_s),
                    "only_stalo": dict(contracts_s - contracts_b),
                }
            )
        elif [r.get("Dogovor", "") or "<empty>" for r in br] != [
            r.get("Dogovor", "") or "<empty>" for r in sr
        ]:
            order_diffs.append(
                {
                    "block": key,
                    "rows": len(br),
                    "bylo_order_sample": [
                        r.get("Dogovor", "") or "<empty>" for r in br[:8]
                    ],
                    "stalo_order_sample": [
                        r.get("Dogovor", "") or "<empty>" for r in sr[:8]
                    ],
                }
            )

    # Dates summary
    dates_b = Counter(r.get("Data", "")[:10] for r in rows_bylo if r.get("Data"))
    dates_s = Counter(r.get("Data", "")[:10] for r in rows_stalo if r.get("Data"))

    report = {
        "rows": len(rows_bylo),
        "rows_equal": len(rows_bylo) == len(rows_stalo),
        "global_contract_balance_diffs": len(global_diff),
        "block_contract_diffs": len(contract_diffs),
        "block_balance_diffs": len(balance_diffs),
        "block_order_only_diffs": len(order_diffs),
        "dates_bylo": dict(dates_b),
        "dates_stalo": dict(dates_s),
    }

    print("=== ERS-AWARE COMPARE 01.06-05.06 ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print()

    if global_diff:
        print("Global diffs (date, schet, dogovor, balances) - top 20:")
        for k, d in sorted(global_diff.items(), key=lambda x: -abs(x[1]))[:20]:
            data, schet, dog, bal = k
            print(f"  delta={d:+d} | {data[:10]} | {schet} | {dog[:35]} | bal={bal[:2]}...")
    else:
        print("Global contract+balance multiset: IDENTICAL")
    print()

    print(f"Blocks with contract COUNT diff: {len(contract_diffs)}")
    for item in contract_diffs[:10]:
        print(f"  {item['block']}")
        print(f"    BYLO: {item['only_bylo']}")
        print(f"    STALO: {item['only_stalo']}")
    print()

    print(f"Blocks with balance diff (per contract): {len(balance_diffs)}")
    for item in balance_diffs[:10]:
        print(f"  {item['block']}")
    print()

    print(f"Blocks with ORDER diff only (same contract multiset): {len(order_diffs)}")
    total_reorder = sum(item["rows"] for item in order_diffs)
    print(f"  total rows in reordered blocks: {total_reorder}")
    for item in order_diffs[:5]:
        print(f"  {item['block'][0][:10]} | {item['block'][1]} | {item['rows']} rows")
        print(f"    BYLO:  {item['bylo_order_sample']}")
        print(f"    STALO: {item['stalo_order_sample']}")

    functional_ok = len(contract_diffs) == 0 and len(balance_diffs) == 0 and len(global_diff) == 0
    print()
    print(
        "VERDICT:",
        "FUNCTIONAL OK" if functional_ok else "FUNCTIONAL DIFF",
        "| order-only blocks:", len(order_diffs),
    )

    out = SCRIPT_DIR / "0106__0506___ers_compare.json"
    out.write_text(
        json.dumps(
            {
                "report": report,
                "contract_diffs": contract_diffs,
                "balance_diffs": balance_diffs,
                "order_diffs": order_diffs[:50],
                "global_diff_sample": [
                    {"key": k, "delta": d}
                    for k, d in sorted(global_diff.items(), key=lambda x: -abs(x[1]))[:30]
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
