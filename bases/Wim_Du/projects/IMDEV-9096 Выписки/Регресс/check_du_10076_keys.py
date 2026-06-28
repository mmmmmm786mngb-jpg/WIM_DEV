#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check DU 10076 linkage by Ключ выписки in May regression XLSX."""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_1805_3105_diffs import (  # noqa: E402
    norm_amount,
    norm_date,
    norm_str,
    read_sheet,
    row_summary,
)

REG = Path(__file__).resolve().parent / "Регресс"
DT = "2026-05-28"
DOG = "10076"


def is_10076_vyp(row: dict) -> bool:
    return DOG in norm_str(row.get("Договор ДУ")) and norm_date(row.get("Дата создания")) == DT


def analyze_side(label: str, vpath: Path, ppath: Path) -> dict:
    vypiski = read_sheet(vpath)
    pp = read_sheet(ppath)
    vv = [r for r in vypiski if is_10076_vyp(r)]
    vkeys = {norm_str(r.get("Ключ выписки")) for r in vv}

    pp_day = [
        r
        for r in pp
        if norm_date(r.get("Дата")) == DT and norm_str(r.get("Операция")) == "Платежное поручение"
    ]
    pp_by_key = Counter(norm_str(r.get("Ключ выписки")) for r in pp_day)

    vyp_rows = []
    for r in vv:
        key = norm_str(r.get("Ключ выписки"))
        s = row_summary(r)
        linked = [x for x in pp_day if norm_str(x.get("Ключ выписки")) == key]
        vyp_rows.append(
            {
                "key": key,
                "zagruzhat": s["zagruzhat"],
                "zagruzhena": s["zagruzhena"],
                "pp_count_on_key": len(linked),
                "pp_list": [
                    {
                        "number": norm_str(x.get("Номер")),
                        "sum": norm_amount(x.get("Сумма")),
                        "loaded": norm_str(x.get("Загружен")),
                    }
                    for x in linked
                ],
            }
        )

    pp_on_vyp = [r for r in pp_day if norm_str(r.get("Ключ выпискi")) in vkeys if False]
    pp_on_vyp = [r for r in pp_day if norm_str(r.get("Ключ выписки")) in vkeys]

    return {
        "label": label,
        "vypiski_count": len(vv),
        "vypiski": vyp_rows,
        "pp_on_10076_vyp_keys": len(pp_on_vyp),
        "pp_on_vyp_details": [
            {
                "number": norm_str(r.get("Номер")),
                "sum": norm_amount(r.get("Сумма")),
                "loaded": norm_str(r.get("Загружен")),
                "key_vypiski": norm_str(r.get("Ключ выписки")),
            }
            for r in pp_on_vyp
        ],
    }


def main() -> int:
    bylo = analyze_side("BYLO", REG / "1805_3105_ВЫПИСКИ_было.xlsx", REG / "1805_3105_ПП_было.xlsx")
    stalo = analyze_side("STALO", REG / "1805_3105_ВЫПИСКИ_стало.xlsx", REG / "1805_3105_ПП_стало.xlsx")

    report = {"date": DT, "dogovor": f"ДУ {DOG} (Калашников А.М.)", "bylo": bylo, "stalo": stalo}
    out = REG / "du_10076_key_analysis.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for side in (bylo, stalo):
        print(f"=== {side['label']} ===")
        print(f"vypiski: {side['vypiski_count']}")
        for v in side["vypiski"]:
            print(f"  key={v['key'][:36]}... z={v['zagruzhat']}/{v['zagruzhena']} PP={v['pp_count_on_key']}")
            for p in v["pp_list"]:
                print(f"    PP {p['number']} sum={p['sum']} loaded={p['loaded']}")
        print(f"PP on 10076 keys total: {side['pp_on_10076_vyp_keys']}")
        print()
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
