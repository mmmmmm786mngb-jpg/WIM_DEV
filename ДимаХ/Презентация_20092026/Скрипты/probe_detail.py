#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальный разбор структуры: непустые колонки Jira-выгрузок и состав Time Sheet.
Результат пишется в текстовый файл UTF-8 (в консоль - только ASCII).
"""

import io
import os
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPTS, "probe_detail.txt")

AVANCOR = os.path.join(BASE, "задачиАванкору VTB Capital - JIRA 2026-09-17T13_22_34+0300.xls")
INTERNAL = os.path.join(BASE, "внутренние задачи VTB Capital - JIRA 2026-09-17T13_23_36+0300.xls")
TS_DIR = os.path.join(BASE, "Reprot Time _Время задач")


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def read_tables(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        html = fh.read()
    return pd.read_html(io.StringIO(html))


def dump_jira(path, label, lines):
    """Выводит непустые колонки таблицы задач Jira."""
    tables = read_tables(path)
    df = tables[1]
    lines.append("=" * 90)
    lines.append("JIRA: %s  (%s)" % (label, os.path.basename(path)))
    lines.append("shape: %s" % (df.shape,))
    lines.append("-" * 90)
    for col in df.columns:
        series = df[col]
        non_null = series.notna().sum()
        if non_null == 0:
            continue
        vals = series.dropna().astype(str).unique()[:6]
        lines.append("COL %-42s | filled=%3d | %s" % (str(col)[:42], non_null, " | ".join(v[:45] for v in vals)))
    lines.append("")
    return df


def dump_timesheets(lines):
    """Выводит состав всех файлов Time Sheet Report."""
    for name in sorted(os.listdir(TS_DIR)):
        if not name.lower().endswith(".xls"):
            continue
        path = os.path.join(TS_DIR, name)
        tables = read_tables(path)
        lines.append("=" * 90)
        lines.append("TIMESHEET: %s" % name)
        lines.append("table0 (header): %s" % tables[0].astype(str).values.tolist())
        df = tables[1]
        lines.append("shape: %s" % (df.shape,))
        lines.append("columns: %s" % [str(c) for c in df.columns])
        lines.append("-" * 90)
        with pd.option_context("display.max_columns", None, "display.width", 250):
            lines.append(df.head(12).astype(str).to_string())
        lines.append("... tail ...")
        with pd.option_context("display.max_columns", None, "display.width", 250):
            lines.append(df.tail(6).astype(str).to_string())
        lines.append("")


def main():
    lines = []
    dump_jira(AVANCOR, "avancor", lines)
    dump_jira(INTERNAL, "internal", lines)
    dump_timesheets(lines)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    safe_print("OK - detail written, lines=%d" % len(lines))


if __name__ == "__main__":
    sys.exit(main())
