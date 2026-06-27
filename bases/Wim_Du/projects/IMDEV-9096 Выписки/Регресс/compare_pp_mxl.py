#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare PP (payment) MXL regression exports."""

import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

PATH_BYLO = SCRIPT_DIR / "0106__0506__ПП_Оригинал4.mxl"
PATH_STALO = SCRIPT_DIR / "0106__0506__ПП_стало_после_испр4.mxl"


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_hash_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def parse_pp_rows(vals: list[str]) -> tuple[list[str], list[dict]]:
    start = 0
    for index, value in enumerate(vals):
        if value == "N" and index + 1 < len(vals) and vals[index + 1] == "Операция":
            start = index
            break

    columns: list[str] = []
    index = start
    while index < len(vals) and vals[index] != "1":
        columns.append(vals[index])
        index += 1

    width = len(columns)
    rows: list[dict] = []
    while index + width <= len(vals):
        chunk = vals[index : index + width]
        if chunk[0].isdigit():
            rows.append(dict(zip(columns, chunk)))
            index += width
        else:
            index += 1

    return columns, rows


def row_tuple(row: dict, columns: list[str]) -> tuple:
    return tuple(row.get(column, "") for column in columns)


def compare_raw_cells(vals_bylo: list[str], vals_stalo: list[str]) -> None:
    print("=== Raw cells ===")
    for index, (left, right) in enumerate(zip(vals_bylo, vals_stalo)):
        if left != right:
            print(f"First raw diff at cell index: {index}")
            for offset in range(max(0, index - 2), min(len(vals_bylo), index + 6)):
                marker = ">>" if offset == index else "  "
                print(f"{marker} [{offset}] BYLO : {left[:90]!r}")
                print(f"   [{offset}] STALO: {right[:90]!r}")
            break
    else:
        if len(vals_bylo) == len(vals_stalo):
            print("All raw cells identical")
        else:
            print(f"Same prefix, length delta: {len(vals_bylo) - len(vals_stalo)}")

    cnt_bylo = Counter(vals_bylo)
    cnt_stalo = Counter(vals_stalo)
    diff = (cnt_bylo - cnt_stalo) + (cnt_stalo - cnt_bylo)
    print(f"Raw cell multiset diff sum: {sum(abs(value) for value in diff.values())}")
    print(f"Raw cell multiset diff types: {len(diff)}")
    if diff:
        print("Top raw cell multiset diffs:")
        for value, delta in diff.most_common(10):
            print(f"  delta={delta:+d} value={value[:90]!r}")
    print()


def compare_business_keys(rows_bylo: list[dict], rows_stalo: list[dict]) -> None:
    key_columns = (
        "Операция",
        "Дата",
        "Номер",
        "Сумма",
        "Плательщик счет",
        "Получатель счет",
        "Назначение платежа",
        "Ключ документа",
    )

    def business_key(row: dict) -> tuple:
        return tuple(row.get(column, "") for column in key_columns)

    cnt_bylo = Counter(business_key(row) for row in rows_bylo)
    cnt_stalo = Counter(business_key(row) for row in rows_stalo)
    diff = (cnt_bylo - cnt_stalo) + (cnt_stalo - cnt_bylo)

    print("=== Business key compare ===")
    print("Key:", ", ".join(key_columns))
    print(f"Rows: {len(rows_bylo)} / {len(rows_stalo)}")
    print(f"Business multiset diff sum: {sum(abs(value) for value in diff.values())}")
    print(f"Business diff types: {len(diff)}")
    print(f"Only in BYLO: {sum((cnt_bylo - cnt_stalo).values())}")
    print(f"Only in STALO: {sum((cnt_stalo - cnt_bylo).values())}")

    if diff:
        print("Top business diffs:")
        for key, delta in diff.most_common(10):
            print(f"  delta={delta:+d}")
            for column, value in zip(key_columns, key):
                if value:
                    print(f"    {column}: {value[:100]}")
            print()
    print()


