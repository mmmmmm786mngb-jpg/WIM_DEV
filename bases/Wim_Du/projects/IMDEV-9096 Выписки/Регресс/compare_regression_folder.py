#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare regression exports in a folder (Vypiski, PP, optional error logs)."""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows, row_signature  # noqa: E402

WIDTH = 33
ACCOUNT_RE = re.compile(r"Для счета: (\d+) не определен")
CORE_PP = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")
BUSINESS_PP = CORE_PP + (
    "Плательщик ИНН",
    "Плательщик",
    "Получатель ИНН",
    "Получатель",
    "Вид оплаты",
    "Статус составителя",
    "Загружен",
    "Лог",
)


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
            return [line.strip() for line in raw.decode(encoding).splitlines() if line.strip()]
        except UnicodeDecodeError:
            continue
    return [line.strip() for line in raw.decode("cp1251", errors="replace").splitlines() if line.strip()]


def parse_primary_pp(vals: list[str]) -> list[dict]:
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


def count_all_tch_rows(vals: list[str]) -> int:
    start = next(index for index, value in enumerate(vals) if value == "N" and vals[index + 1] == "Операция")
    count = 0
    index = start + WIDTH
    while index + WIDTH <= len(vals):
        if vals[index].isdigit():
            count += 1
            index += WIDTH
        else:
            index += 1
    return count


def compare_vypiski(path_bylo: Path, path_stalo: Path) -> dict:
    rows_bylo = parse_rows(extract_hash_cells(path_bylo))
    rows_stalo = parse_rows(extract_hash_cells(path_stalo))

    cnt_bylo = Counter(row_signature(row) for row in rows_bylo)
    cnt_stalo = Counter(row_signature(row) for row in rows_stalo)
    diff = (cnt_bylo - cnt_stalo) + (cnt_stalo - cnt_bylo)

    alt_key = lambda row: (row.get("Data", ""), row.get("BankSchet", ""), row.get("Dogovor", "") or "(empty)")
    alt_bylo = Counter(alt_key(row) for row in rows_bylo)
    alt_stalo = Counter(alt_key(row) for row in rows_stalo)
    alt_diff = (alt_bylo - alt_stalo) + (alt_stalo - alt_bylo)

    positional = sum(
        1
        for left, right in zip(rows_bylo, rows_stalo)
        if row_signature(left) != row_signature(right)
    )

    return {
        "rows": (len(rows_bylo), len(rows_stalo)),
        "row_count_delta": len(rows_bylo) - len(rows_stalo),
        "md5_identical": md5_file(path_bylo) == md5_file(path_stalo),
        "multiset_identical": len(diff) == 0,
        "multiset_diff_types": len(diff),
        "multiset_only_bylo": sum((cnt_bylo - cnt_stalo).values()),
        "multiset_only_stalo": sum((cnt_stalo - cnt_bylo).values()),
        "alt_key_diff_types": len(alt_diff),
        "alt_key_diffs": [
            {
                "delta": cnt_bylo[key] - cnt_stalo[key],
                "count_bylo": cnt_bylo[key],
                "count_stalo": cnt_stalo[key],
                "key": key,
            }
            for key in sorted(set(alt_bylo) | set(alt_stalo))
            if alt_bylo[key] != alt_stalo[key]
        ],
        "positional_diffs": positional,
        "top_multiset_diffs": [
            {
                "delta": delta,
                "data": key[0],
                "schet": key[1],
                "dogovor": key[2][:80],
                "bank": key[3],
                "n": key[4],
            }
            for key, delta in sorted(diff.items(), key=lambda item: -abs(item[1]))[:15]
        ],
    }


