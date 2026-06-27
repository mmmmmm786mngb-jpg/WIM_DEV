#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze ispr2 regression artifacts: MXL and error log."""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent
sys.path.insert(0, str(REG))
from compare_mxl import extract_hash_cells, parse_rows  # noqa: E402

ACCOUNT_RE = re.compile(r"Для счета: (\d+) не определен")
BIK_MSG = "Не найдена запись по БИК в справочнике Банки для БИК = 040702788"


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def biz_key(row: dict) -> tuple:
    return (
        row.get("Data", ""),
        row.get("NomerScheta", ""),
        row.get("Dogovor", ""),
        row.get("BankSchet", ""),
    )


def bal_key(row: dict) -> tuple:
    return biz_key(row) + (tuple(row.get("balances", [])),)


def compare_mxl(left: str, right: str, title: str) -> dict:
    path_left = REG / left
    path_right = REG / right
    rows_left = parse_rows(extract_hash_cells(path_left))
    rows_right = parse_rows(extract_hash_cells(path_right))
    cnt_left = Counter(biz_key(row) for row in rows_left)
    cnt_right = Counter(biz_key(row) for row in rows_right)
    bal_left = Counter(bal_key(row) for row in rows_left)
    bal_right = Counter(bal_key(row) for row in rows_right)
    return {
        "title": title,
        "left": left,
        "right": right,
        "rows_left": len(rows_left),
        "rows_right": len(rows_right),
        "md5_left": md5_file(path_left),
        "md5_right": md5_file(path_right),
        "bytes_identical": md5_file(path_left) == md5_file(path_right),
        "business_multiset_diff": sum((cnt_left - cnt_right).values()) + sum((cnt_right - cnt_left).values()),
        "balance_multiset_diff": sum((bal_left - bal_right).values()) + sum((bal_right - bal_left).values()),
    }


def load_lines(name: str) -> list[str]:
    raw = (REG / name).read_bytes()
    for encoding in ("utf-8", "cp1251"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            text = raw.decode("cp1251", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def summarize_errors(name: str) -> dict:
    lines = load_lines(name)
    msgs = Counter(lines)
    accounts = Counter()
    for line in lines:
        match = ACCOUNT_RE.search(line)
        if match:
            accounts[match.group(1)] += 1
    duration = next((line for line in lines if line.startswith("Продолжительность")), "")
    return {
        "file": name,
        "lines": len(lines),
        "duration": duration,
        "bik_040702788": msgs.get(BIK_MSG, 0),
        "account_messages": sum(accounts.values()),
        "unique_accounts": len(accounts),
        "top_accounts": accounts.most_common(10),
        "message_types": len(msgs),
    }


def diff_logs(left_name: str, right_name: str) -> dict:
    left = Counter(load_lines(left_name))
    right = Counter(load_lines(right_name))
    only_left = left - right
    only_right = right - left
    return {
        "left": left_name,
        "right": right_name,
        "only_left_count": sum(only_left.values()),
        "only_right_count": sum(only_right.values()),
        "only_left_top": dict(only_left.most_common(10)),
        "only_right_top": dict(only_right.most_common(10)),
        "multiset_identical": left == right,
    }


def main() -> int:
    report = {
        "mxl": [
            compare_mxl("0106__0506___было.mxl", "0106__0506___стало_после_испр2.mxl", "bylo_vs_ispr2"),
            compare_mxl("0106__0506___стало_после_испр.mxl", "0106__0506___стало_после_испр2.mxl", "ispr1_vs_ispr2"),
            compare_mxl("0106__0506___стало.mxl", "0106__0506___стало_после_испр2.mxl", "stalo_vs_ispr2"),
        ],
        "errors": {
            "ispr2": summarize_errors("Ошибки_новые_0106_0506_после доработок2.txt"),
            "baseline_old": summarize_errors("Ошибки_старые_0106_0506.txt"),
            "v591_sim": summarize_errors("Ошибки_новые_0106_0506_v591_sim.txt"),
            "ispr1_log": summarize_errors("Ошибки_новые_0106_0506_после доработок.txt"),
        },
        "diffs": {
            "ispr2_vs_old": diff_logs("Ошибки_старые_0106_0506.txt", "Ошибки_новые_0106_0506_после доработок2.txt"),
            "ispr2_vs_sim": diff_logs("Ошибки_новые_0106_0506_v591_sim.txt", "Ошибки_новые_0106_0506_после доработок2.txt"),
            "ispr2_vs_ispr1_log": diff_logs(
                "Ошибки_новые_0106_0506_после доработок.txt",
                "Ошибки_новые_0106_0506_после доработок2.txt",
            ),
        },
    }

    out = REG / "0106_ispr2_analysis.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("MXL:")
    for item in report["mxl"]:
        print(
            f"  {item['title']}: rows {item['rows_left']}/{item['rows_right']} "
            f"bytes_identical={item['bytes_identical']} "
            f"biz_diff={item['business_multiset_diff']} bal_diff={item['balance_multiset_diff']}"
        )

    print("ERRORS ispr2:", report["errors"]["ispr2"])
    print("DIFF ispr2 vs sim591 identical:", report["diffs"]["ispr2_vs_sim"]["multiset_identical"])
    print("DIFF ispr2 vs ispr1_log identical:", report["diffs"]["ispr2_vs_ispr1_log"]["multiset_identical"])
    print("Report:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
