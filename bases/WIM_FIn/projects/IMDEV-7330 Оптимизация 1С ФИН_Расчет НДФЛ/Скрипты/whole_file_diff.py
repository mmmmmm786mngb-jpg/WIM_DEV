#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полный построчный дифф модулей расширения и CF (после снятия префикса NDFL_RDU_).

Нужен, чтобы поймать отличия ВНЕ тел процедур: преамбулы, #Область, объявления Перем,
директивы компиляции и т.п.
"""

import difflib
import os

EXT_ROOT = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects",
    "IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ", "Расширения", "NDFL_RDU")
CF_ROOT = r"C:\1c\Cursor_1c\WORK\WIM_FIn\src\cf"
OUT = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects",
    "IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ", "Документация",
    "imdev7330_whole_file_diffs.txt")

RELS = [
    r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ManagerModule.bsl",
    r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ObjectModule.bsl",
    r"DataProcessors\ФормированиеНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl",
    r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ManagerModule.bsl",
    r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ObjectModule.bsl",
    r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ManagerModule.bsl",
    r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ObjectModule.bsl",
    r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl",
]

# Для этих модулей расширение содержит только перехваты, полный дифф файла бессмысленен
SKIP_FULL = {r"Documents\НачислениеНДФЛПоПортфелю\Ext\ObjectModule.bsl"}


def norm(path, strip_prefix):
    with open(path, "r", encoding="utf-8-sig") as f:
        txt = f.read().replace("\r\n", "\n")
    if strip_prefix:
        txt = txt.replace("NDFL_RDU_", "")
    out = [ln.replace("\t", "    ").rstrip() for ln in txt.split("\n")]
    return out


chunks = []
for rel in RELS:
    if rel in SKIP_FULL:
        continue
    pe = os.path.join(EXT_ROOT, rel)
    pc = os.path.join(CF_ROOT, rel)
    if not (os.path.exists(pe) and os.path.exists(pc)):
        chunks.append("MISSING: %s (ext=%s cf=%s)" % (rel, os.path.exists(pe), os.path.exists(pc)))
        continue
    a = norm(pe, True)
    b = norm(pc, False)
    d = list(difflib.unified_diff(a, b, "EXT", "CF", lineterm="", n=2))
    chunks.append("=" * 100)
    chunks.append(rel + ("   -> IDENTICAL" if not d else "   -> DIFF (%d lines)" % len(d)))
    if d:
        chunks.append("\n".join(d))

text = "\n".join(chunks)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(text)
print("OK saved %s (%d chars)" % (OUT, len(text)))
