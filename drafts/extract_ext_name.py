#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract transcript lines about the parallel deal generator extension."""
import os

paths = [
    r"C:\Users\Acer\.cursor\projects\c-1c-Cursor-1c-WIM-DEV\agent-transcripts\d7ed7fbb-9ad9-4fb2-8eb0-bb40c1f39aeb\d7ed7fbb-9ad9-4fb2-8eb0-bb40c1f39aeb.jsonl",
    r"C:\Users\Acer\.cursor\projects\c-1c-Cursor-1c-WIM-DEV\agent-transcripts\f1ed90de-741d-4bac-89ee-4c88b3f6fdb7\compaction\segment_000.md",
]
keys = (
    "ОбработкаЗагрузкиСделок",
    "расширен",
    "Расширен",
    ".cfe",
    "Генератор",
    "параллел",
)
out = r"C:\1c\Cursor_1c\WIM_DEV\drafts\extract_ext_name.txt"
chunks = []
for path in paths:
    chunks.append("===== " + path)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            if any(k in line for k in keys):
                chunks.append(f"{i}: {line[:1500]}")
                if len(chunks) > 80:
                    break
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(chunks))
print("lines", len(chunks))