def compare_pp(path_bylo: Path, path_stalo: Path) -> dict:
    vals_bylo = extract_hash_cells(path_bylo)
    vals_stalo = extract_hash_cells(path_stalo)
    rows_bylo = parse_primary_pp(vals_bylo)
    rows_stalo = parse_primary_pp(vals_stalo)

    def core_key(row: dict) -> tuple:
        return tuple(row.get(column, "").strip() for column in CORE_PP)

    def business_key(row: dict) -> tuple:
        return tuple(row.get(column, "").strip() for column in BUSINESS_PP)

    cnt_core_bylo = Counter(core_key(row) for row in rows_bylo)
    cnt_core_stalo = Counter(core_key(row) for row in rows_stalo)
    core_diff = (cnt_core_bylo - cnt_core_stalo) + (cnt_core_stalo - cnt_core_bylo)

    cnt_business_bylo = Counter(business_key(row) for row in rows_bylo)
    cnt_business_stalo = Counter(business_key(row) for row in rows_stalo)
    business_diff = (cnt_business_bylo - cnt_business_stalo) + (cnt_business_stalo - cnt_business_bylo)

    loaded_diff = 0
    for key in cnt_core_bylo & cnt_core_stalo:
        left = Counter(
            (row.get("Загружен", ""), row.get("Лог", ""))
            for row in rows_bylo
            if core_key(row) == key
        )
        right = Counter(
            (row.get("Загружен", ""), row.get("Лог", ""))
            for row in rows_stalo
            if core_key(row) == key
        )
        if left != right:
            loaded_diff += 1

    return {
        "all_tch_rows": (count_all_tch_rows(vals_bylo), count_all_tch_rows(vals_stalo)),
        "primary_pp_rows": (len(rows_bylo), len(rows_stalo)),
        "row_count_delta": len(rows_bylo) - len(rows_stalo),
        "md5_identical": md5_file(path_bylo) == md5_file(path_stalo),
        "core_multiset_identical": len(core_diff) == 0,
        "core_multiset_diff_types": len(core_diff),
        "core_only_bylo": sum((cnt_core_bylo - cnt_core_stalo).values()),
        "core_only_stalo": sum((cnt_core_stalo - cnt_core_bylo).values()),
        "core_shared_keys": len(cnt_core_bylo & cnt_core_stalo),
        "shared_keys_loaded_log_diff": loaded_diff,
        "business_multiset_identical": len(business_diff) == 0,
        "business_multiset_diff_types": len(business_diff),
        "business_only_bylo": sum((cnt_business_bylo - cnt_business_stalo).values()),
        "business_only_stalo": sum((cnt_business_stalo - cnt_business_bylo).values()),
        "top_core_diffs": [
            {"delta": delta, "keys": dict(zip(CORE_PP, key))}
            for key, delta in core_diff.most_common(8)
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

    return {
        "lines": (len(lines_bylo), len(lines_stalo)),
        "messages_multiset_identical": not only_bylo and not only_stalo,
        "only_bylo_count": sum(only_bylo.values()),
        "only_stalo_count": sum(only_stalo.values()),
        "accounts_identical": acc_bylo == acc_stalo,
    }


def find_pair(folder: Path, suffix: str) -> tuple[Path, Path] | None:
    bylo = sorted(folder.glob(f"*{suffix}*было*"))
    stalo = sorted(folder.glob(f"*{suffix}*стало*"))
    if not bylo or not stalo:
        return None
    return bylo[0], stalo[0]


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", nargs="?", default="Регресс2105")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_absolute():
        folder = SCRIPT_DIR / folder

    label = args.label or folder.name
    report: dict = {"folder": str(folder), "label": label}

    vypiski_pair = find_pair(folder, "ВЫПИСКИ") or find_pair(folder, "Выписки")
    pp_pair = find_pair(folder, "ПП")
    errors_bylo = sorted(folder.glob("*было*.txt"))
    errors_stalo = sorted(folder.glob("*стало*.txt"))

    if vypiski_pair:
        report["vypiski"] = compare_vypiski(*vypiski_pair)
        report["vypiski"]["files"] = tuple(path.name for path in vypiski_pair)

    if pp_pair:
        report["pp"] = compare_pp(*pp_pair)
        report["pp"]["files"] = tuple(path.name for path in pp_pair)

    if errors_bylo and errors_stalo:
        report["errors"] = compare_errors(errors_bylo[0], errors_stalo[0])
        report["errors"]["files"] = (errors_bylo[0].name, errors_stalo[0].name)
    else:
        report["errors"] = {"present": False}

    out_path = folder / f"{label}_compare_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    safe_print(f"=== REGRESSION {label} ===")
    safe_print("")

    if "vypiski" in report:
        v = report["vypiski"]
        safe_print("1. VYPISKI")
        safe_print(f"   Files: {v['files'][0]} / {v['files'][1]}")
        safe_print(f"   Rows: {v['rows'][0]} / {v['rows'][1]} (delta {v['row_count_delta']})")
        safe_print(f"   MD5 identical: {v['md5_identical']}")
        safe_print(f"   Multiset (Data,Schet,Dogovor,Bank,N) identical: {v['multiset_identical']}")
        safe_print(
            f"   Alt multiset (Data,Bank,Dogovor) diff types: {v['alt_key_diff_types']} "
            f"only_bylo={v['multiset_only_bylo']} only_stalo={v['multiset_only_stalo']}"
        )
        safe_print(f"   Positional diffs: {v['positional_diffs']}")
        for item in v.get("alt_key_diffs", [])[:10]:
            safe_print(f"     delta={item['delta']:+d} bylo={item['count_bylo']} stalo={item['count_stalo']} key={item['key']}")
        safe_print("")

    if "pp" in report:
        p = report["pp"]
        safe_print("2. PP")
        safe_print(f"   Files: {p['files'][0]} / {p['files'][1]}")
        safe_print(f"   All TCH rows: {p['all_tch_rows'][0]} / {p['all_tch_rows'][1]}")
        safe_print(f"   Primary PP rows: {p['primary_pp_rows'][0]} / {p['primary_pp_rows'][1]} (delta {p['row_count_delta']})")
        safe_print(f"   MD5 identical: {p['md5_identical']}")
        safe_print(f"   Core multiset identical: {p['core_multiset_identical']}")
        safe_print(
            f"   Core shared keys: {p['core_shared_keys']} | only BYLO: {p['core_only_bylo']} | only STALO: {p['core_only_stalo']}"
        )
        safe_print(f"   Shared keys with different Zагружен/Log: {p['shared_keys_loaded_log_diff']}")
        safe_print(f"   Business multiset identical: {p['business_multiset_identical']}")
        safe_print("")

    e = report["errors"]
    safe_print("3. ERRORS")
    if not e.get("present", True):
        safe_print("   Files not found in folder")
    else:
        safe_print(f"   Files: {e['files'][0]} / {e['files'][1]}")
        safe_print(f"   Lines: {e['lines'][0]} / {e['lines'][1]}")
        safe_print(f"   Messages multiset identical: {e['messages_multiset_identical']}")
        safe_print(f"   Account warnings identical: {e['accounts_identical']}")

    safe_print("")
    safe_print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
