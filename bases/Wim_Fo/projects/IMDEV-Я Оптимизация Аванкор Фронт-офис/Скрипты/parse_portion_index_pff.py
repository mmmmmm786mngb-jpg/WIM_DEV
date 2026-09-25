#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор папки замеров отладчика после расширения FO_PortionIndex."""

import collections
import os
import re

FOLDER = os.path.join(os.path.dirname(__file__), "..", "ЗамерыРасщиренияИндексов")
OUT = os.path.join(os.path.dirname(__file__), "..", "Тестирование", "reports", "portion_index_pff.txt")

ROW = re.compile(
    r'\},"((?:[^"]|"")*)",(\d+),"((?:[^"]|"")*)",(\d+),([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+),',
)

KEYS = (
    "ДополнитьМассив",
    "ИндексПортфелейПорции",
    "ЗаписатьПорцию",
    "ОбработатьДерево",
    "ДеревоЗначенийПоСоставу",
    "ДеревоЗначенийПоЭмитентам",
    "НекаяВременнаяТаблица",
    "ДобавитьВТ",
    "БазисыОтАктивов",
    "РасширенияПортфелей",
    "ПроверкаПоЛимитам",
    "ПроверкаИОтправка",
    "Набор.Записать",
    "Записать()",
    "Выполнить()",
)


def parse_file(path):
    text = open(path, "r", encoding="utf-8-sig").read()
    rows = []
    for match in ROW.finditer(text):
        module, line, code, count, total, pure, total_share, pure_share = match.groups()
        code = code.replace('""', '"').replace("\n", " ").replace("\r", " ")
        rows.append((
            module,
            int(line),
            code,
            int(count),
            float(total),
            float(pure),
        ))
    return rows


def main():
    names = sorted(
        (name for name in os.listdir(FOLDER) if name.lower().endswith(".pff")),
        key=lambda name: (len(name), name),
    )
    lines = []
    agg = {}
    lines.append("FILES")
    for name in names:
        rows = parse_file(os.path.join(FOLDER, name))
        pure_sum = sum(item[5] for item in rows)
        total_max = max((item[4] for item in rows), default=0)
        lines.append("%s\trows %s\tpure %.3f\tmax_total %.3f" % (name, len(rows), pure_sum, total_max))
        top = sorted(rows, key=lambda row: row[5], reverse=True)[:3]
        for item in top:
            code = item[2]
            if len(code) > 90:
                code = code[:90]
            lines.append("  %.3f\t%s\t%s:%s\t%s" % (item[5], item[3], item[0], item[1], code))
        for item in rows:
            key = (item[0], item[1], item[2])
            bucket = agg.get(key)
            if bucket is None:
                agg[key] = [item[3], item[5], item[4]]
            else:
                bucket[0] += item[3]
                bucket[1] += item[5]
                if item[4] > bucket[2]:
                    bucket[2] = item[4]
    pure_all = sum(value[1] for value in agg.values())
    lines.append("")
    lines.append("AGG pure_sum_sec %.3f" % pure_all)
    lines.append("AGG lines %s" % len(agg))
    lines.append("")
    lines.append("TOP PURE LINES")
    ranked = sorted(agg.items(), key=lambda pair: pair[1][1], reverse=True)
    for key, value in ranked[:50]:
        code = key[2]
        if len(code) > 140:
            code = code[:140]
        lines.append("%.3f\tcalls %s\tmax_total %.3f\t%s:%s\t%s" % (
            value[1], value[0], value[2], key[0], key[1], code))
    modules = collections.Counter()
    for key, value in agg.items():
        modules[key[0]] += value[1]
    lines.append("")
    lines.append("TOP MODULES")
    for name, seconds in modules.most_common(20):
        lines.append("%.3f\t%s" % (seconds, name))
    lines.append("")
    lines.append("KEY LINES")
    for key, value in ranked:
        blob = key[2]
        if any(marker in blob for marker in KEYS) and value[1] >= 0.05:
            code = blob if len(blob) <= 160 else blob[:160]
            lines.append("%.3f\tcalls %s\t%s:%s\t%s" % (value[1], value[0], key[0], key[1], code))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("WROTE", OUT)
    print("files", len(names), "pure", round(pure_all, 1))


if __name__ == "__main__":
    main()
