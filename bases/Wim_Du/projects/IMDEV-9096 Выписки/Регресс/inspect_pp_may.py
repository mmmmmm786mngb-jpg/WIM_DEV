#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

REG = Path(__file__).resolve().parent / "Регресс"


def cells(path):
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


for name in ["1805_3105_ПП_было.mxl", "0106__0506__ПП_Оригинал4.mxl"]:
    path = REG / name if name.startswith("1805") else Path(__file__).resolve().parent / name
    vals = cells(path)
    for index, value in enumerate(vals):
        if value == "N" and index + 1 < len(vals) and vals[index + 1] == "Операция":
            print("FILE", name, "header at", index)
            print(" cols:", vals[index : index + 15])
            print(" next chunk:", vals[index + 33 : index + 48])
            break
