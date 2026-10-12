#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find files and folders related to the parallel deal generator extension."""
import os

roots = [
    r"C:\1c\Cursor_1c\WIM_DEV",
    r"C:\1c\Cursor_1c\WORK",
]
needles_name = (
    "ОбработкаЗагрузкиСделок",
    "ГенераторСделок",
    "Паралл",
)
needles_text = (
    "ОбработкаЗагрузкиСделок",
)
out = r"C:\1c\Cursor_1c\WIM_DEV\drafts\find_cfe_name.txt"
hits = []
skip_dirs = {"1Cv8Log", ".git", "node_modules", "__pycache__", ".code-index"}

for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        base = os.path.basename(dirpath)
        for needle in needles_name:
            if needle.lower() in base.lower() or needle in base:
                hits.append("DIR " + dirpath)
                break
        for fn in filenames:
            low = fn.lower()
            path = os.path.join(dirpath, fn)
            if any(n.lower() in low for n in needles_name) or "обработказагрузки" in low:
                hits.append("NAME " + path)
            if low.endswith((".bsl", ".xml", ".cfe", ".md", ".html", ".txt")) and "ОбработкаЗагрузкиСделок" in fn:
                hits.append("FN " + path)
            # text search only small-ish text files outside huge CF dump of main config
            if "\\SRC\\CF\\" in path or "/SRC/CF/" in path:
                continue
            if not low.endswith((".bsl", ".xml", ".md", ".html", ".txt")):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size > 5_000_000:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "ОбработкаЗагрузкиСделок" in text:
                hits.append("TEXT " + path)

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(hits) if hits else "NONE")
print("hits", len(hits))
