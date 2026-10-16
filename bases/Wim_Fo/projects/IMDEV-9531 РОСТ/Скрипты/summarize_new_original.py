#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сводка прогона новой обработки РОСТ."""

import json
import os
from collections import defaultdict

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Тестирование", "reports", "new_original_run.json")
OUT = os.path.join(os.path.dirname(SRC), "new_original_summary.txt")


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    lines = []
    lines.append("COUPON error: " + str(data.get("coupons", {}).get("ошибка", ""))[:500])
    lines.append("COUPON docs: " + str(data.get("coupons", {}).get("документы")))
    lines.append("")
    lines.append("STEPS")
    for step in data["run"]["шаги"]:
        err = (step.get("ошибка") or step.get("ошибка_задания") or "")
        lines.append(
            "%s | %s | %s s | orders %s | err %s"
            % (step.get("шаг"), step.get("состояние") or step.get("сценарий"), step.get("длительность_с"),
               step.get("поручений"), err[:240].replace("\n", " "))
        )
        log = step.get("лог") or ""
        if log:
            tail = " | ".join(line.strip() for line in log.splitlines() if line.strip())[-700:]
            lines.append("  log: " + tail)
    lines.append("")
    groups = defaultdict(list)
    for row in data["measurements"]:
        groups[row["ключ"]].append(row)
    lines.append("MEASURES")
    for key, rows in sorted(groups.items(), key=lambda item: -sum(x["время_с"] for x in item[1])):
        seconds = [x["время_с"] for x in rows]
        weights = [x["вес"] for x in rows]
        lines.append(
            "%s | n=%d | sum=%.3f | avg=%.3f | max=%.3f | weight_sum=%.0f"
            % (key, len(rows), sum(seconds), sum(seconds) / len(seconds), max(seconds), sum(weights))
        )
        for row in sorted(rows, key=lambda item: -item["время_с"])[:4]:
            lines.append("  %.3f w=%s %s" % (row["время_с"], row["вес"], str(row["комментарий"])[:180]))
    lines.append("")
    lines.append("ORDERS %d" % len(data["orders"]))
    by_kind = defaultdict(int)
    for order in data["orders"]:
        by_kind[str(order.get("Вид"))] += 1
    for kind, count in by_kind.items():
        lines.append("  %s %d" % (kind, count))
    text = "\n".join(lines)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("lines", len(lines))


if __name__ == "__main__":
    main()
