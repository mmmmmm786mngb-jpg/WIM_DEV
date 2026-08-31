#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze 6 parallel NDFL formation PFF measurements."""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

FOLDER = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 НовыеТесты"
)
FILES = ["Новый9.pff", "Новый10.pff", "Новый13.pff", "Новый14.pff", "Новый15.pff", "Новый16.pff"]
OUT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ"
    r"\Документация\pff_6threads_hotspots.json"
)

# },"Module",line,"code with ""quotes""",count,t1,t2,
PAT = re.compile(
    r'\},"([^"]+)",(\d+),"((?:[^"]|"")*)",(\d+),([0-9.eE+-]+),([0-9.eE+-]+),',
    re.S,
)
HDR = re.compile(
    r'\{10,"([^"]*)","[^"]*",(\d+),"",(\d+),"([^"]*)"',
)


def parse_file(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    hdr = HDR.search(text[:800])
    header = {}
    if hdr:
        header = {
            "host": hdr.group(1),
            "n1": int(hdr.group(2)),
            "n2": int(hdr.group(3)),
            "user": hdr.group(4),
        }
    rows = []
    for m in PAT.finditer(text):
        module, line, code, count, t1, t2 = m.groups()
        code = code.replace('""', '"').replace("\r\n", " ").replace("\n", " ")
        rows.append({
            "module": module,
            "line": int(line),
            "code": code[:220],
            "count": int(count),
            "t1": float(t1),
            "t2": float(t2),
        })
    return header, rows


def short_mod(mod: str) -> str:
    return mod.replace("Документ.", "Д.").replace("Обработка.", "О.").replace(
        "ОбщийМодуль.", "ОМ."
    ).replace("Справочник.", "С.").replace("РегистрСведений.", "РС.").replace(
        "РегистрНакопления.", "РН."
    ).replace("РегистрБухгалтерии.", "РБ.")


def classify(mod: str, code: str) -> str:
    blob = (mod + " " + code).lower()
    if "общиеобороты" in blob or "получитьобщиеобороты" in blob:
        return "oboroty"
    if "нкд" in blob or "расходыпонкд" in blob:
        return "nkd"
    if "запрос.выполнить" in blob or "выполнитьпакет" in blob:
        return "query"
    if "записать(" in blob or ".записать" in blob:
        return "write"
    if "обменданными" in blob or "зарегистрировать" in blob:
        return "exchange"
    if "ндфл" in blob or "начислениендфл" in blob:
        return "ndfl"
    return "other"


def main():
    per_file = {}
    all_rows = []
    for name in FILES:
        path = FOLDER / name
        header, rows = parse_file(path)
        sum_t1 = sum(r["t1"] for r in rows)
        sum_t2 = sum(r["t2"] for r in rows)
        max_t1 = max(rows, key=lambda r: r["t1"]) if rows else None
        per_file[name] = {
            "header": header,
            "rows": len(rows),
            "sum_t1": round(sum_t1, 3),
            "sum_t2": round(sum_t2, 3),
            "max_t1": {
                "t1": round(max_t1["t1"], 3),
                "t2": round(max_t1["t2"], 3),
                "n": max_t1["count"],
                "module": max_t1["module"],
                "line": max_t1["line"],
                "code": max_t1["code"][:160],
            } if max_t1 else None,
            "top_t2": [
                {
                    "t2": round(r["t2"], 4),
                    "t1": round(r["t1"], 4),
                    "n": r["count"],
                    "avg_t2": round(r["t2"] / r["count"], 4) if r["count"] else 0,
                    "module": r["module"],
                    "line": r["line"],
                    "code": r["code"][:160],
                    "cls": classify(r["module"], r["code"]),
                }
                for r in sorted(rows, key=lambda x: x["t2"], reverse=True)[:25]
            ],
            "top_t1": [
                {
                    "t1": round(r["t1"], 4),
                    "t2": round(r["t2"], 4),
                    "n": r["count"],
                    "module": r["module"],
                    "line": r["line"],
                    "code": r["code"][:160],
                    "cls": classify(r["module"], r["code"]),
                }
                for r in sorted(rows, key=lambda x: x["t1"], reverse=True)[:15]
            ],
        }
        for r in rows:
            r["file"] = name
            all_rows.append(r)
        print("FILE", name, "rows", len(rows), "sum_t2", round(sum_t2, 2),
              "sum_t1", round(sum_t1, 2), "hdr", header)

    # Aggregate by module+line+code across files
    agg = defaultdict(lambda: {
        "t2": 0.0, "t1": 0.0, "n": 0, "files": {},
        "module": "", "line": 0, "code": "",
    })
    for r in all_rows:
        key = (r["module"], r["line"], r["code"][:80])
        a = agg[key]
        a["t2"] += r["t2"]
        a["t1"] += r["t1"]
        a["n"] += r["count"]
        a["files"][r["file"]] = {
            "t2": round(r["t2"], 3),
            "t1": round(r["t1"], 3),
            "n": r["count"],
        }
        a["module"] = r["module"]
        a["line"] = r["line"]
        a["code"] = r["code"]

    top_agg_t2 = sorted(agg.values(), key=lambda x: x["t2"], reverse=True)[:40]
    top_agg_out = []
    for a in top_agg_t2:
        times = [v["t2"] for v in a["files"].values()]
        ns = [v["n"] for v in a["files"].values()]
        mean = sum(times) / len(times)
        var = sum((t - mean) ** 2 for t in times) / len(times)
        std = var ** 0.5
        top_agg_out.append({
            "t2_sum": round(a["t2"], 3),
            "t1_sum": round(a["t1"], 3),
            "n_sum": a["n"],
            "threads": len(a["files"]),
            "t2_min": round(min(times), 3),
            "t2_max": round(max(times), 3),
            "t2_mean": round(mean, 3),
            "t2_std": round(std, 3),
            "n_min": min(ns),
            "n_max": max(ns),
            "avg_call_s": round(a["t2"] / a["n"], 4) if a["n"] else 0,
            "module": a["module"],
            "line": a["line"],
            "code": a["code"][:160],
            "cls": classify(a["module"], a["code"]),
            "per_file": a["files"],
        })

    by_mod = defaultdict(lambda: {"t2": 0.0, "t1": 0.0, "n": 0})
    for r in all_rows:
        b = by_mod[r["module"]]
        b["t2"] += r["t2"]
        b["t1"] += r["t1"]
        b["n"] += r["count"]
    top_mod = [
        {"module": m, "t2": round(v["t2"], 3), "t1": round(v["t1"], 3), "n": v["n"]}
        for m, v in sorted(by_mod.items(), key=lambda x: -x[1]["t2"])[:25]
    ]

    # Query-only own time
    queries = [a for a in top_agg_out if a["cls"] == "query" or "Выполнить" in a["code"]]

    by_cls = defaultdict(lambda: {"t2": 0.0, "n": 0})
    for r in all_rows:
        c = classify(r["module"], r["code"])
        by_cls[c]["t2"] += r["t2"]
        by_cls[c]["n"] += r["count"]

    # High variance lines (contention candidates): present in all 6, std/mean high
    contention = []
    for a in agg.values():
        if len(a["files"]) < 6:
            continue
        times = [v["t2"] for v in a["files"].values()]
        mean = sum(times) / len(times)
        if mean < 1.0:
            continue
        std = (sum((t - mean) ** 2 for t in times) / len(times)) ** 0.5
        cv = std / mean if mean else 0
        if cv >= 0.15 or (max(times) - min(times)) > 5:
            contention.append({
                "t2_mean": round(mean, 3),
                "t2_std": round(std, 3),
                "cv": round(cv, 3),
                "t2_min": round(min(times), 3),
                "t2_max": round(max(times), 3),
                "n_mean": round(sum(v["n"] for v in a["files"].values()) / 6, 1),
                "module": a["module"],
                "line": a["line"],
                "code": a["code"][:160],
                "per_file": a["files"],
            })
    contention.sort(key=lambda x: -x["cv"])

    result = {
        "per_file": {k: {kk: vv for kk, vv in v.items() if kk != "top_t1"} | {"top_t1": v["top_t1"]}
                     for k, v in per_file.items()},
        "top_agg_t2": top_agg_out,
        "top_modules": top_mod,
        "by_class": {k: {"t2": round(v["t2"], 3), "n": v["n"]} for k, v in by_cls.items()},
        "contention": contention[:20],
        "queries_top": queries[:20],
    }
    # Shrink per_file for json (drop huge top lists duplication) - keep them
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", OUT)

    print("\n=== TOP AGG t2 (own) ===")
    for a in top_agg_out[:20]:
        print(
            f"{a['t2_sum']:10.2f}s mean={a['t2_mean']:8.2f} std={a['t2_std']:6.2f} "
            f"n={a['n_sum']:6d} avg={a['avg_call_s']:7.4f} {a['cls']:8s} "
            f"{short_mod(a['module'])[-55:]} L{a['line']}"
        )
        print(f"           {a['code'][:110]}")

    print("\n=== TOP MODULES t2 ===")
    for m in top_mod[:15]:
        print(f"{m['t2']:10.2f}s n={m['n']:7d} {m['module']}")

    print("\n=== CLASS ===")
    for k, v in sorted(by_cls.items(), key=lambda x: -x[1]["t2"]):
        print(f"{v['t2']:10.2f}s n={v['n']:7d} {k}")

    print("\n=== CONTENTION cv>=0.15 or spread>5s, mean t2>=1 ===")
    for c in contention[:15]:
        print(
            f"cv={c['cv']:.2f} mean={c['t2_mean']:8.2f} [{c['t2_min']:.1f}..{c['t2_max']:.1f}] "
            f"{short_mod(c['module'])[-50:]} L{c['line']}"
        )
        print(f"           {c['code'][:110]}")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
