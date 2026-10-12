#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print context around СоздатьОбъектыПоДоговору in transcripts."""
import os

root = r"C:\Users\Acer\.cursor\projects\c-1c-Cursor-1c-WIM-DEV\agent-transcripts"
needle = "СоздатьОбъектыПоДоговору"
out_path = r"C:\1c\Cursor_1c\WIM_DEV\drafts\extract_method.txt"
parts = []
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        path = os.path.join(dirpath, fn)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        idx = 0
        n = 0
        while True:
            i = text.find(needle, idx)
            if i < 0:
                break
            n += 1
            start = max(0, i - 400)
            end = min(len(text), i + 500)
            parts.append(f"\n===== {path} #{n}\n" + text[start:end].replace("\n", " "))
            idx = i + len(needle)
            if n >= 3:
                break
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(parts) if parts else "NONE")
print("parts", len(parts))
