#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep analysis for May 1805-3105 regression."""

import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REG_DIR = SCRIPT_DIR / "Регресс"
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows  # noqa: E402

WIDTH = 33
CORE = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")


def extract_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def parse_primary(vals: list[str]) -> list[dict]:
    start = next(index for index, value in enumerate(vals) if value == "N" and vals[index + 1] == "Операция")
    columns = vals[start : start + WIDTH]
    rows: list[dict] = []
    index = start + WIDTH
    while index + WIDTH <= len(vals):
        if vals[index].isdigit() and vals[index + 1] == "Платежное поручение":
            rows.append(dict(zip(columns, vals[index : index + WIDTH])))
            index += WIDTH
        else:
            index += 1
    return rows


def core_key(row: dict) -> tuple:
    return tuple(row.get(column, "").strip() for column in CORE)


def main() -> int:
    rows_bylo = parse_primary(extract_cells(REG_DIR / "1805_3105_ПП_было.mxl"))
    rows_stalo = parse_primary(extract_cells(REG_DIR / "1805_3105_ПП_стало.mxl"))

    cnt_bylo = Counter(core_key(row) for row in rows_bylo)
    cnt_stalo = Counter(core_key(row) for row in rows_stalo)

    print("=== PP LOOSER MATCHING ===")
    date_number_bylo = Counter((row.get("Дата", ""), row.get("Номер", "")) for row in rows_bylo)
    date_number_stalo = Counter((row.get("Дата", ""), row.get("Номер", "")) for row in rows_stalo)
    date_number_diff = (date_number_bylo - date_number_stalo) + (date_number_stalo - date_number_bylo)
    print(
        f"Date+Number: diff types={len(date_number_diff)} "
        f"only_bylo={sum((date_number_bylo - date_number_stalo).values())} "
        f"only_stalo={sum((date_number_stalo - date_number_bylo).values())}"
    )

    number_sum_bylo = Counter((row.get("Номер", ""), row.get("Сумма", "")) for row in rows_bylo)
    number_sum_stalo = Counter((row.get("Номер", ""), row.get("Сумма", "")) for row in rows_stalo)
    number_sum_diff = (number_sum_bylo - number_sum_stalo) + (number_sum_stalo - number_sum_bylo)
    print(
        f"Number+Sum: diff types={len(number_sum_diff)} "
        f"only_bylo={sum((number_sum_bylo - number_sum_stalo).values())} "
        f"only_stalo={sum((number_sum_stalo - number_sum_bylo).values())}"
    )
    print()

    only_bylo = list((cnt_bylo - cnt_stalo).elements())[:5]
    print("ONLY BYLO core samples vs STALO Date+Number lookup:")
    for key in only_bylo:
        date, number = key[0], key[1]
        matches = [row for row in rows_stalo if row.get("Дата") == date and row.get("Номер") == number]
        print(f"  {date} #{number}: same DN in stalo={len(matches)}")
        if matches:
            print(f"    stalo sum={matches[0].get('Сумма', '')}")
            print(f"    bylo назн={key[5][:90]}")
            print(f"    stalo назн={matches[0].get('Назначение платежа', '')[:90]}")
    print()

    rows_v_bylo = parse_rows(extract_cells(REG_DIR / "1805_3105_ВЫПИСКИ_было.mxl"))
    rows_v_stalo = parse_rows(extract_cells(REG_DIR / "1805_3105_ВЫПИСКИ_стало.mxl"))

    print("=== VYPISKI DU9957 / DU10076 ===")
    for label, rows in (("BYLO", rows_v_bylo), ("STALO", rows_v_stalo)):
        total_9957 = sum(1 for row in rows if "9957" in row.get("Dogovor", ""))
        cny_9957 = sum(
            1
            for row in rows
            if row.get("Data", "").startswith("18.05")
            and "CNY" in row.get("BankSchet", "")
            and "9957" in row.get("Dogovor", "")
        )
        total_10076 = sum(1 for row in rows if "10076" in row.get("Dogovor", ""))
        print(f"{label}: DU9957 total={total_9957}, 18.05 CNY={cny_9957}, DU10076 total={total_10076}")

    alt_key = lambda row: (row.get("Data", ""), row.get("BankSchet", ""), row.get("Dogovor", "") or "(empty)")
    cnt_v_bylo = Counter(alt_key(row) for row in rows_v_bylo)
    cnt_v_stalo = Counter(alt_key(row) for row in rows_v_stalo)
    print()
    print("VYPISKI key counts for diff types:")
    for key in sorted(set(cnt_v_bylo) | set(cnt_v_stalo)):
        delta = cnt_v_bylo[key] - cnt_v_stalo[key]
        if delta != 0:
            print(f"  delta={delta:+d} count_bylo={cnt_v_bylo[key]} count_stalo={cnt_v_stalo[key]} key={key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
