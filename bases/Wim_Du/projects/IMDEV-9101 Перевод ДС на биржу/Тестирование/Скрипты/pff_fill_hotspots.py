#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hotspots under fill path from PFF."""

import re
from pathlib import Path

p = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9101 "
    r"Перевод ДС на биржу\Тестирование\Новый4_массовое_Замеры_0107_1307.pff"
)
text = p.read_text(encoding="utf-8-sig")
pat = re.compile(
    r'\},"([^"]+)",(\d+),"((?:\\.|[^"\\])*)",(\d+),([0-9.]+),([0-9.]+)',
    re.S,
)
rows = []
for m in pat.finditer(text):
    rows.append({
        "mod": m.group(1),
        "line": int(m.group(2)),
        "code": m.group(3).replace("\n", " ").replace("\r", " "),
        "n": int(m.group(4)),
        "t1": float(m.group(5)),
        "t2": float(m.group(6)),
    })

print("=== Document.ПП object module (no IMDEV), t1>=0.1 ===")
for r in sorted(rows, key=lambda x: x["t1"], reverse=True):
    if "Документ.ПлатежноеПоручение.МодульОбъекта" not in r["mod"]:
        continue
    if "IMDEV" in r["mod"]:
        continue
    if r["t1"] < 0.1:
        continue
    print(f"{r['t1']:8.3f}/{r['t2']:7.3f} n={r['n']:4d} L{r['line']}: {r['code'][:110]}")

print("\n=== Templates / DSredstva / ObchegoNaznacheniya for fill context ===")
for r in sorted(rows, key=lambda x: x["t1"], reverse=True):
    blob = r["mod"]
    if not any(k in blob for k in ("ШаблоныПлатежных", "ДенежныеСредства", "ОбщегоНазначения.Модуль")):
        continue
    if r["t1"] < 0.3:
        continue
    # only show if likely fill-related counts around 649/1947/3245
    print(f"{r['t1']:8.3f}/{r['t2']:7.3f} n={r['n']:4d} {blob[-50:]} L{r['line']}: {r['code'][:90]}")
