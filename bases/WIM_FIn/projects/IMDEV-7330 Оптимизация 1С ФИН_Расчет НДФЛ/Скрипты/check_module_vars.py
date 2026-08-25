#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка объявлений переменных модуля (Перем) и прочих строк вне процедур."""

import os
import re

EXT_ROOT = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects",
    "IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ",
    "Расширения", "NDFL_RDU")
CF_ROOT = r"C:\1c\Cursor_1c\WORK\WIM_FIn\src\cf"

RELS = [
    r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ManagerModule.bsl",
    r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ObjectModule.bsl",
    r"DataProcessors\ФормированиеНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl",
    r"Documents\НачислениеНДФЛПоПортфелю\Ext\ObjectModule.bsl",
    r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ManagerModule.bsl",
    r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ObjectModule.bsl",
    r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ManagerModule.bsl",
    r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ObjectModule.bsl",
    r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl",
]

PEREM = re.compile(r"^\s*Перем\s+(.+?);", re.IGNORECASE)

lines_out = []
for rel in RELS:
    for label, root in (("EXT", EXT_ROOT), ("CF ", CF_ROOT)):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            lines_out.append("%s %s : FILE NOT FOUND" % (label, rel))
            continue
        with open(p, "r", encoding="utf-8-sig") as f:
            txt = f.read()
        perems = PEREM.findall(txt)
        lines_out.append("%s %s" % (label, rel))
        for v in perems:
            lines_out.append("      Перем %s" % v.strip())
    lines_out.append("-" * 90)

out = "\n".join(lines_out)
path = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects",
    "IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ", "Документация", "imdev7330_module_vars.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write(out)
print("OK saved %s" % path)
