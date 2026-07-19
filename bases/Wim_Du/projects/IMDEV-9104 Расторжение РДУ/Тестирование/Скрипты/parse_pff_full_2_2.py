#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Замер_50_Договоров_2_2.pff (full contour)."""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PFF = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9104 "
    r"Расторжение РДУ\Тестирование\Замер_50_Договоров_2_2.pff"
)
OUT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9104 "
    r"Расторжение РДУ\Тестирование\reports\pff_hotspots_50_full_2_2.json"
)


def main() -> None:
    if len(sys.argv) > 1:
        pff = Path(sys.argv[1])
    else:
        pff = PFF

    text = pff.read_text(encoding="utf-8-sig")
    print("file", pff.name, "size", pff.stat().st_size, "chars", len(text))

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
            "code": code[:300],
            "count": int(count),
            "t1": float(t1),
            "t2": float(t2),
            "t3": float(t3),
            "t4": float(t4),
        })

    print("parsed_rows", len(rows))
    print("sum_t1", round(sum(r["t1"] for r in rows), 3))
    print("sum_t2", round(sum(r["t2"] for r in rows), 3))

    # which processing
    names = defaultdict(int)
    for r in rows:
        if "внТест" in r["module"] or "ПлатежноеПоручение" in r["module"]:
            names[r["module"].split("\\")[-1]] += 1
    print("name_hits", dict(names))

    print("\n===TOP_t1===")
    top_t1 = sorted(rows, key=lambda x: x["t1"], reverse=True)[:50]
    for r in top_t1:
        print(
            f"{r['t1']:10.4f}s self={r['t2']:8.4f} n={r['count']:5d} "
            f"{r['module'][-95:]} L{r['line']}"
        )
        print(f"           {r['code'][:160]}")

    print("\n===TOP_t2_self===")
    top_t2 = sorted(rows, key=lambda x: x["t2"], reverse=True)[:40]
    for r in top_t2:
        print(
            f"{r['t2']:10.4f}s tot={r['t1']:8.4f} n={r['count']:5d} "
            f"{r['module'][-95:]} L{r['line']}"
        )
        print(f"           {r['code'][:160]}")

    print("\n===PP_MANAGER_ALL_t1>=0.05===")
    pp = [r for r in rows if "ПлатежноеПоручение" in r["module"] and r["t1"] >= 0.05]
    pp.sort(key=lambda x: x["t1"], reverse=True)
    for r in pp[:40]:
        print(
            f"{r['t1']:10.4f}/{r['t2']:8.4f} n={r['count']:5d} L{r['line']} "
            f"{r['code'][:140]}"
        )

    print("\n===TARGET_LINES 1388 1835===")
    for want in (1388, 1835):
        hits = [r for r in rows if r["line"] == want and "ПлатежноеПоручение" in r["module"]]
        for r in hits:
            print(
                f"L{want}: t1={r['t1']:.4f} t2={r['t2']:.4f} n={r['count']} "
                f"{r['code'][:180]}"
            )

    print("\n===CALL_SITES in full contour EPF===")
    for want in (2010, 2062, 1973, 894, 913, 963, 904, 923, 932):
        hits = [r for r in rows if r["line"] == want and "ПолныйКонтур" in r["module"]]
        for r in hits:
            print(
                f"L{want}: t1={r['t1']:.4f} t2={r['t2']:.4f} n={r['count']} "
                f"{r['code'][:160]}"
            )

    print("\n===FULL_CONTOUR high t1===")
    for r in top_t1:
        if "ПолныйКонтур" in r["module"] or (
            "ПлатежноеПоручение" in r["module"] and r["t1"] >= 1
        ):
            print(
                f"{r['t1']:10.4f}/{r['t2']:8.4f} n={r['count']:5d} "
                f"{r['module'][-90:]} L{r['line']}"
            )
            print(f"           {r['code'][:150]}")

    by_mod = defaultdict(lambda: {"t1": 0.0, "t2": 0.0, "n": 0})
    for r in rows:
        short = r["module"].split("\\")[-1].split("/")[-1]
        by_mod[short]["t1"] += r["t1"]
        by_mod[short]["t2"] += r["t2"]
        by_mod[short]["n"] += r["count"]
    print("\n===MODS_by_t2===")
    mods = sorted(by_mod.items(), key=lambda x: x[1]["t2"], reverse=True)[:25]
    for name, a in mods:
        print(f"{a['t2']:10.3f}s t1={a['t1']:10.3f} n={a['n']:7d} {name}")

    OUT.write_text(
        json.dumps(
            {
                "source": str(pff),
                "parsed_rows": len(rows),
                "sum_t1": sum(r["t1"] for r in rows),
                "sum_t2": sum(r["t2"] for r in rows),
                "top_t1": top_t1,
                "top_t2": top_t2,
                "pp_manager": pp[:50],
                "mods_by_t2": [{"module": k, **v} for k, v in mods],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()
