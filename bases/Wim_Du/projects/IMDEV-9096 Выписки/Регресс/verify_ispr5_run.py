#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify ispr5 regression: MXL data + error log vs original."""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent
sys.path.insert(0, str(REG))

from compare_mxl import extract_hash_cells, parse_rows, row_signature
from compare_pp_business import parse_primary_rows, core_key

DOG_RE = re.compile(r"Для счета: (\d+) не определен ДоговорДУ")


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp866"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Cannot decode {path}")


def parse_errors(path: Path) -> dict:
    lines = [
        line.strip()
        for line in read_text(path).splitlines()
        if line.strip() and not line.startswith("Продолжительность")
    ]
    dog = Counter()
    bik = 0
    duration = ""
    for line in read_text(path).splitlines():
        if line.strip().startswith("Продолжительность"):
            duration = line.strip()
    for line in lines:
        match = DOG_RE.search(line)
        if match:
            dog[match.group(1)] += 1
        elif "БИК" in line:
            bik += 1
    return {
        "file": path.name,
        "lines": len(lines),
        "duration": duration,
        "bik": bik,
        "dog_total": sum(dog.values()),
        "dog_accounts": dict(dog),
        "dog_unique": len(dog),
    }


def compare_error_logs(left: Path, right: Path) -> dict:
    left_data = parse_errors(left)
    right_data = parse_errors(right)
    left_dog = Counter(left_data["dog_accounts"])
    right_dog = Counter(right_data["dog_accounts"])
    only_left = sorted(set(left_dog) - set(right_dog))
    only_right = sorted(set(right_dog) - set(left_dog))
    count_diff = {
        acc: {"left": left_dog[acc], "right": right_dog[acc], "delta": right_dog[acc] - left_dog[acc]}
        for acc in sorted(set(left_dog) & set(right_dog))
        if left_dog[acc] != right_dog[acc]
    }
    return {
        "left": left.name,
        "right": right.name,
        "left_dog_total": left_data["dog_total"],
        "right_dog_total": right_data["dog_total"],
        "left_unique": left_data["dog_unique"],
        "right_unique": right_data["dog_unique"],
        "left_bik": left_data["bik"],
        "right_bik": right_data["bik"],
        "left_duration": left_data["duration"],
        "right_duration": right_data["duration"],
        "accounts_identical": left_dog == right_dog,
        "only_left": {acc: left_dog[acc] for acc in only_left},
        "only_right": {acc: right_dog[acc] for acc in only_right},
        "count_diff": count_diff,
    }


def compare_statement_mxl(left: Path, right: Path) -> dict:
    rows_left = parse_rows(extract_hash_cells(left))
    rows_right = parse_rows(extract_hash_cells(right))
    cnt_left = Counter(row_signature(row) for row in rows_left)
    cnt_right = Counter(row_signature(row) for row in rows_right)
    biz_diff = sum((cnt_left - cnt_right).values()) + sum((cnt_right - cnt_left).values())

    def bal_key(row: dict) -> tuple:
        return row_signature(row) + (tuple(row.get("balances", [])),)

    bal_left = Counter(bal_key(row) for row in rows_left)
    bal_right = Counter(bal_key(row) for row in rows_right)
    bal_diff = sum((bal_left - bal_right).values()) + sum((bal_right - bal_left).values())

    return {
        "left": left.name,
        "right": right.name,
        "rows_left": len(rows_left),
        "rows_right": len(rows_right),
        "md5_left": md5_file(left),
        "md5_right": md5_file(right),
        "bytes_identical": md5_file(left) == md5_file(right),
        "business_multiset_diff": biz_diff,
        "balance_multiset_diff": bal_diff,
    }


