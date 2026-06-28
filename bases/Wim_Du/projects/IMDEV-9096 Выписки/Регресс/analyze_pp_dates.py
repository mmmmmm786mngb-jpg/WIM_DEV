#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from collections import Counter
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

def count_all(vals):
    start = next(i for i,v in enumerate(vals) if v=='N' and vals[i+1]=='Операция')
    n=0; i=start+WIDTH
    while i+WIDTH<=len(vals):
        if vals[i].isdigit(): n+=1; i+=WIDTH
        else: i+=1
    return n

rb = parse_primary(extract_cells(REG/'1805_3105_ПП_было.mxl'))
rs = parse_primary(extract_cells(REG/'1805_3105_ПП_стало.mxl'))
print('Payments per date BYLO:')
for d,c in sorted(Counter(r.get('Дата','') for r in rb).items())[:8]:
    print(' ', d, c)
print('... total dates', len(Counter(r.get('Дата','') for r in rb)))
print('Payments per date STALO first 8:')
for d,c in sorted(Counter(r.get('Дата','') for r in rs).items())[:8]:
    print(' ', d, c)

by_date_b = Counter(r.get('Дата','') for r in rb)
by_date_s = Counter(r.get('Дата','') for r in rs)
print('Date count diffs:')
for d in sorted(set(by_date_b)|set(by_date_s)):
    if by_date_b[d]!=by_date_s[d]:
        print(f'  {d}: BYLO={by_date_b[d]} STALO={by_date_s[d]}')

print('All TCH rows:', count_all(extract_cells(REG/'1805_3105_ПП_было.mxl')), count_all(extract_cells(REG/'1805_3105_ПП_стало.mxl')))
