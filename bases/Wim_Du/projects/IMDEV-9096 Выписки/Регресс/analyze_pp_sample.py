#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

REG = Path(__file__).resolve().parent / "Регресс"
WIDTH = 33
CORE = ("Дата", "Номер", "Сумма", "Плательщик счет", "Получатель счет", "Назначение платежа")

def extract_cells(path):
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)

def parse_primary(vals):
    start = next(i for i,v in enumerate(vals) if v=='N' and vals[i+1]=='Операция')
    cols = vals[start:start+WIDTH]
    rows=[]; i=start+WIDTH
    while i+WIDTH<=len(vals):
        if vals[i].isdigit() and vals[i+1]=='Платежное поручение':
            rows.append(dict(zip(cols, vals[i:i+WIDTH]))); i+=WIDTH
        else: i+=1
    return cols, rows

for name in ['1805_3105_ПП_было.mxl', '1805_3105_ПП_стало.mxl']:
    cols, rows = parse_primary(extract_cells(REG/name))
    print('===', name, 'first 3 payments ===')
    for row in rows[:3]:
        print({c: row.get(c,'')[:60] for c in CORE})

print()
cols_b, rb = parse_primary(extract_cells(REG/'1805_3105_ПП_было.mxl'))
cols_s, rs = parse_primary(extract_cells(REG/'1805_3105_ПП_стало.mxl'))
print('First payment identical:', rb[0] == rs[0] if rb and rs else 'empty')
if rb and rs and rb[0]!=rs[0]:
    for c in cols_b:
        if rb[0].get(c)!=rs[0].get(c):
            print(' diff', c, rb[0].get(c)[:50], '|', rs[0].get(c)[:50])

# sort by core and compare first
from collections import Counter
def ck(r):
    return tuple(r.get(c,'') for c in CORE)
cb = sorted(rb, key=ck)
cs = sorted(rs, key=ck)
same = sum(1 for a,b in zip(cb,cs) if ck(a)==ck(b))
print('Sorted core positional match:', same, 'of', min(len(cb),len(cs)))