def compare_pp_mxl(left: Path, right: Path) -> dict:
    _, rows_left = parse_primary_rows(extract_hash_cells(left))
    _, rows_right = parse_primary_rows(extract_hash_cells(right))
    cnt_left = Counter(core_key(row) for row in rows_left)
    cnt_right = Counter(core_key(row) for row in rows_right)
    core_diff = sum((cnt_left - cnt_right).values()) + sum((cnt_right - cnt_left).values())
    return {
        "left": left.name,
        "right": right.name,
        "rows_left": len(rows_left),
        "rows_right": len(rows_right),
        "md5_left": md5_file(left),
        "md5_right": md5_file(right),
        "bytes_identical": md5_file(left) == md5_file(right),
        "core_multiset_diff": core_diff,
    }


def main() -> int:
    report = {
        "errors": {
            "ispr5_vs_original": compare_error_logs(
                REG / "Ошибки_новые_0106_0506_после доработок41_оригинал.txt",
                REG / "Ошибки_новые_0106_0506_после доработок5.txt",
            ),
            "ispr5_vs_ispr4": compare_error_logs(
                REG / "Ошибки_новые_0106_0506_после доработок41.txt",
                REG / "Ошибки_новые_0106_0506_после доработок5.txt",
            ),
        },
        "mxl": {
            "ispr5_vs_stalo": compare_statement_mxl(
                REG / "0106__0506___стало.mxl",
                REG / "0106__0506___стало_после_испр5.mxl",
            ),
            "ispr5_vs_ispr4": compare_statement_mxl(
                REG / "0106__0506___стало_после_испр4.mxl",
                REG / "0106__0506___стало_после_испр5.mxl",
            ),
            "vypiski5_vs_stalo": compare_statement_mxl(
                REG / "0106__0506___стало.mxl",
                REG / "0106__0506__Выписки_стало_после_испр5.mxl",
            ),
        },
        "pp": {
            "ispr5_vs_ispr4": compare_pp_mxl(
                REG / "0106__0506__ПП_стало_после_испр4.mxl",
                REG / "0106__0506__ПП_стало_после_испр5.mxl",
            ),
            "ispr5_vs_original_pp": compare_pp_mxl(
                REG / "0106__0506__ПП_Оригинал4.mxl",
                REG / "0106__0506__ПП_стало_после_испр5.mxl",
            ),
        },
    }

    out = REG / "0106_ispr5_verify.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== ERRORS ispr5 vs ORIGINAL ===")
    e = report["errors"]["ispr5_vs_original"]
    print(f"  DogovorDU: {e['left_dog_total']} / {e['right_dog_total']} unique {e['left_unique']}/{e['right_unique']}")
    print(f"  BIK: {e['left_bik']} / {e['right_bik']}")
    print(f"  Duration: {e['left_duration']} | {e['right_duration']}")
    print(f"  Accounts identical: {e['accounts_identical']}")
    if e["only_left"]:
        print(f"  Only in original: {e['only_left']}")
    if e["only_right"]:
        print(f"  Only in ispr5: {e['only_right']}")
    if e["count_diff"]:
        print(f"  Count diff: {e['count_diff']}")

    print("\n=== ERRORS ispr5 vs ispr4 ===")
    e4 = report["errors"]["ispr5_vs_ispr4"]
    print(f"  DogovorDU: {e4['left_dog_total']} / {e4['right_dog_total']} unique {e4['left_unique']}/{e4['right_unique']}")
    print(f"  Accounts identical: {e4['accounts_identical']}")
    if e4["only_right"]:
        print(f"  Removed from ispr4: {e4['only_left']}")
        print(f"  Added in ispr5: {e4['only_right']}")

    print("\n=== MXL ===")
    for key, item in report["mxl"].items():
        print(
            f"  {key}: rows {item['rows_left']}/{item['rows_right']} "
            f"bytes={item['bytes_identical']} biz_diff={item['business_multiset_diff']} "
            f"bal_diff={item['balance_multiset_diff']}"
        )

    print("\n=== PP ===")
    for key, item in report["pp"].items():
        print(
            f"  {key}: rows {item['rows_left']}/{item['rows_right']} "
            f"bytes={item['bytes_identical']} core_diff={item['core_multiset_diff']}"
        )

    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
