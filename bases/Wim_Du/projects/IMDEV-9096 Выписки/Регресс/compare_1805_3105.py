#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare May regression exports (1805-3105): Vypiski, PP, error logs."""

import json
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REG_DIR = SCRIPT_DIR / "Регресс"

sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows, row_signature  # noqa: E402
from compare_pp_mxl import parse_pp_rows, row_tuple  # noqa: E402

ACCOUNT_RE = re.compile(r"Для счета: (\d+) не определен")


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp1251"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            text = raw.decode("cp1251", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def compare_vypiski(path_bylo: Path, path_stalo: Path) -> dict:
    vals_bylo = extract_hash_cells(path_bylo)
    vals_stalo = extract_hash_cells(path_stalo)
    rows_bylo = parse_rows(vals_bylo)
    rows_stalo = parse_rows(vals_stalo)

    cnt_bylo = Counter(row_signature(row) for row in rows_bylo)
    cnt_stalo = Counter(row_signature(row) for row in rows_stalo)
    diff = (cnt_bylo - cnt_stalo) + (cnt_stalo - cnt_bylo)

    positional = sum(
        1
        for left, right in zip(rows_bylo, rows_stalo)
        if row_signature(left) != row_signature(right)
    )

    return {
        "files": (path_bylo.name, path_stalo.name),
        "size_bytes": (path_bylo.stat().st_size, path_stalo.stat().st_size),
        "rows": (len(rows_bylo), len(rows_stalo)),
        "md5_identical": md5_file(path_bylo) == md5_file(path_stalo),
        "multiset_diff_types": len(diff),
        "multiset_only_bylo": sum((cnt_bylo - cnt_stalo).values()),
        "multiset_only_stalo": sum((cnt_stalo - cnt_bylo).values()),
        "multiset_identical": len(diff) == 0,
        "positional_diffs": positional,
        "row_count_delta": len(rows_bylo) - len(rows_stalo),
        "top_diffs": [
            {
                "delta": delta,
                "data": key[0],
                "schet": key[1],
                "dogovor": key[2][:80],
                "bank": key[3],
                "n": key[4],
            }
            for key, delta in sorted(diff.items(), key=lambda item: -abs(item[1]))[:20]
        ],
    }


def compare_pp(path_bylo: Path, path_stalo: Path) -> dict:
    vals_bylo = extract_hash_cells(path_bylo)
    vals_stalo = extract_hash_cells(path_stalo)
    columns_bylo, rows_bylo = parse_pp_rows(vals_bylo)
    columns_stalo, rows_stalo = parse_pp_rows(vals_stalo)

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

    full_bylo = Counter(row_tuple(row, columns_bylo) for row in rows_bylo)
    full_stalo = Counter(row_tuple(row, columns_stalo) for row in rows_stalo)
    full_diff = (full_bylo - full_stalo) + (full_stalo - full_bylo)

    field_diff = Counter()
    positional = 0
    for row_bylo, row_stalo in zip(rows_bylo, rows_stalo):
        if row_bylo != row_stalo:
            positional += 1
            for column in columns_bylo:
                if row_bylo.get(column) != row_stalo.get(column):
                    field_diff[column] += 1

    return {
        "files": (path_bylo.name, path_stalo.name),
        "size_bytes": (path_bylo.stat().st_size, path_stalo.stat().st_size),
        "rows": (len(rows_bylo), len(rows_stalo)),
        "columns": (len(columns_bylo), len(columns_stalo)),
        "columns_identical": columns_bylo == columns_stalo,
        "md5_identical": md5_file(path_bylo) == md5_file(path_stalo),
        "raw_cells_identical": vals_bylo == vals_stalo,
        "business_multiset_identical": len(diff) == 0,
        "business_multiset_diff_types": len(diff),
        "business_only_bylo": sum((cnt_bylo - cnt_stalo).values()),
        "business_only_stalo": sum((cnt_stalo - cnt_bylo).values()),
        "full_row_multiset_identical": len(full_diff) == 0,
        "full_row_diff_types": len(full_diff),
        "positional_diffs": positional,
        "row_count_delta": len(rows_bylo) - len(rows_stalo),
        "field_diffs_positional": dict(field_diff.most_common(20)),
        "top_business_diffs": [
            {"delta": delta, "keys": dict(zip(key_columns, key))}
            for key, delta in diff.most_common(10)
        ],
    }


