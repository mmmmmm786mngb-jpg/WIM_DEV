#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Замер_Р2.pff and summarize P2 (payment position) impact."""

import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PFF = BASE / "Замер_Р2.pff"
BASELINE = BASE / "reports" / "pff_hotspots_50_full_2_2.json"


def parse_pff(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    pat = re.compile(
        r'\},"([^"]+)",(\d+),"((?:\\.|[^"\\])*)",(\d+),([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+)',
        re.S,
    )
    rows = []
    for m in pat.finditer(text):
        module, line, code, count, t1, t2, t3, t4 = m.groups()
        code = code.replace("\r\n", " ").replace("\n", " ").replace('\\"', '"')
        rows.append({
            "module": module,
            "line": int(line),
            "code": code[:400],
            "count": int(count),
            "t1": float(t1),
            "t2": float(t2),
            "t3": float(t3),
            "t4": float(t4),
        })
    return rows


def main() -> None:
    rows = parse_pff(PFF)
    print("file", PFF.name, "size", PFF.stat().st_size)
    print("parsed_rows", len(rows))

    top = sorted(rows, key=lambda x: x["t1"], reverse=True)[:20]
    print("\n=== TOP t1 ===")
    for r in top:
        print(
            f"{r['t1']:10.2f}s self={r['t2']:8.2f} n={r['count']:5d} "
            f"L{r['line']:5d} ...{r['module'][-75:]}"
        )
        print(f"           {r['code'][:150]}")

    keys = (
        "ПлатежныеПозицииПоСчетамДС",
        "БанковскийСчетПоПлатежной",
        "ПодготовитьКэш",
        "КэшПлатежных",
        "СписокДоговоровДляКэша",
    )
    print("\n=== P2-RELATED (code match) ===")
    hits = []
    for r in rows:
        if any(k in r["code"] for k in keys):
            hits.append(r)
    hits.sort(key=lambda x: x["t1"], reverse=True)
    for r in hits:
        print(
            f"{r['t1']:10.3f}/{r['t2']:8.3f} n={r['count']:5d} "
            f"L{r['line']:5d} ...{r['module'][-65:]}"
        )
        print(f"           {r['code'][:160]}")

    print("\n=== ПлатежноеПоручение Manager: Execute with t1>=0.3 ===")
    for r in sorted(rows, key=lambda x: x["t1"], reverse=True):
        if "ПлатежноеПоручение" in r["module"] and "Выполнить" in r["code"] and r["t1"] >= 0.3:
            print(
                f"{r['t1']:10.3f}/{r['t2']:8.3f} n={r['count']:5d} "
                f"L{r['line']:5d} {r['code'][:120]}"
            )

    # Specific baseline lines L1388 / L1835
    print("\n=== Manager L1388 / L1835 (baseline P2/P1 query lines) ===")
    for want in (1388, 1835):
        for r in rows:
            if r["line"] == want and "ПлатежноеПоручение" in r["module"]:
                print(
                    f"L{want}: t1={r['t1']:.3f} t2={r['t2']:.3f} n={r['count']} "
                    f"{r['code'][:140]}"
                )

    # Compare to baseline JSON if present
    if BASELINE.exists():
        import json
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        print("\n=== vs baseline full_2_2 (from JSON) ===")
        print(f"baseline root ~1290s; P2 L1388 was ~514.8s n=104")
        for r in base.get("top_t1", [])[:8]:
            if "Платежн" in r.get("code", "") or r.get("line") in (1388, 2062, 1973, 1835):
                print(
                    f"  BASE t1={r['t1']:.2f} n={r['count']} L{r['line']} "
                    f"{r['code'][:100]}"
                )

    # Estimate: sum of ПлатежныеПозицииПоСчетамДС call site
    pp_sum = sum(r["t1"] for r in hits if "ПлатежныеПозицииПоСчетамДС" in r["code"])
    bank_sum = sum(r["t1"] for r in hits if "БанковскийСчетПоПлатежной" in r["code"])
    cache_sum = sum(
        r["t1"] for r in hits
        if "ПодготовитьКэш" in r["code"] or "КэшПлатежных" in r["code"]
    )
    print("\n=== SUMS (may double-count parent/child) ===")
    print(f"code contains ПлатежныеПозицииПоСчетамДС: sum_t1={pp_sum:.2f}")
    print(f"code contains БанковскийСчетПоПлатежной: sum_t1={bank_sum:.2f}")
    print(f"code contains cache prep: sum_t1={cache_sum:.2f}")

    root = top[0]["t1"] if top else 0
    print(f"\nroot_t1={root:.2f}s (~{root/60:.1f} min)")


if __name__ == "__main__":
    main()
