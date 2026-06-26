#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detailed regression compare: 0106__0506___bylo vs stalo."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import (  # noqa: E402
    extract_hash_cells,
    parse_rows,
    row_signature,
)

PATH_BYLO = SCRIPT_DIR / "0106__0506___было.mxl"
PATH_STALO = SCRIPT_DIR / "0106__0506___стало.mxl"
REPORT_JSON = SCRIPT_DIR / "0106__0506___compare_report.json"


def format_sig(sig: tuple) -> str:
    data, schet, dog, bank, n = sig
    return f"N={n} | {data} | {schet} | {dog} | {bank}"


def full_row_key(row: dict) -> tuple:
  return (
        row.get("N", ""),
        row.get("Zagruzhat", ""),
        row.get("Zagruzhena", ""),
        row.get("Data", ""),
        row.get("Dogovor", ""),
        row.get("BankSchet", ""),
        row.get("NomerScheta", ""),
        tuple(row.get("balances", [])),
    )


def compare_blocks(rows_bylo: list[dict], rows_stalo: list[dict]) -> list[dict]:
    """Group by (Data, NomerScheta) and compare contract sets and order."""
    def group(rows: list[dict]) -> dict[tuple, list[dict]]:
        g: dict[tuple, list[dict]] = defaultdict(list)
        for row in rows:
            key = (row.get("Data", ""), row.get("NomerScheta", ""))
            if key[0] and key[1]:
                g[key].append(row)
        return g

    gb = group(rows_bylo)
    gs = group(rows_stalo)
    all_keys = sorted(set(gb) | set(gs))
    issues = []

    for key in all_keys:
        b_rows = gb.get(key, [])
        s_rows = gs.get(key, [])
        data, schet = key
        contracts_b = [r.get("Dogovor", "") for r in b_rows if r.get("Dogovor")]
        contracts_s = [r.get("Dogovor", "") for r in s_rows if r.get("Dogovor")]
        set_b, set_s = set(contracts_b), set(contracts_s)

        issue = {
            "data": data,
            "schet": schet,
            "rows_bylo": len(b_rows),
            "rows_stalo": len(s_rows),
            "contracts_bylo": len(contracts_b),
            "contracts_stalo": len(contracts_s),
            "set_equal": set_b == set_s,
            "order_equal": contracts_b == contracts_s,
            "only_bylo": sorted(set_b - set_s),
            "only_stalo": sorted(set_s - set_b),
        }
        if (
            issue["rows_bylo"] != issue["rows_stalo"]
            or not issue["set_equal"]
            or not issue["order_equal"]
        ):
            issues.append(issue)

    return issues