def compare_errors(path_bylo: Path, path_stalo: Path) -> dict:
    lines_bylo = load_lines(path_bylo)
    lines_stalo = load_lines(path_stalo)

    def classify(line: str) -> str:
        if line.startswith("Продолжительность"):
            return "__duration__"
        return line

    cnt_bylo = Counter(classify(line) for line in lines_bylo)
    cnt_stalo = Counter(classify(line) for line in lines_stalo)
    only_bylo = cnt_bylo - cnt_stalo
    only_stalo = cnt_stalo - cnt_bylo

    def account_counts(lines: list[str]) -> Counter:
        result = Counter()
        for line in lines:
            match = ACCOUNT_RE.search(line)
            if match:
                result[match.group(1)] += 1
        return result

    acc_bylo = account_counts(lines_bylo)
    acc_stalo = account_counts(lines_stalo)
    all_accounts = sorted(set(acc_bylo) | set(acc_stalo))
    accounts_diff = {
        account: {"bylo": acc_bylo[account], "stalo": acc_stalo[account]}
        for account in all_accounts
        if acc_bylo[account] != acc_stalo[account]
    }

    duration_bylo = next((key for key in cnt_bylo if key.startswith("Продолжительность")), "")
    duration_stalo = next((key for key in cnt_stalo if key.startswith("Продолжительность")), "")

    return {
        "files": (path_bylo.name, path_stalo.name),
        "lines": (len(lines_bylo), len(lines_stalo)),
        "unique_types": (len(cnt_bylo), len(cnt_stalo)),
        "duration_bylo": duration_bylo,
        "duration_stalo": duration_stalo,
        "messages_multiset_identical": not only_bylo and not only_stalo,
        "only_bylo_count": sum(only_bylo.values()),
        "only_stalo_count": sum(only_stalo.values()),
        "only_bylo_samples": [
            f"x{count} {message[:120]}"
            for message, count in only_bylo.most_common(10)
            if message != "__duration__"
        ],
        "only_stalo_samples": [
            f"x{count} {message[:120]}"
            for message, count in only_stalo.most_common(10)
            if not message.startswith("Продолжительность")
        ],
        "accounts_identical": acc_bylo == acc_stalo,
        "accounts_diff": accounts_diff,
    }


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def main() -> int:
    report = {
        "period": "1805-3105 (May regression)",
        "vypiski": compare_vypiski(
            REG_DIR / "1805_3105_ВЫПИСКИ_было.mxl",
            REG_DIR / "1805_3105_ВЫПИСКИ_стало.mxl",
        ),
        "pp": compare_pp(
            REG_DIR / "1805_3105_ПП_было.mxl",
            REG_DIR / "1805_3105_ПП_стало.mxl",
        ),
        "errors": compare_errors(
            REG_DIR / "Ошибки_1805_3105_было.txt",
            REG_DIR / "Ошибки_1805_3105_стало.txt",
        ),
    }

    out_path = REG_DIR / "1805_3105_compare_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    safe_print("=== MAY REGRESSION 1805-3105 ===")
    safe_print("")

    safe_print("1. VYPISKI MXL")
    vypiski = report["vypiski"]
    safe_print(
        f"   Rows: {vypiski['rows'][0]} / {vypiski['rows'][1]} "
        f"(delta {vypiski['row_count_delta']})"
    )
    safe_print(f"   MD5 identical: {vypiski['md5_identical']}")
    safe_print(f"   Multiset identical: {vypiski['multiset_identical']}")
    safe_print(
        f"   Multiset diff types: {vypiski['multiset_diff_types']} "
        f"only_bylo={vypiski['multiset_only_bylo']} "
        f"only_stalo={vypiski['multiset_only_stalo']}"
    )
    safe_print(f"   Positional diffs: {vypiski['positional_diffs']}")
    for item in vypiski["top_diffs"][:10]:
        safe_print(
            f"     delta={item['delta']:+d} | {item['data']} | {item['schet']} | "
            f"{item['dogovor']} | N={item['n']}"
        )
    safe_print("")

    safe_print("2. PP MXL")
    pp = report["pp"]
    safe_print(f"   Rows: {pp['rows'][0]} / {pp['rows'][1]} (delta {pp['row_count_delta']})")
    safe_print(f"   MD5 identical: {pp['md5_identical']}")
    safe_print(f"   Raw cells identical: {pp['raw_cells_identical']}")
    safe_print(f"   Business multiset identical: {pp['business_multiset_identical']}")
    safe_print(f"   Full row multiset identical: {pp['full_row_multiset_identical']}")
    safe_print(
        f"   Business diff types: {pp['business_multiset_diff_types']} "
        f"only_bylo={pp['business_only_bylo']} only_stalo={pp['business_only_stalo']}"
    )
    safe_print(f"   Positional diffs: {pp['positional_diffs']}")
    if pp["field_diffs_positional"]:
        safe_print(f"   Fields changed (positional): {pp['field_diffs_positional']}")
    safe_print("")

    safe_print("3. ERROR LOGS")
    errors = report["errors"]
    safe_print(f"   Lines: {errors['lines'][0]} / {errors['lines'][1]}")
    safe_print(f"   Unique message types: {errors['unique_types'][0]} / {errors['unique_types'][1]}")
    safe_print(f"   Duration BYLO: {errors['duration_bylo']}")
    safe_print(f"   Duration STALO: {errors['duration_stalo']}")
    safe_print(f"   Messages multiset identical: {errors['messages_multiset_identical']}")
    safe_print(
        f"   Only BYLO lines: {errors['only_bylo_count']} | "
        f"Only STALO lines: {errors['only_stalo_count']}"
    )
    safe_print(f"   Account warnings identical: {errors['accounts_identical']}")
    if errors["accounts_diff"]:
        safe_print(f"   Account count diffs: {errors['accounts_diff']}")
    for sample in errors["only_bylo_samples"]:
        safe_print(f"   ONLY BYLO: {sample}")
    for sample in errors["only_stalo_samples"]:
        safe_print(f"   ONLY STALO: {sample}")
    safe_print("")
    safe_print(f"Saved: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
