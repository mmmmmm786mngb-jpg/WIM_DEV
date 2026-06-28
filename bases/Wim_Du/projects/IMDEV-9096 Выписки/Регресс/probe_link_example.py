#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path
import sys

REG = Path(__file__).resolve().parent / "Регресс2105"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_mxl import extract_hash_cells, parse_rows

WIDTH = 33

def parse_pp(path):
    vals = extract_hash_cells(path)
    start = next(i for i,v in enumerate(vals) if v=='N' and vals[i+1]=='Операция')
    cols = vals[start:start+WIDTH]
    rows=[]
    i=start+WIDTH
    while i+WIDTH<=len(vals):
        if vals[i].isdigit() and vals[i+1]=='Платежное поручение':
            rows.append(dict(zip(cols, vals[i:i+WIDTH])))
            i+=WIDTH
        else: i+=1
    return rows

for probe in ['8304-000000016', '7227-000000181', '8209', '10061', '8959']:
    print('=== probe', probe)
    for tag, fn in [('BYLO','2105_2105_ПП_было.mxl'),('STALO','2105_2105_ПП_стало.mxl')]:
        hits = [r for r in parse_pp(REG/fn) if probe in (r.get('Ключ выписки','')+r.get('Назначение платежа','')+r.get('NomerScheta',''))]
        print(tag, len(hits))
        for r in hits[:2]:
            print(' ', r.get('Nomer'), r.get('Summa') or r.get('Сумма'), r.get('Klyuch vypiski') if False else r.get('Ключ выписки','')[:70])
    print()

rows = parse_rows(extract_cells(REG/'2105_2105_ВЫПИСКИ_было.mxl'))
for probe in ['8209','10061','8959','8304']:
    hits = [r for r in rows if probe in (r.get('Dogovor','')+r.get('BankSchet','')+str(r.get('raw','')))]
    print('VYPISKI bylo hits', probe, len(hits))
    for r in hits[:3]:
        print(' ', r.get('Data','')[:10], r.get('Dogovor','')[:50], r.get('BankSchet',''))

def extract_cells(path):
    text = path.read_bytes().decode('utf-8', errors='replace')
    return re.findall(r'\{\"#\",\"((?:[^\"\\\\]|\\\\.)*)\"\}', text)
