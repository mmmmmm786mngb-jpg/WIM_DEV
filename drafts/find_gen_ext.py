#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find extension or module related to parallel deal generator."""
import os

ROOTS = [
    r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF",
    r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\cfe",
    r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\epf",
]
NEEDLES = [
    "ОбработкаЗагрузкиСделок",
    "СоздатьОбъектыПоДоговору",
    "ГенераторСделок",
]
OUT = r"C:\1c\Cursor_1c\WIM_DEV\drafts\find_gen_ext_result.txt"

hits = []
for root in ROOTS:
    if not os.path.isdir(root):
        hits.append("MISSING " + root)
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        base = os.path.basename(dirpath)
        for needle in NEEDLES:
            if needle in base:
                hits.append("DIR " + dirpath)
        for fn in filenames:
            if not fn.lower().endswith((".bsl", ".xml", ".txt")):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            for needle in NEEDLES:
                if needle in text:
                    hits.append("FILE " + needle + " " + path)
                    break

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(hits) if hits else "NONE")
print("hits", len(hits))
