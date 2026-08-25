#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Печать подробных диффов из imdev7330_compare_raw.json в текстовый файл."""

import json
import os
import sys

DOC = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects",
    "IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ",
    "Документация")

with open(os.path.join(DOC, "imdev7330_compare_raw.json"), "r", encoding="utf-8") as f:
    report = json.load(f)

only = sys.argv[1] if len(sys.argv) > 1 else None

out = []
for block in report:
    for it in block["items"]:
        if it.get("identical") or not it.get("found"):
            continue
        if only and only not in block["key"]:
            continue
        out.append("=" * 100)
        out.append("%s :: %s  (ext lines=%s, cf lines=%s)" % (
            block["key"], it["cf_name_expected"], it["ext_lines"], it["cf_lines"]))
        out.append("annotations: %s" % it["annotations"])
        out.append("-" * 100)
        out.append(it["diff"])

text = "\n".join(out)
path = os.path.join(DOC, "imdev7330_diffs.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("OK saved: %s (%d chars)" % (path, len(text)))