def main() -> int:
    vals_bylo = extract_hash_cells(PATH_BYLO)
    vals_stalo = extract_hash_cells(PATH_STALO)
    rows_bylo = parse_rows(vals_bylo)
    rows_stalo = parse_rows(vals_stalo)

    cnt_b = Counter(row_signature(r) for r in rows_bylo)
    cnt_s = Counter(row_signature(r) for r in rows_stalo)
    multiset_diff = (cnt_b - cnt_s) + (cnt_s - cnt_b)

    full_b = Counter(full_row_key(r) for r in rows_bylo)
    full_s = Counter(full_row_key(r) for r in rows_stalo)
    full_diff = (full_b - full_s) + (full_s - full_b)

    positional = []
    for index, pair in enumerate(zip(rows_bylo, rows_stalo), start=1):
        rb, rs = pair
        if row_signature(rb) != row_signature(rs):
            positional.append(
                {
                    "index": index,
                    "bylo": format_sig(row_signature(rb)),
                    "stalo": format_sig(row_signature(rs)),
                }
            )

    block_issues = compare_blocks(rows_bylo, rows_stalo)

    dates_bylo = Counter(r.get("Data", "") for r in rows_bylo if r.get("Data"))
    dates_stalo = Counter(r.get("Data", "") for r in rows_stalo if r.get("Data"))

    report = {
        "files": {
            "bylo": str(PATH_BYLO),
            "stalo": str(PATH_STALO),
            "size_bylo": PATH_BYLO.stat().st_size,
            "size_stalo": PATH_STALO.stat().st_size,
        },
        "rows": {
            "bylo": len(rows_bylo),
            "stalo": len(rows_stalo),
            "delta": len(rows_stalo) - len(rows_bylo),
        },
        "dates": {
            "bylo": dict(sorted(dates_bylo.items())),
            "stalo": dict(sorted(dates_stalo.items())),
        },
        "multiset_business_key": {
            "diff_count": len(multiset_diff),
            "only_bylo": [
                {"key": format_sig(k), "delta": d}
                for k, d in sorted((cnt_b - cnt_s).items(), key=lambda x: -x[1])
            ],
            "only_stalo": [
                {"key": format_sig(k), "delta": d}
                for k, d in sorted((cnt_s - cnt_b).items(), key=lambda x: -x[1])
            ],
        },
        "full_row_match": {
            "diff_count": len(full_diff),
            "diffs": [
                {"delta": d, "key": str(k)[:200]}
                for k, d in sorted(full_diff.items(), key=lambda x: -abs(x[1]))[:50]
            ],
        },
        "positional": {
            "count": len(positional),
            "compared": min(len(rows_bylo), len(rows_stalo)),
            "samples": positional[:30],
        },
        "block_issues": block_issues,
        "verdict": {
            "multiset_ok": len(multiset_diff) == 0,
            "full_row_ok": len(full_diff) == 0,
            "positional_ok": len(positional) == 0 and len(rows_bylo) == len(rows_stalo),
            "functional_ok": len(multiset_diff) == 0,
        },
    }

    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== REGRESS 01.06-05.06: bylo vs stalo ===")
    print(f"Rows: {len(rows_bylo)} / {len(rows_stalo)} (delta {report['rows']['delta']:+d})")
    print(f"File size: {report['files']['size_bylo']} / {report['files']['size_stalo']} bytes")
    print()
    print("Rows per date BYLO:", dates_bylo)
    print("Rows per date STALO:", dates_stalo)
    print()
    print(f"Multiset (Data, Schet, Dogovor, Bank, N): {len(multiset_diff)} diff types")
    if multiset_diff:
        for key, delta in sorted(multiset_diff.items(), key=lambda x: -abs(x[1]))[:20]:
            print(f"  delta={delta:+d} | {format_sig(key)}")
    print()
    print(f"Full row (incl. balances): {len(full_diff)} diff types")
    if full_diff:
        for key, delta in sorted(full_diff.items(), key=lambda x: -abs(x[1]))[:15]:
            print(f"  delta={delta:+d} | {str(key)[:120]}")
    print()
    print(
        f"Positional diffs: {len(positional)} / {min(len(rows_bylo), len(rows_stalo))}"
    )
    if positional:
        for item in positional[:15]:
            print(f"  #{item['index']}")
            print(f"    BYLO:  {item['bylo']}")
            print(f"    STALO: {item['stalo']}")
    print()
    print(f"Block issues (date+account): {len(block_issues)}")
    for issue in block_issues[:20]:
        print(
            f"  {issue['data']} | {issue['schet']} | "
            f"rows {issue['rows_bylo']}/{issue['rows_stalo']} | "
            f"set={issue['set_equal']} order={issue['order_equal']}"
        )
        if issue["only_bylo"]:
            print(f"    only BYLO: {issue['only_bylo']}")
        if issue["only_stalo"]:
            print(f"    only STALO: {issue['only_stalo']}")
    print()
    v = report["verdict"]
    print(
        "VERDICT: "
        f"multiset={'OK' if v['multiset_ok'] else 'FAIL'} | "
        f"full_row={'OK' if v['full_row_ok'] else 'DIFF'} | "
        f"positional={'OK' if v['positional_ok'] else 'REORDER/DIFF'}"
    )
    print(f"Report: {REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