def main() -> int:
    path_bylo = PATH_BYLO
    path_stalo = PATH_STALO
    if len(sys.argv) >= 3:
        path_bylo = Path(sys.argv[1])
        path_stalo = Path(sys.argv[2])

    vals_bylo = extract_hash_cells(path_bylo)
    vals_stalo = extract_hash_cells(path_stalo)

    print("=== PP MXL compare ===")
    print(f"BYLO:  {path_bylo.name}")
    print(f"STALO: {path_stalo.name}")
    print(f"Size bytes: {path_bylo.stat().st_size} / {path_stalo.stat().st_size}")
    print(f"MD5: {md5_file(path_bylo)} / {md5_file(path_stalo)}")
    print(f"Bytes identical: {md5_file(path_bylo) == md5_file(path_stalo)}")
    print(f"Cells extracted: {len(vals_bylo)} / {len(vals_stalo)}")
    print(f"Raw cells identical: {vals_bylo == vals_stalo}")
    print()

    compare_raw_cells(vals_bylo, vals_stalo)

    columns_bylo, rows_bylo = parse_pp_rows(vals_bylo)
    columns_stalo, rows_stalo = parse_pp_rows(vals_stalo)

    print(f"Columns: {len(columns_bylo)} / {len(columns_stalo)}")
    print(f"Rows parsed: {len(rows_bylo)} / {len(rows_stalo)}")
    if columns_bylo != columns_stalo:
        only_bylo = set(columns_bylo) - set(columns_stalo)
        only_stalo = set(columns_stalo) - set(columns_bylo)
        print(f"Column names differ. Only BYLO: {only_bylo}")
        print(f"Column names differ. Only STALO: {only_stalo}")
    print()

    compare_business_keys(rows_bylo, rows_stalo)

    columns = columns_bylo if columns_bylo == columns_stalo else columns_bylo
    cnt_bylo = Counter(row_tuple(row, columns) for row in rows_bylo)
    cnt_stalo = Counter(row_tuple(row, columns) for row in rows_stalo)
    diff = (cnt_bylo - cnt_stalo) + (cnt_stalo - cnt_bylo)

    print(f"Full-row multiset diff sum: {sum(abs(value) for value in diff.values())}")
    print(f"Diff row types: {len(diff)}")
    print(f"Only in BYLO rows: {sum((cnt_bylo - cnt_stalo).values())}")
    print(f"Only in STALO rows: {sum((cnt_stalo - cnt_bylo).values())}")
    print()

    positional = 0
    field_diff = Counter()
    for index, (row_bylo, row_stalo) in enumerate(zip(rows_bylo, rows_stalo)):
        if row_bylo != row_stalo:
            positional += 1
            for column in columns:
                if row_bylo.get(column) != row_stalo.get(column):
                    field_diff[column] += 1

    print(f"Positional diffs (same index): {positional} of {min(len(rows_bylo), len(rows_stalo))}")
    print(f"Row count delta: {len(rows_bylo) - len(rows_stalo)}")
    if field_diff:
        print("Fields changed (positional compare):")
        for column, count in field_diff.most_common(20):
            print(f"  {column}: {count}")
    print()

    if diff:
        print("--- Top multiset diffs ---")
        for key, delta in diff.most_common(15):
            print(f"delta={delta:+d}")
            for column, value in zip(columns, key):
                if value:
                    print(f"  {column}: {value[:100]}")
            print()

    # Business key without row number N
    business_columns = [column for column in columns if column != "N"]
    biz_bylo = Counter(row_tuple({k: row[k] for k in business_columns}, business_columns) for row in rows_bylo)
    biz_stalo = Counter(row_tuple({k: row[k] for k in business_columns}, business_columns) for row in rows_stalo)
    biz_diff = (biz_bylo - biz_stalo) + (biz_stalo - biz_bylo)
    print(f"Business multiset (without N) diff sum: {sum(abs(value) for value in biz_diff.values())}")
    print(f"Business diff row types: {len(biz_diff)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
