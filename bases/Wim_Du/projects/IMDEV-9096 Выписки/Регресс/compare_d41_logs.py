#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare DogovorDU error logs: original vs optimized (d41)."""

import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
ORIG = BASE / "Ошибки_новые_0106_0506_после доработок41_оригинал.txt"
NEW = BASE / "Ошибки_новые_0106_0506_после доработок41.txt"

DOG_RE = re.compile(r"Для счета: (\d+) не определен ДоговорДУ")


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp866"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Cannot decode {path}")


def parse(text: str):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("Продолжительность")
    ]
    dog = Counter()
    bik = 0
    for line in lines:
        m = DOG_RE.search(line)
        if m:
            dog[m.group(1)] += 1
        elif "БИК" in line:
            bik += 1
    return len(lines), dog, bik


def main():
    _, do, bo = parse(read_text(ORIG))
    _, dn, bn = parse(read_text(NEW))

    print("TOTAL lines (excl duration): orig=%d new=%d" % (sum(do.values()) + bo, sum(dn.values()) + bn))
    print("BIK messages: orig=%d new=%d (delta=%+d)" % (bo, bn, bn - bo))
    print("DogovorDU messages: orig=%d new=%d (delta=%+d)" % (sum(do.values()), sum(dn.values()), sum(dn.values()) - sum(do.values())))
    print("Unique DogovorDU accounts: orig=%d new=%d" % (len(do), len(dn)))

    only_new = sorted(set(dn) - set(do))
    only_orig = sorted(set(do) - set(dn))

    print("\n=== ONLY IN OPTIMIZED (%d accounts) ===" % len(only_new))
    for acc in only_new:
        print("  %s: new=%d" % (acc, dn[acc]))

    print("\n=== ONLY IN ORIGINAL (%d accounts) ===" % len(only_orig))
    for acc in only_orig:
        print("  %s: orig=%d" % (acc, do[acc]))

    print("\n=== COUNT DIFF (in both) ===")
    diffs = []
    for acc in sorted(set(do) & set(dn)):
        delta = dn[acc] - do[acc]
        if delta:
            diffs.append((acc, do[acc], dn[acc], delta))
    for acc, o, n, d in sorted(diffs, key=lambda x: -abs(x[3])):
        print("  %s: orig=%d new=%d delta=%+d" % (acc, o, n, d))

    print("\n=== SAME COUNT (%d accounts) ===" % sum(1 for a in set(do) & set(dn) if dn[a] == do[a]))
    for acc in sorted(set(do) & set(dn)):
        if dn[acc] == do[acc]:
            print("  %s: %d" % (acc, do[acc]))


if __name__ == "__main__":
    main()
