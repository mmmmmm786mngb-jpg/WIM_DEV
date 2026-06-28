#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Link PP diffs to Vypiski dogovor blocks for Regress2105."""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REG = SCRIPT_DIR / "Регресс2105"
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows  # noqa: E402

WIDTH = 33
CORE = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")


def parse_primary_pp(vals: list[str]) -> list[dict]:
    start = next(i for i, v in enumerate(vals) if v == "N" and vals[i + 1] == "Операция")
    cols = vals[start : start + WIDTH]
    rows = []
    i = start + WIDTH
    while i + WIDTH <= len(vals):
        if vals[i].isdigit() and vals[i + 1] == "Платежное поручение":
            rows.append(dict(zip(cols, vals[i : i + WIDTH])))
            i += WIDTH
        else:
            i += 1
    return cols, rows


def core_key(row: dict) -> tuple:
    return tuple(row.get(c, "").strip() for c in CORE)


def main() -> None:
    _, rows_pp_bylo = parse_primary_pp(extract_cells(REG / "2105_2105_ПП_было.mxl"))
    cols, rows_pp_stalo = parse_primary_pp(extract_cells(REG / "2105_2105_ПП_стало.mxl"))

    cnt_b = Counter(core_key(r) for r in rows_pp_bylo)
    cnt_s = Counter(core_key(r) for r in rows_pp_stalo)
    only_b = set((cnt_b - cnt_s).elements())
    only_s = set((cnt_s - cnt_b).elements())

    # PP link field
    link_col = "Ключ выписки"
    print("PP link column present:", link_col in cols)
    print()

    def by_link(rows, keys):
        result = defaultdict(list)
        for row in rows:
            if core_key(row) in keys:
                result[row.get(link_col, "(empty)")].append(row)
        return result

    b_links = by_link(rows_pp_bylo, only_b)
    s_links = by_link(rows_pp_stalo, only_s)

    print("ONLY BYLO payments grouped by Klyuch vypiski (top 10):")
    for link, items in sorted(b_links.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  link={link!r}: {len(items)} payments, sample #{items[0].get('Номер')} sum={items[0].get('Сумма')}")
    print()
    print("ONLY STALO payments grouped by Klyuch vypiski (top 10):")
    for link, items in sorted(s_links.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  link={link!r}: {len(items)} payments, sample #{items[0].get('Номер')} sum={items[0].get('Сумма')}")
    print()

    # Vypiski rows 21.05 ERS
    rows_v_b = parse_rows(extract_cells(REG / "2105_2105_ВЫПИСКИ_было.mxl"))
    rows_v_s = parse_rows(extract_cells(REG / "2105_2105_ВЫПИСКИ_стало.mxl"))

    def vypiski_ers(date_prefix="21.05"):
        for label, rows in ("BYLO", rows_v_b), ("STALO", rows_v_s):
            block = [
                r
                for r in rows
                if r.get("Data", "").startswith(date_prefix)
                and "RUR_ЕРС" in r.get("BankSchet", "")
            ]
            contracts = Counter(r.get("Dogovor", "") or "(empty)" for r in block)
            print(f"{label} ERS RUR {date_prefix}: {len(block)} rows")
            for dog, cnt in contracts.most_common(15):
                print(f"  {cnt:4d} x {dog[:55]}")
            print()

    vypiski_ers()

    # Search PP назначение for DU numbers from ERS contracts
    ers_dogs = ["8959", "8668", "8209", "8204", "10061", "10076", "9957"]
    print("ONLY BYLO PP mentioning ERS DU numbers in Naznachenie:")
    for num in ers_dogs:
        n = sum(1 for k in only_b if num in k[5])
        if n:
            print(f"  DU {num}: {n} payments")
    print()
    print("Sample ONLY BYLO with dogovor hint in text:")
    for row in rows_pp_bylo:
        k = core_key(row)
        if k not in only_b:
            continue
        text = row.get("Назначение платежа", "")
        if any(d in text for d in ("8959", "8668", "8209", "8204", "10061", "SUBSCET", "DU ", "ДУ ")):
            print(f"  #{row.get('Номер')} sum={row.get('Сумма')} link={row.get(link_col)!r}")
            print(f"    {text[:120]}")
            break
    else:
        row = next(r for r in rows_pp_bylo if core_key(r) in only_b)
        print(f"  #{row.get('Номер')} sum={row.get('Summa') or row.get('Сумма')} link={row.get(link_col)!r}")
        print(f"    {row.get('Назначение платежа','')[:120]}")

    # Compare PP count per Klyuch vypiski for shared keys
    all_links = sorted(set(r.get(link_col, "") for r in rows_pp_bylo) | set(r.get(link_col, "") for r in rows_pp_stalo))
    print()
    print("PP count delta by Klyuch vypiski (where differs):")
    shown = 0
    for link in all_links:
        cb = sum(1 for r in rows_pp_bylo if r.get(link_col) == link)
        cs = sum(1 for r in rows_pp_stalo if r.get(link_col) == link)
        if cb != cs:
            ob = sum(1 for r in rows_pp_bylo if r.get(link_col) == link and core_key(r) in only_b)
            os = sum(1 for r in rows_pp_stalo if r.get(link_col) == link and core_key(r) in only_s)
            print(f"  link={link!r}: BYLO={cb} STALO={cs} (only_b={ob} only_s={os})")
            shown += 1
            if shown >= 15:
                break


def extract_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


if __name__ == "__main__":
    main()
