#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Разведка структуры исходных данных для пакета презентаций 20.09.2026.

Файлы Jira-выгрузок и Time Sheet Report имеют расширение .xls,
но фактически являются HTML-таблицами (экспорт Jira в Excel).
Скрипт печатает состав колонок и первые строки каждой таблицы.
Результат пишется в JSON, консольный вывод — только ASCII.
"""

import json
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_report.json")


def safe_print(text):
    """Безопасный вывод в консоль Windows (только ASCII)."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def read_tables(path):
    """Читает HTML-таблицы из файла .xls (фактически HTML)."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        html = fh.read()
    return pd.read_html(html)


def describe(path, label):
    """Формирует описание таблиц файла."""
    info = {"label": label, "file": os.path.basename(path), "tables": []}
    try:
        tables = read_tables(path)
    except Exception as exc:
        info["error"] = str(exc)
        safe_print("ERROR %s: %s" % (label, exc))
        return info

    for idx, df in enumerate(tables):
        entry = {
            "index": idx,
            "shape": list(df.shape),
            "columns": [str(c) for c in df.columns],
            "head": df.head(4).astype(str).values.tolist(),
        }
        info["tables"].append(entry)
        safe_print("  table %d: rows=%d cols=%d" % (idx, df.shape[0], df.shape[1]))
    return info


def main():
    targets = [
        (os.path.join(BASE, "задачиАванкору VTB Capital - JIRA 2026-09-17T13_22_34+0300.xls"), "avancor_jira"),
        (os.path.join(BASE, "внутренние задачи VTB Capital - JIRA 2026-09-17T13_23_36+0300.xls"), "internal_jira"),
    ]

    ts_dir = os.path.join(BASE, "Reprot Time _Время задач")
    for name in sorted(os.listdir(ts_dir)):
        if name.lower().endswith(".xls"):
            targets.append((os.path.join(ts_dir, name), "timesheet:" + name))

    result = []
    for path, label in targets:
        safe_print("== %s" % label.encode("ascii", "replace").decode("ascii"))
        if not os.path.exists(path):
            safe_print("  MISSING")
            continue
        result.append(describe(path, label))

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    safe_print("OK - report written")


if __name__ == "__main__":
    sys.exit(main())
