#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

REG = Path(__file__).resolve().parent / "Регресс"
WIDTH = 33

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
    return rows

rb = parse_primary(extract_cells(REG/'1805_3105_ПП_было.mxl'))
rs = parse_primary(extract_cells(REG/'1805_3105_ПП_стало.mxl'))

probe = ('18.05.2026', '155114')
in_b = [r for r in rb if r.get('Дата')==probe[0] and r.get('Номер')==probe[1]]
in_s = [r for r in rs if r.get('Дата')==probe[0] and r.get('Номер')==probe[1]]
print('Payment 18.05 #155114 in BYLO', len(in_b), 'STALO', len(in_s))
if in_b:
    print(' BYLO sum', in_b[0].get('Сумма'))

# reverse probe from stalo first
probe2 = ('18.05.2026', '483466')
in_b2 = [r for r in rb if r.get('Дата')==probe2[0] and r.get('Номер')==probe2[1]]
in_s2 = [r for r in rs if r.get('Дата')==probe2[0] and r.get('Номер')==probe2[1]]
print('Payment 18.05 #483466 in BYLO', len(in_b2), 'STALO', len(in_s2))

# operation type counts in full TCH
def all_ops(vals):
    start = next(i for i,v in enumerate(vals) if v=='N' and vals[i+1]=='Операция')
    cols = vals[start:start+WIDTH]
    ops=[]
    i=start+WIDTH
    while i+WIDTH<=len(vals):
        if vals[i].isdigit():
            row=dict(zip(cols, vals[i:i+WIDTH]))
            ops.append(row.get('Операция',''))
            i+=WIDTH
        else: i+=1
    return ops

from collections import Counter
ob = Counter(all_ops(extract_cells(REG/'1805_3105_ПП_было.mxl')))
os_ = Counter(all_ops(extract_cells(REG/'1805_3105_ПП_стало.mxl')))
print('Operation types BYLO:', dict(ob))
print('Operation types STALO:', dict(os_))
print('Op diff:', dict((ob-os_)+(os_-ob)))
