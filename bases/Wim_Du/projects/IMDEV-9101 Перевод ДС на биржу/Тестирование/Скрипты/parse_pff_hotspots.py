#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse 1C PFF performance profile into hotspots."""

import re
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    pff = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9101 "
        r"Перевод ДС на биржу\Тестирование\Новый4_массовое_Замеры_0107_1307.pff"
    )
    text = pff.read_text(encoding="utf-8-sig")

    # },"Module",lineno,"code",count,t1,t2,t3,t4
    pat = re.compile(
        r'\},"([^"]+)",(\d+),"((?:\\.|[^"\\])*)",(\d+),([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+)',
        re.S,
    )

    rows = []
    for m in pat.finditer(text):
        module, line, code, count, t1, t2, t3, t4 = m.groups()
        code = code.replace("\r\n", " ").replace("\n", " ")
        if len(code) > 140:
            code = code[:137] + "..."
        rows.append({
            "module": module,
            "line": int(line),
            "code": code,
            "count": int(count),
            "t1": float(t1),
            "t2": float(t2),
            "t3": float(t3),
            "t4": float(t4),
        })

    print("parsed_rows", len(rows))
    print("sum_t1", round(sum(r["t1"] for r in rows), 3))
    print("sum_t2", round(sum(r["t2"] for r in rows), 3))

    for label, key in [("TOP_t1_with_children", "t1"), ("TOP_t2_self", "t2")]:
        print("\n===" + label + "===")
        for r in sorted(rows, key=lambda x: x[key], reverse=True)[:30]:
            print(
                f"{r[key]:10.4f}s n={r['count']:5d} "
                f"{r['module'][:75]} L{r['line']}"
            )
            print(f"           {r['code'][:120]}")

    print("\n===MODS_by_t2===")
    agg = defaultdict(lambda: {"t1": 0.0, "t2": 0.0})
    for r in rows:
        agg[r["module"]]["t1"] += r["t1"]
        agg[r["module"]]["t2"] += r["t2"]
    for mod, a in sorted(agg.items(), key=lambda x: x[1]["t2"], reverse=True)[:25]:
        print(f"{a['t2']:10.3f}s t1={a['t1']:10.3f} {mod[:100]}")

    print("\n===MODS_by_t1===")
    for mod, a in sorted(agg.items(), key=lambda x: x[1]["t1"], reverse=True)[:25]:
        print(f"{a['t1']:10.3f}s t2={a['t2']:10.3f} {mod[:100]}")

    # Interesting subsets
    print("\n===STATUS_RELATED_t1===")
    for r in sorted(rows, key=lambda x: x["t1"], reverse=True):
        blob = (r["module"] + " " + r["code"]).lower()
        if any(k in blob for k in (
            "историятстатус", "историястатус", "статус", "сохранитьтекущий",
            "изменитьстатус", "imdev9101"
        )):
            if r["t1"] < 0.05:
                continue
            print(
                f"{r['t1']:9.4f}/{r['t2']:8.4f} n={r['count']:5d} "
                f"{r['module'][:60]} L{r['line']}"
            )
            print(f"          {r['code'][:120]}")

    print("\n===WRITE_POST_FILL_t1===")
    for r in sorted(rows, key=lambda x: x["t1"], reverse=True)[:80]:
        blob = (r["module"] + " " + r["code"]).lower()
        if any(k in blob for k in (
            "записать", "проведен", "заполнить", "обработкпроведен",
            "обработкапроведения", "передзаписью", "призаписи", "движен",
            "формирован", "счет", "ndsl", "ндфл"
        )):
            print(
                f"{r['t1']:9.4f}/{r['t2']:8.4f} n={r['count']:5d} "
                f"{r['module'][:60]} L{r['line']}"
            )
            print(f"          {r['code'][:120]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
