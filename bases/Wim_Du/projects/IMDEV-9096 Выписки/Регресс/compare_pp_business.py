#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare PP MXL by primary payment rows (ignore UUID noise)."""

import hashlib
import re
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent
PATH_BYLO = REG / "0106__0506__ПП_Оригинал4.mxl"
PATH_STALO = REG / "0106__0506__ПП_стало_после_испр4.mxl"

WIDTH = 33
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)

BUSINESS_COLUMNS = (
    "Операция",
    "Дата",
    "Номер",
    "Сумма",
    "Дата поступления",
    "Плательщик счет",
    "Получатель счет",
    "Назначение платежа",
    "Плательщик ИНН",
    "Плательщик",
    "Получатель ИНН",
    "Получатель",
    "Вид оплаты",
    "Статус составителя",
    "Загружен",
    "Лог",
)

IGNORE_COLUMNS = (
    "N",
    "Плательщик1",
    "Получатель1",
    "Плательщик банк",
    "Получатель банк",
    "Показатель КБК",
    "ОКАТО",
    "Ключ выписки",
    "Плательщик БИК",
    "Получатель БИК",
    "Дата списано",
    "Дата поступило",
    "Ключ документа",
    "Документ",
    "Направление",
    "Документ ссылка1",
    "Документ ссылка2",
)


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
            chunk = vals[index : index + WIDTH]
            rows.append(dict(zip(columns, chunk)))
            index += WIDTH
        else:
            index += 1

    return columns, rows


def business_key(row: dict) -> tuple:
    return tuple(row.get(column, "").strip() for column in BUSINESS_COLUMNS)


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


CORE_COLUMNS = (
    "Дата",
    "Номер",
    "Сумма",
    "Плательщик счет",
    "Получатель счет",
    "Назначение платежа",
)


def core_key(row: dict) -> tuple:
    return tuple(row.get(column, "").strip() for column in CORE_COLUMNS)


def main() -> None:
    vals_bylo = extract_hash_cells(PATH_BYLO)
    vals_stalo = extract_hash_cells(PATH_STALO)

    print("=== PP payment data compare ===")
    print(f"File size: {PATH_BYLO.stat().st_size} / {PATH_STALO.stat().st_size}")
    print(f"MD5: {md5_file(PATH_BYLO)} / {md5_file(PATH_STALO)}")
    print(f"Bytes identical: {md5_file(PATH_BYLO) == md5_file(PATH_STALO)}")
    print(f"Raw cells: {len(vals_bylo)} / {len(vals_stalo)}")
    print()

    _, rows_bylo = parse_primary_rows(vals_bylo)
    _, rows_stalo = parse_primary_rows(vals_stalo)

    print(f"Primary payment rows parsed: {len(rows_bylo)} / {len(rows_stalo)}")
    print()

    cnt_bylo = Counter(business_key(row) for row in rows_bylo)
    cnt_stalo = Counter(business_key(row) for row in rows_stalo)
    diff = (cnt_bylo - cnt_stalo) + (cnt_stalo - cnt_bylo)

    print("Business columns compared:")
    for column in BUSINESS_COLUMNS:
        print(f"  - {column}")
    print()
    print(f"Business multiset diff sum: {sum(abs(value) for value in diff.values())}")
    print(f"Business diff payment types: {len(diff)}")
    print(f"Only in BYLO payments: {sum((cnt_bylo - cnt_stalo).values())}")
    print(f"Only in STALO payments: {sum((cnt_stalo - cnt_bylo).values())}")
    print(f"Business multiset identical: {not diff}")
    print()

    cnt_core_bylo = Counter(core_key(row) for row in rows_bylo)
    cnt_core_stalo = Counter(core_key(row) for row in rows_stalo)
    core_diff = (cnt_core_bylo - cnt_core_stalo) + (cnt_core_stalo - cnt_core_bylo)
    print("=== Core payment fields only ===")
    for column in CORE_COLUMNS:
        print(f"  - {column}")
    print(f"Core multiset diff sum: {sum(abs(value) for value in core_diff.values())}")
    print(f"Core diff payment types: {len(core_diff)}")
    print(f"Only in BYLO: {sum((cnt_core_bylo - cnt_core_stalo).values())}")
    print(f"Only in STALO: {sum((cnt_core_stalo - cnt_core_bylo).values())}")
    print(f"Core multiset identical: {not core_diff}")
    core_pos = sum(
        1
        for row_bylo, row_stalo in zip(rows_bylo, rows_stalo)
        if core_key(row_bylo) != core_key(row_stalo)
    )
    print(f"Positional core diffs: {core_pos} of {min(len(rows_bylo), len(rows_stalo))}")
    print()

    positional = 0
    field_diff = Counter()
    for row_bylo, row_stalo in zip(rows_bylo, rows_stalo):
        if business_key(row_bylo) != business_key(row_stalo):
            positional += 1
            for column in BUSINESS_COLUMNS:
                if row_bylo.get(column, "").strip() != row_stalo.get(column, "").strip():
                    field_diff[column] += 1

    print(
        f"Positional business diffs: {positional} of {min(len(rows_bylo), len(rows_stalo))}"
    )
    if field_diff:
        print("Changed business fields:")
        for column, count in field_diff.most_common():
            print(f"  {column}: {count}")
    print()

    if core_diff:
        print("--- Sample core diffs ---")
        for key, delta in core_diff.most_common(10):
            print(f"delta={delta:+d}")
            for column, value in zip(CORE_COLUMNS, key):
                if value:
                    print(f"  {column}: {value[:100]}")
            print()

    if diff:
        print("--- Sample business diffs ---")
        for key, delta in diff.most_common(10):
            print(f"delta={delta:+d}")
            for column, value in zip(BUSINESS_COLUMNS, key):
                if value:
                    print(f"  {column}: {value[:100]}")
            print()

    # Non-UUID column diffs on aligned primary rows
    all_columns = list(parse_primary_rows(vals_bylo)[0])
    compare_columns = [c for c in all_columns if c not in IGNORE_COLUMNS]
    non_uuid_diff = Counter()
    for row_bylo, row_stalo in zip(rows_bylo, rows_stalo):
        for column in compare_columns:
            left = row_bylo.get(column, "").strip()
            right = row_stalo.get(column, "").strip()
            if left != right:
                non_uuid_diff[column] += 1

    print("Non-ignored column diffs on aligned primary rows:")
    if non_uuid_diff:
        for column, count in non_uuid_diff.most_common():
            print(f"  {column}: {count}")
    else:
        print("  none")


if __name__ == "__main__":
    main()
