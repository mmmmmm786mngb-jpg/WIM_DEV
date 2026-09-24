#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор файла замера производительности 1С (.pff) по строкам модулей."""

import collections
import os
import re

SRC = os.path.join(
    os.path.dirname(__file__),
    "..",
    "Новый30_ЗамерРегламентаПроверкаПоЛимитам_ФО_Розн.pff",
)
OUT = os.path.join(os.path.dirname(__file__), "..", "Тестирование", "reports", "retail_pff_top.txt")

ROW = re.compile(
    r'\},"((?:[^"]|"")*)",(\d+),"((?:[^"]|"")*)",(\d+),([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+),',
)


def main():
    text = open(SRC, "r", encoding="utf-8-sig").read()
    rows = []
    for match in ROW.finditer(text):
        module, line, code, count, total, pure, total_share, pure_share = match.groups()
        code = code.replace('""', '"').replace("\n", " ").replace("\r", " ")
        if len(code) > 140:
            code = code[:140]
        rows.append((
            module,
            int(line),
            code,
            int(count),
            float(total),
            float(pure),
            float(total_share),
            float(pure_share),
        ))
    pure_sum = sum(item[5] for item in rows)
    total_max = max((item[4] for item in rows), default=0)
    lines = []
    lines.append("rows %s" % len(rows))
    lines.append("pure_sum_sec %.3f" % pure_sum)
    lines.append("max_total_sec %.3f" % total_max)
    lines.append("")
    lines.append("TOP PURE LINES")
    for item in sorted(rows, key=lambda row: row[5], reverse=True)[:40]:
        lines.append("%.3f\t%.3f\t%s\t%s:%s\t%s" % (
            item[5], item[4], item[3], item[0], item[1], item[2]))
    lines.append("")
    lines.append("TOP MODULES BY PURE")
    modules = collections.Counter()
    module_calls = collections.Counter()
    for item in rows:
        modules[item[0]] += item[5]
        module_calls[item[0]] += item[3]
    for name, seconds in modules.most_common(25):
        lines.append("%.3f\t%s\tcalls_sum %s" % (seconds, name, module_calls[name]))
    keys = (
        "ЗаписатьПорцию",
        "ОбработатьДерево",
        "ДеревоЗначенийПоСоставу",
        "ДеревоЗначенийПоЭмитентам",
        "НекаяВременнаяТаблица",
        "ДобавитьВТ_ТаблицаНабораДанных",
        "Проверить(",
        "БазисыОтАктивов",
        "Выполнить()",
        "Записать()",
    )
    lines.append("")
    lines.append("KEY LINES")
    for item in sorted(rows, key=lambda row: row[5], reverse=True):
        blob = item[2]
        if any(key in blob for key in keys) and item[5] >= 0.05:
            lines.append("%.3f\t%s\t%s:%s\t%s" % (item[5], item[3], item[0], item[1], blob))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("\n".join(lines[:50]))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
