#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze ispr3 regression artifacts: MXL and error log."""

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


def compare_mxl(left: str, right: str, title: str) -> dict:
    path_left = REG / left
    path_right = REG / right
    rows_left = parse_rows(extract_hash_cells(path_left))
    rows_right = parse_rows(extract_hash_cells(path_right))
    cnt_left = Counter(biz_key(row) for row in rows_left)
    cnt_right = Counter(biz_key(row) for row in rows_right)
    return {
        "title": title,
        "left": left,
        "right": right,
        "rows_left": len(rows_left),
        "rows_right": len(rows_right),
        "bytes_identical": md5_file(path_left) == md5_file(path_right),
        "business_multiset_diff": sum((cnt_left - cnt_right).values())
        + sum((cnt_right - cnt_left).values()),
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


def account_delta(old_name: str, new_name: str) -> dict:
    old = Counter()
    new = Counter()
    for line in load_lines(old_name):
        match = ACCOUNT_RE.search(line)
        if match:
            old[match.group(1)] += 1
    for line in load_lines(new_name):
        match = ACCOUNT_RE.search(line)
        if match:
            new[match.group(1)] += 1
    return {
        account: {"old": old[account], "new": new[account], "delta": new[account] - old[account]}
        for account in sorted(set(old) | set(new))
        if old[account] != new[account]
    }


def main() -> int:
    report = {
        "mxl": [
            compare_mxl(
                "0106__0506___стало.mxl",
                "0106__0506___стало_после_испр3.mxl",
                "baseline_stalo_vs_ispr3",
            ),
            compare_mxl(
                "0106__0506___стало_после_испр2.mxl",
                "0106__0506___стало_после_испр3.mxl",
                "ispr2_vs_ispr3",
            ),
            compare_mxl(
                "0106__0506___было.mxl",
                "0106__0506___стало_после_испр3.mxl",
                "bylo_vs_ispr3",
            ),
        ],
        "errors": {
            "ispr3": summarize_errors("Ошибки_новые_0106_0506_после доработок3.txt"),
            "ispr2": summarize_errors("Ошибки_новые_0106_0506_после доработок2.txt"),
            "baseline_old": summarize_errors("Ошибки_старые_0106_0506.txt"),
        },
        "diffs": {
            "ispr3_vs_old": diff_logs(
                "Ошибки_старые_0106_0506.txt",
                "Ошибки_новые_0106_0506_после доработок3.txt",
            ),
            "ispr3_vs_ispr2": diff_logs(
                "Ошибки_новые_0106_0506_после доработок2.txt",
                "Ошибки_новые_0106_0506_после доработок3.txt",
            ),
        },
        "account_delta_vs_old": account_delta(
            "Ошибки_старые_0106_0506.txt",
            "Ошибки_новые_0106_0506_после доработок3.txt",
        ),
    }

    out = REG / "0106_ispr3_analysis.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== MXL ===")
    for item in report["mxl"]:
        print(
            f"  {item['title']}: bytes_identical={item['bytes_identical']} "
            f"rows={item['rows_left']}/{item['rows_right']} "
            f"biz_diff={item['business_multiset_diff']}"
        )

    print("\n=== ERRORS ===")
    for key in ("baseline_old", "ispr2", "ispr3"):
        err = report["errors"][key]
        print(
            f"  {key}: lines={err['lines']} account_msgs={err['account_messages']} "
            f"unique={err['unique_accounts']} bik={err['bik_040702788']}"
        )
        print(f"    top: {err['top_accounts'][:5]}")

    print("\n=== ispr3 vs OLD ===")
    d = report["diffs"]["ispr3_vs_old"]
    print(
        f"  multiset_identical={d['multiset_identical']} "
        f"only_old={d['only_left_count']} only_new={d['only_right_count']}"
    )
    if d["only_left_top"]:
        print(f"  only in OLD: {d['only_left_top']}")
    if d["only_right_top"]:
        print(f"  only in ispr3: {d['only_right_top']}")

    print("\n=== ispr3 vs ispr2 ===")
    d2 = report["diffs"]["ispr3_vs_ispr2"]
    print(
        f"  multiset_identical={d2['multiset_identical']} "
        f"only_ispr2={d2['only_left_count']} only_ispr3={d2['only_right_count']}"
    )

    print("\n=== Account delta vs old (top) ===")
    for account, vals in sorted(
        report["account_delta_vs_old"].items(),
        key=lambda x: abs(x[1]["delta"]),
        reverse=True,
    )[:10]:
        print(f"  {account}: old={vals['old']} new={vals['new']} delta={vals['delta']:+d}")

    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
