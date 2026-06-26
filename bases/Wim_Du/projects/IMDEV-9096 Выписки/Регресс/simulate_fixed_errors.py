#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulate error log after OPT-02 warning fix (v5.91).
Removes preload warnings for payer-only accounts (not statement accounts).
"""

import json
import re
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OLD_PATH = SCRIPT_DIR / "Ошибки_старые_0106_0506.txt"
NEW_PATH = SCRIPT_DIR / "Ошибки_новые_0106_0506.txt"
FIXED_PATH = SCRIPT_DIR / "Ошибки_новые_0106_0506_v591_sim.txt"
OUT_PATH = SCRIPT_DIR / "0106_errors_compare_v591_sim.json"

# Payer-only warnings removed by preload filter (not in old log, not statement accounts)
PAYER_ONLY_ACCOUNTS = {
    "40701810100000012217",
    "47426810000010090440",
    "47426810024600000949",
    "47426810025600000074",
    "47426810224600000749",
    "47426810225600000049",
    "47426810500000039000",
    "47426810625600001075",
    "47426810877102000018",
    "47426810900000041300",
}

ACCOUNT_RE = re.compile(r"Для счета: (\d+) не определен")


def load_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp1251"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            text = raw.decode("cp1251", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def simulate_fixed_new_lines(new_lines: list[str]) -> tuple[list[str], list[str]]:
    removed = []
    fixed = []
    for line in new_lines:
        match = ACCOUNT_RE.search(line)
        if match and match.group(1) in PAYER_ONLY_ACCOUNTS:
            removed.append(line)
            continue
        fixed.append(line)
    return fixed, removed


def compare(old_lines: list[str], fixed_lines: list[str]) -> dict:
    def norm_msgs(lines):
        return Counter(
            line for line in lines if not line.startswith("Продолжительность")
        )

    old_msgs = norm_msgs(old_lines)
    new_msgs = norm_msgs(fixed_lines)
    only_old = old_msgs - new_msgs
    only_new = new_msgs - old_msgs

    acc_old = Counter()
    acc_new = Counter()
    for line in old_lines:
        m = ACCOUNT_RE.search(line)
        if m:
            acc_old[m.group(1)] += 1
    for line in fixed_lines:
        m = ACCOUNT_RE.search(line)
        if m:
            acc_new[m.group(1)] += 1

    return {
        "lines": {"old": len(old_lines), "new_before": len(load_lines(NEW_PATH)), "new_sim": len(fixed_lines)},
        "only_old": dict(only_old),
        "only_new": dict(only_new),
        "accounts_only_new": {a: acc_new[a] for a in sorted(acc_new) if acc_new[a] and not acc_old[a]},
        "accounts_diff": {
            a: {"old": acc_old[a], "new": acc_new[a]}
            for a in sorted(set(acc_old) | set(acc_new))
            if acc_old[a] != acc_new[a]
        },
        "bik": {
            "old": old_msgs.get("Не найдена запись по БИК в справочнике Банки для БИК = 040702788", 0),
            "new": new_msgs.get("Не найдена запись по БИК в справочнике Банки для БИК = 040702788", 0),
        },
        "multiset_identical": not only_old and not only_new,
    }


if __name__ == "__main__":
    old_lines = load_lines(OLD_PATH)
    new_lines = load_lines(NEW_PATH)
    fixed_lines, removed = simulate_fixed_new_lines(new_lines)

    FIXED_PATH.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")

    report = compare(old_lines, fixed_lines)
    report["removed_payer_only"] = len(removed)
    report["removed_lines"] = removed
    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== SIMULATED ERROR LOG v5.91 (warning fix) ===")
    print(f"NEW before: {len(new_lines)} lines")
    print(f"Removed payer-only warnings: {len(removed)}")
    print(f"NEW after sim: {len(fixed_lines)} lines")
    print(f"BIK 040702788: OLD={report['bik']['old']} NEW={report['bik']['new']}")
    print()
    print("Removed accounts:")
    for line in removed:
        print(f"  - {line}")
    print()
    print(f"Accounts only NEW (after fix): {len(report['accounts_only_new'])}")
    for acc, cnt in report["accounts_only_new"].items():
        print(f"  {acc} x{cnt}")
    print()
    print(f"Account count diffs: {len(report['accounts_diff'])}")
    for acc, vals in report["accounts_diff"].items():
        print(f"  {acc}: OLD={vals['old']} NEW={vals['new']}")
    print()
    print(f"Only OLD message types: {sum(report['only_old'].values())} lines")
    for msg, cnt in Counter(report["only_old"]).most_common(5):
        print(f"  x{cnt} | {msg[:85]}")
    print(f"Only NEW message types: {sum(report['only_new'].values())} lines")
    for msg, cnt in Counter(report["only_new"]).most_common(5):
        print(f"  x{cnt} | {msg[:85]}")
    print()
    print(f"VERDICT multiset identical: {report['multiset_identical']}")
    print(f"Saved: {FIXED_PATH}")
    print(f"Report: {OUT_PATH}")
