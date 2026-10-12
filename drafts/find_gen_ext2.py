#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search transcripts and nearby trees for the parallel deal-generator extension."""
import os

NEEDLES = [
    "ОбработкаЗагрузкиСделок",
    "СоздатьОбъектыПоДоговору",
]
ROOTS = [
    r"C:\Users\Acer\.cursor\projects\c-1c-Cursor-1c-WIM-DEV\agent-transcripts",
    r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\cfe",
]
OUT = r"C:\1c\Cursor_1c\WIM_DEV\drafts\find_gen_ext2_result.txt"
hits = []
for root in ROOTS:
    if not os.path.isdir(root):
        hits.append("MISSING " + root)
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        # skip huge logs
        if "1Cv8Log" in dirpath:
            continue
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            if os.path.getsize(path) > 20_000_000:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            for needle in NEEDLES:
                if needle in text:
                    hits.append(needle + " :: " + path)
                    break

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(hits) if hits else "NONE")
print("hits", len(hits))
