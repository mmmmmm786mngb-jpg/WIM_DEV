#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка структурной целостности HTML ТЗ после правок (раунд 1).
Целевой файл: КорректировкаОтПользователя_1/tz_ndfl_engine.html.
"""

import os
import re
import sys

p = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "КорректировкаОтПользователя_1",
    "tz_ndfl_engine.html",
)

if not os.path.exists(p):
    print(f"NOT FOUND: {p}")
    sys.exit(1)

with open(p, "r", encoding="utf-8") as f:
    content = f.read()

print(f"File: {p}")
print(f"Size: {os.path.getsize(p)} bytes")
print(f"Lines: {content.count(chr(10)) + 1}")

tags = ["section", "div", "table", "tbody", "thead", "tr", "td", "th",
        "ul", "ol", "li", "pre", "h2", "h3", "h4", "details",
        "ins", "del", "header", "aside", "main", "p", "span"]
print()
print("Tag balance:")
mismatch = False
for t in tags:
    o = len(re.findall(r"<" + t + r"\b", content))
    c = len(re.findall(r"</" + t + r">", content))
    flag = "OK" if o == c else "MISMATCH"
    if o != c:
        mismatch = True
    print(f"  {t:10s}  open={o:4d}  close={c:4d}  {flag}")

print()
block_count = content.count('class="block"')
fr_count = content.count('badge fr')
alg_count = content.count('badge alg')
nfr_count = content.count('badge nfr')
edit_count = content.count('badge edit')
edit_mark = content.count('class="edit-mark"')
edit_mark_del = content.count('class="edit-mark-del"')
edit_block = content.count('class="edit-block"')
ks_count = len(re.findall(r"\bКС-\d{2}\b", content))

print(f"Number of section blocks: {block_count}")
print(f"Number of FR badges: {fr_count}")
print(f"Number of ALG badges: {alg_count}")
print(f"Number of NFR badges: {nfr_count}")
print(f"Number of EDIT badges: {edit_count}")
print(f"Inline ins.edit-mark: {edit_mark}")
print(f"Inline del.edit-mark-del: {edit_mark_del}")
print(f"Edit-block wrappers: {edit_block}")
print(f"КС-NN occurrences in text: {ks_count}")
print()
if "<!DOCTYPE html>" in content:
    print("DOCTYPE: OK")
if 'charset="UTF-8"' in content:
    print("Charset declared: UTF-8 OK")
if "</html>" in content:
    print("Closing </html>: OK")
if mismatch:
    print()
    print("WARNING: tag balance mismatch detected.")
    sys.exit(2)
print()
print("Validation: PASSED")
