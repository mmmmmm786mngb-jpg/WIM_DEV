#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая проверка структурной целостности сгенерированного HTML ТЗ.
"""

import os
import re
import sys

p = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Документация",
    "requirements",
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
        "ul", "ol", "li", "pre", "h2", "h3", "details"]
print()
print("Tag balance:")
for t in tags:
    o = len(re.findall(r"<" + t + r"\b", content))
    c = len(re.findall(r"</" + t + r">", content))
    flag = "OK" if o == c else "MISMATCH"
    print(f"  {t:10s}  open={o:4d}  close={c:4d}  {flag}")

print()
block_count = content.count('class="block"')
fr_count = content.count('badge fr')
alg_count = content.count('badge alg')
nfr_count = content.count('badge nfr')
print(f"Number of section blocks: {block_count}")
print(f"Number of FR badges: {fr_count}")
print(f"Number of ALG badges: {alg_count}")
print(f"Number of NFR badges: {nfr_count}")
print()
if "<!DOCTYPE html>" in content:
    print("DOCTYPE: OK")
if 'charset="UTF-8"' in content:
    print("Charset declared: UTF-8 OK")
if "</html>" in content:
    print("Closing </html>: OK")
