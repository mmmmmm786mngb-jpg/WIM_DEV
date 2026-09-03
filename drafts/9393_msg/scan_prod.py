#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сводка по выгрузке РС.ЗамерыВремени: какие ключевые операции есть и их статистика."""

import collections
import statistics

import openpyxl

SRC = r'bases\Wim_Du\projects\IMDEV-9391 ПРоверить ключевые операции замеры\ЗамерыВремени.xlsx'
OUT = r'drafts\9393_msg\prod_coverage.txt'


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    ws = wb['TDSheet']
    rows = ws.iter_rows(values_only=True)
    next(rows)

    groups = collections.defaultdict(list)
    total = 0
    for r in rows:
        ko = r[0]
        if not ko:
            continue
        total += 1
        try:
            sec = float(r[4])
        except (TypeError, ValueError):
            sec = None
        try:
            weight = float(r[5]) if r[5] is not None else None
        except (TypeError, ValueError):
            weight = None
        groups[str(ko).strip()].append((sec, weight, r[10], r[9], r[11]))

    lines = ['TOTAL ROWS: %d   DISTINCT OPS: %d' % (total, len(groups)), '']
    summary = []
    for ko, vals in groups.items():
        secs = sorted(v[0] for v in vals if v[0] is not None)
        weights = [v[1] for v in vals if v[1] is not None]
        dates = sorted(str(v[2]) for v in vals if v[2])
        users = collections.Counter(str(v[3]) for v in vals if v[3])
        errs = sum(1 for v in vals if str(v[4]).strip() == 'Да')
        p95 = secs[min(len(secs) - 1, int(round(0.95 * (len(secs) - 1))))] if secs else None
        summary.append({
            'op': ko,
            'n': len(vals),
            'min': min(secs) if secs else None,
            'med': statistics.median(secs) if secs else None,
            'p95': p95,
            'max': max(secs) if secs else None,
            'wmed': statistics.median(weights) if weights else None,
            'wmax': max(weights) if weights else None,
            'd1': dates[0] if dates else '',
            'd2': dates[-1] if dates else '',
            'users': ', '.join('%s(%d)' % (u, c) for u, c in users.most_common(3)),
            'err': errs,
        })

    summary.sort(key=lambda x: -x['n'])
    for s in summary:
        lines.append(
            'N=%-5d min=%-10s med=%-10s p95=%-10s max=%-10s wmed=%-9s wmax=%-9s err=%-3d | %s\n'
            '        period %s .. %s | users: %s'
            % (s['n'],
               _f(s['min']), _f(s['med']), _f(s['p95']), _f(s['max']),
               _f(s['wmed']), _f(s['wmax']), s['err'], s['op'],
               s['d1'], s['d2'], s['users'])
        )

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('OK, ops:', len(groups), 'rows:', total, '->', OUT)


def _f(v):
    return '-' if v is None else ('%.3f' % v)


if __name__ == '__main__':
    main()
