#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare error message logs for 0106-0506 regression."""

import json
import re
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OLD_PATH = SCRIPT_DIR / "Ошибки_старые_0106_0506.txt"
NEW_PATH = SCRIPT_DIR / "Ошибки_новые_0106_0506.txt"
OUT_PATH = SCRIPT_DIR / "0106_errors_compare.json"

ACCOUNT_RE = re.compile(r"Для счета: (\d+) не определен")
BIK_RE = re.compile(r"БИК = (\d+)")


def load_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp1251"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            text = raw.decode("cp1251", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def classify(line: str) -> str:
    if line.startswith("Продолжительность"):
        return "__duration__"
    return line


def account_counts(lines: list[str]) -> Counter:
    result = Counter()
    for line in lines:
        match = ACCOUNT_RE.search(line)
        if match:
            result[match.group(1)] += 1
    return result


def main() -> int:
    old_lines = load_lines(OLD_PATH)
    new_lines = load_lines(NEW_PATH)

    old_msgs = Counter(classify(line) for line in old_lines)
    new_msgs = Counter(classify(line) for line in new_lines)

    only_old = old_msgs - new_msgs
    only_new = new_msgs - old_msgs

    acc_old = account_counts(old_lines)
    acc_new = account_counts(new_lines)

    report = {
        "lines": {"old": len(old_lines), "new": len(new_lines)},
        "unique_types": {"old": len(old_msgs), "new": len(new_msgs)},
        "duration": {
            "old": next((k for k in old_msgs if k.startswith("Продолжительность")), ""),
            "new": next((k for k in new_msgs if k.startswith("Продолжительность")), ""),
        },
        "only_old": dict(only_old),
        "only_new": dict(only_new),
        "accounts": {},
        "bik_040702788": {
            "old": old_msgs.get("Не найдена запись по БИК в справочнике Банки для БИК = 040702788", 0),
            "new": new_msgs.get("Не найдена запись по БИК в справочнике Банки для БИК = 040702788", 0),
        },
    }

    all_accounts = sorted(set(acc_old) | set(acc_new))
    for account in all_accounts:
        report["accounts"][account] = {
            "old": acc_old[account],
            "new": acc_new[account],
        }

    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== ERROR LOGS 0106-0506 ===")
    print(f"Lines: OLD={len(old_lines)} NEW={len(new_lines)}")
    print(f"Unique types: OLD={len(old_msgs)} NEW={len(new_msgs)}")
    print(f"Duration OLD: {report['duration']['old']}")
    print(f"Duration NEW: {report['duration']['new']}")
    print(f"BIK 040702788: OLD={report['bik_040702788']['old']} NEW={report['bik_040702788']['new']}")
    print()

    accounts_only_old = {a for a in all_accounts if acc_old[a] and not acc_new[a]}
    accounts_only_new = {a for a in all_accounts if acc_new[a] and not acc_old[a]}
    accounts_diff_count = {a for a in all_accounts if acc_old[a] != acc_new[a]}

    print(f"Accounts only OLD: {len(accounts_only_old)}")
    for a in sorted(accounts_only_old):
        print(f"  {a} x{acc_old[a]}")
    print(f"Accounts only NEW: {len(accounts_only_new)}")
    for a in sorted(accounts_only_new):
        print(f"  {a} x{acc_new[a]}")
    print(f"Accounts with different counts: {len(accounts_diff_count)}")
    for a in sorted(accounts_diff_count):
        print(f"  {a}: OLD={acc_old[a]} NEW={acc_new[a]}")

    print()
    print(f"Message types only OLD: {sum(only_old.values())} lines")
    for msg, cnt in only_old.most_common(10):
        if msg != "__duration__":
            print(f"  x{cnt} | {msg[:90]}")
    print(f"Message types only NEW: {sum(only_new.values())} lines")
    for msg, cnt in only_new.most_common(10):
        if not msg.startswith("Продолжительность"):
            print(f"  x{cnt} | {msg[:90]}")

    same_multiset = not only_old and not only_new
    same_accounts = acc_old == acc_new
    print()
    print(f"VERDICT messages multiset identical: {same_multiset}")
    print(f"VERDICT account warnings identical: {same_accounts}")
    print(f"Saved: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
