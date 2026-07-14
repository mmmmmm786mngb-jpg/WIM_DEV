#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse IMDEV-9105 Отладчик_100.pff into hotspot summary."""

import re
import json
from collections import defaultdict
from pathlib import Path

PFF = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9105 "
    r"Загрузка договоров РДУ\Тестирование\Отладчик_100.pff"
)
OUT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9105 "
    r"Загрузка договоров РДУ\Тестирование\reports\pff_hotspots_100.json"
)


def main() -> None:
    text = PFF.read_text(encoding="utf-8-sig")
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
            "code": code[:200],
            "count": int(count),
            "t1": float(t1),
            "t2": float(t2),
            "t3": float(t3),
            "t4": float(t4),
        })

    print("parsed_rows", len(rows))
    print("sum_t1", round(sum(r["t1"] for r in rows), 3))
    print("sum_t2", round(sum(r["t2"] for r in rows), 3))

    top_t1 = sorted(rows, key=lambda x: x["t1"], reverse=True)[:40]
    top_t2 = sorted(rows, key=lambda x: x["t2"], reverse=True)[:40]

    print("\n===TOP_t1_with_children===")
    for r in top_t1[:25]:
        print(f"{r['t1']:10.4f}s self={r['t2']:8.4f} n={r['count']:5d} {r['module'][-80:]} L{r['line']}")
        print(f"           {r['code'][:130]}")

    print("\n===TOP_t2_self===")
    for r in top_t2[:25]:
        print(f"{r['t2']:10.4f}s tot={r['t1']:8.4f} n={r['count']:5d} {r['module'][-80:]} L{r['line']}")
        print(f"           {r['code'][:130]}")

    # Aggregate by module
    by_mod = defaultdict(lambda: {"t1": 0.0, "t2": 0.0, "n": 0})
    for r in rows:
        short = r["module"].split("\\")[-1].split("/")[-1]
        by_mod[short]["t1"] += r["t1"]
        by_mod[short]["t2"] += r["t2"]
        by_mod[short]["n"] += r["count"]

    print("\n===MODS_by_t2===")
    mods = sorted(by_mod.items(), key=lambda x: x[1]["t2"], reverse=True)[:30]
    for name, a in mods:
        print(f"{a['t2']:10.3f}s t1={a['t1']:10.3f} n={a['n']:6d} {name}")

    # Focus keywords for create path
    keys = (
        "создать", "заполн", "поручен", "договор", "аналит", "инвест",
        "учетн", "вознагражд", "торгов", "записать", "проведен",
        "историятстатус", "историястатус", "внтест", "кеш", "сопостав",
    )
    print("\n===FOCUS_t1>0.05===")
    focus = []
    for r in sorted(rows, key=lambda x: x["t1"], reverse=True):
        blob = (r["module"] + " " + r["code"]).lower()
        if any(k in blob for k in keys) and r["t1"] >= 0.05:
            focus.append(r)
            if len(focus) <= 50:
                print(
                    f"{r['t1']:9.4f}/{r['t2']:8.4f} n={r['count']:5d} "
                    f"{r['module'][-70:]} L{r['line']}"
                )
                print(f"          {r['code'][:130]}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "parsed_rows": len(rows),
                "sum_t1": sum(r["t1"] for r in rows),
                "sum_t2": sum(r["t2"] for r in rows),
                "top_t1": top_t1,
                "top_t2": top_t2,
                "mods_by_t2": [{"module": k, **v} for k, v in mods],
                "focus": focus[:80],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()
