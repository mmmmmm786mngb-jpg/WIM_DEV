#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сводка замеров создания торговых поручений РОСТ."""

import json
import os
from collections import defaultdict

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Тестирование", "reports", "measure_rost_keys.json")
OUT = os.path.join(os.path.dirname(SRC), "measure_rost_keys_summary.txt")


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    groups = defaultdict(list)
    for row in data["rows"]:
        if row["name"].startswith("Создание торговых поручений"):
            groups[row["name"]].append(row)
    lines = []
    for name, rows in sorted(groups.items(), key=lambda item: -max(x["seconds"] for x in item[1])):
        seconds = [x["seconds"] for x in rows]
        lines.append(
            "%s | n=%d | sum=%.3f | avg=%.3f | max=%.3f | min=%.3f"
            % (name, len(rows), sum(seconds), sum(seconds) / len(seconds), max(seconds), min(seconds))
        )
        top = sorted(rows, key=lambda item: -item["seconds"])[:8]
        for row in top:
            lines.append("  %.3f sec weight=%s comment=%s" % (row["seconds"], row["weight"], row["comment"]))
    text = "\n".join(lines)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("groups", len(groups))


if __name__ == "__main__":
    main()
