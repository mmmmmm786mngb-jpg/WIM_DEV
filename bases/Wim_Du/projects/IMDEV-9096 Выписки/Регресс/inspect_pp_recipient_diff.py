#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Show examples where Получатель differs but core payment fields match."""

import re
from pathlib import Path

REG = Path(__file__).resolve().parent
WIDTH = 33


def extract_hash_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def parse_primary_rows(vals: list[str]) -> tuple[list[str], list[dict]]:
    start = next(i for i, value in enumerate(vals) if value == "N" and vals[i + 1] == "Операция")
    columns = vals[start : start + WIDTH]
    rows: list[dict] = []
    index = start + WIDTH
    while index + WIDTH <= len(vals):
        if vals[index].isdigit() and vals[index + 1] == "Платежное поручение":
            rows.append(dict(zip(columns, vals[index : index + WIDTH])))
            index += WIDTH
        else:
            index += 1
    return columns, rows


def core_key(row: dict) -> tuple:
    cols = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")
    return tuple(row.get(c, "").strip() for c in cols)


def main() -> None:
    _, rows_bylo = parse_primary_rows(extract_hash_cells(REG / "0106__0506__ПП_Оригинал4.mxl"))
    _, rows_stalo = parse_primary_rows(extract_hash_cells(REG / "0106__0506__ПП_стало_после_испр4.mxl"))

    diff_recipient = 0
    diff_recipient_same_core = 0
    examples = []

    for row_bylo, row_stalo in zip(rows_bylo, rows_stalo):
        same_core = core_key(row_bylo) == core_key(row_stalo)
        rec_b = row_bylo.get("Получатель", "").strip()
        rec_s = row_stalo.get("Получатель", "").strip()
        if rec_b != rec_s:
            diff_recipient += 1
            if same_core:
                diff_recipient_same_core += 1
                if len(examples) < 5:
                    examples.append((row_bylo, row_stalo))

    print(f"Rows with different Получатель: {diff_recipient}")
    print(f"Of them, same core payment fields: {diff_recipient_same_core}")
    print()

    for index, (row_bylo, row_stalo) in enumerate(examples, 1):
        print(f"=== Example {index} ===")
        print(
            f"Core: {row_bylo.get('Дата')} | N={row_bylo.get('Номер')} | "
            f"Sum={row_bylo.get('Сумма')} | from={row_bylo.get('Плательщик счет')} | "
            f"to={row_bylo.get('Получатель счет')}"
        )
        for col in (
            "Получатель",
            "Получатель ИНН",
            "Получатель банк",
            "Плательщик",
            "Плательщик ИНН",
            "Статус составителя",
            "Документ ссылка2",
        ):
            print(f"  {col}:")
            print(f"    BYLO : {row_bylo.get(col, '')[:90]!r}")
            print(f"    STALO: {row_stalo.get(col, '')[:90]!r}")
        print()


if __name__ == "__main__":
    main()
