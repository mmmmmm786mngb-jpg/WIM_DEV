#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check DU 9957 linkage by Ключ выписки in May regression XLSX."""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_1805_3105_diffs import (  # noqa: E402
    norm_account,
    norm_amount,
    norm_date,
    norm_str,
    read_sheet,
    row_summary,
)

REG = Path(__file__).resolve().parent / "Регресс"
DT = "2026-05-18"
DOG = "9957"
PP_NUM = "483527"
CNY_ERS = "40701156603801000004"


def is_9957_vyp(row: dict) -> bool:
    return DOG in norm_str(row.get("Договор ДУ")) and norm_date(row.get("Дата создания")) == DT


def analyze_side(label: str, vpath: Path, ppath: Path) -> dict:
    vypiski = read_sheet(vpath)
    pp = read_sheet(ppath)
    vv = [r for r in vypiski if is_9957_vyp(r)]
    vkeys = {norm_str(r.get("Ключ выписки")) for r in vv}

    pp_day = [
        r
        for r in pp
        if norm_date(r.get("Дата")) == DT and norm_str(r.get("Операция")) == "Платежное поручение"
    ]
    pp_483527 = [r for r in pp_day if norm_str(r.get("Номер")) == PP_NUM]
    pp_on_vyp = [r for r in pp_day if norm_str(r.get("Ключ выписки")) in vkeys]
    pp_by_key = Counter(norm_str(r.get("Ключ выписки")) for r in pp_day)

    vyp_rows = []
    for r in vv:
        key = norm_str(r.get("Ключ выписки"))
        s = row_summary(r)
        vyp_rows.append(
            {
                "key": key,
                "bank": s["bank"],
                "account": s["account"],
                "zagruzhat": s["zagruzhat"],
                "zagruzhena": s["zagruzhena"],
                "pp_count_on_key": pp_by_key.get(key, 0),
            }
        )

    pp_rows = []
    for r in pp_483527:
        key = norm_str(r.get("Ключ выписки"))
        pp_rows.append(
            {
                "number": norm_str(r.get("Номер")),
                "sum": norm_amount(r.get("Сумма")),
                "loaded": norm_str(r.get("Загружен")),
                "key_vypiski": key,
                "key_doc": norm_str(r.get("Ключ документа")),
                "on_9957_vyp_key": key in vkeys,
            }
        )

    return {
        "label": label,
        "vypiski_count": len(vv),
        "vypiski": vyp_rows,
        "pp_483527_count": len(pp_483527),
        "pp_483527": pp_rows,
        "pp_on_9957_vyp_keys": len(pp_on_vyp),
        "pp_distribution": dict(Counter(norm_str(r.get("Ключ выписки")) for r in pp_on_vyp)),
    }


def main() -> int:
    bylo = analyze_side("BYLO", REG / "1805_3105_ВЫПИСКИ_было.xlsx", REG / "1805_3105_ПП_было.xlsx")
    stalo = analyze_side("STALO", REG / "1805_3105_ВЫПИСКИ_стало.xlsx", REG / "1805_3105_ПП_стало.xlsx")

    cross = {}
    if bylo["pp_483527"] and stalo["pp_483527"]:
        bk = bylo["pp_483527"][0]["key_vypiski"]
        sk = stalo["pp_483527"][0]["key_vypiski"]
        cross = {
            "pp_key_bylo": bk,
            "pp_key_stalo": sk,
            "same_key": bk == sk,
            "stalo_vyp_matching_pp": [
                v for v in stalo["vypiski"] if v["key"] == sk
            ],
            "stalo_vyp_not_matching_pp": [
                v for v in stalo["vypiski"] if v["key"] != sk
            ],
        }

    report = {"date": DT, "dogovor": f"ДУ {DOG} (Гольдфарб М.Н.)", "bylo": bylo, "stalo": stalo, "cross": cross}
    out = REG / "du_9957_key_analysis.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def safe_print(text: str) -> None:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode("ascii", errors="replace").decode("ascii"))

    safe_print("=== DU 9957 KEY ANALYSIS ===")
    for side in (bylo, stalo):
        safe_print(f"\n{side['label']}:")
        safe_print(f"  Vypiski rows: {side['vypiski_count']}")
        for v in side["vypiski"]:
            safe_print(f"    key={v['key'][:36]}... z={v['zagruzhat']}/{v['zagruzhena']} PP={v['pp_count_on_key']}")
        safe_print(f"  PP 483527: {side['pp_483527_count']}")
        for p in side["pp_483527"]:
            safe_print(f"    key={p['key_vypiski'][:36]}... loaded={p['loaded']} on_9957_vyp={p['on_9957_vyp_key']}")

    if cross:
        safe_print("\nCROSS:")
        safe_print(f"  PP key bylo:  {cross['pp_key_bylo']}")
        safe_print(f"  PP key stalo: {cross['pp_key_stalo']}")
        safe_print(f"  Same? {cross['same_key']}")
        safe_print(f"  Stalo vyp matching PP: {len(cross['stalo_vyp_matching_pp'])}")
        for v in cross["stalo_vyp_matching_pp"]:
            safe_print(f"    {v['key'][:36]}... z={v['zagruzhat']}/{v['zagruzhena']} PP={v['pp_count_on_key']}")
        safe_print(f"  Stalo vyp WITHOUT PP (extra row): {len(cross['stalo_vyp_not_matching_pp'])}")
        for v in cross["stalo_vyp_not_matching_pp"]:
            safe_print(f"    {v['key'][:36]}... z={v['zagruzhat']}/{v['zagruzhena']} PP={v['pp_count_on_key']}")

    safe_print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
