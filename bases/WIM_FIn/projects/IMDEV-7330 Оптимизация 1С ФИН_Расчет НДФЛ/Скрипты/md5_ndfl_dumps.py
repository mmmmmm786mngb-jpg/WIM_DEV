#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MD5 of NDFL xlsx dumps old / new2 / new3."""

import hashlib
from pathlib import Path

BASE = Path(r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 НовыеТесты")
names = [
    "НДФЛ_Портфели_27292.xlsx",
    "НДФЛ_Портфели_27292_ПоНовому2.xlsx",
    "НДФЛ_Портфели_27292_ПоНовому3.xlsx",
    "НДФЛ_Управление_27292.xlsx",
    "НДФЛ_Управление_27292_ПоНовому2.xlsx",
    "НДФЛ_Управление_27292_ПоНовому3.xlsx",
]


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


for n in names:
    p = BASE / n
    print(f"{p.stat().st_size:10d}  {md5(p)}  {n}")
