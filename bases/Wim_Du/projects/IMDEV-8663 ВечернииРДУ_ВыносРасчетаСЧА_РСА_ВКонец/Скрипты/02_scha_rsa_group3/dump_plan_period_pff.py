#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump PFF rows for plan/period query research."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze_stage34_pff import parse_pff

ROOT = HERE.parents[1]
SRC = ROOT / "Тесты_Этап2_34"
OUT = ROOT / "Тестирование" / "reports" / "_stage34_analysis"

KEYS = (
    "Справочник.РегламентныеПериоды.МодульМенеджера",
    "Документ.ПланРегламентныхОперацийДУ.МодульМенеджера",
    "Документ.ПланРегламентныхОперацийДУ.МодульОбъекта",
)


def slim_rec(r: dict) -> dict:
    return {
        "line": r["line"],
        "src": r["src"][:160],
        "count": r["count"],
        "time_pure": round(r["time_pure"], 4),
        "time_total": round(r["time_total"], 4),
        "per_call_ms": round(1000.0 * r["time_pure"] / r["count"], 3) if r["count"] else 0.0,
    }


def dump(info: dict) -> dict:
    out = {}
    for k in KEYS:
        recs = [r for r in info["records"] if r["module"] == k]
        recs.sort(key=lambda r: -r["time_pure"])
        out[k] = {
            "rows": len(recs),
            "pure": round(sum(r["time_pure"] for r in recs), 3),
            "total": round(sum(r["time_total"] for r in recs), 3),
            "lines": [slim_rec(r) for r in recs if r["time_pure"] >= 0.5],
        }
    return out


def main() -> int:
    was = parse_pff(SRC / "1308_Было.pff")
    now = parse_pff(SRC / "1308_Стало.pff")
    payload = {"was": dump(was), "now": dump(now)}
    path = OUT / "plan_period_lines.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK", path)
    for label, block in payload.items():
        print("====", label)
        for k, v in block.items():
            print(k, "pure", v["pure"], "lines", len(v["lines"]))
            for r in v["lines"][:12]:
                print(
                    "  L%s n=%s pure=%s ms=%s %s"
                    % (r["line"], r["count"], r["time_pure"], r["per_call_ms"], r["src"][:70])
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
