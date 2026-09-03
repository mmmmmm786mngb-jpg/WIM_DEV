#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разведка: распределение веса и длительности по ключевым операциям.

Нужно, чтобы выбрать порог "полного объёма" для каждой операции
и понять, в каком контуре (регламентное задание или ручной запуск)
операция реально работает на боевом объёме.
"""

import collections
import datetime
import json
import re

import openpyxl

SRC = r'bases\Wim_Du\projects\IMDEV-9391 ПРоверить ключевые операции замеры\ЗамерыВремени.xlsx'
OUT = r'drafts\9393_msg\volume_probe.txt'

# Операции, по которым нужно посмотреть верх распределения по весу.
PROBE = [
    'Д у. регламентные операции.2. вечерние операции',
    'Д у. регламентные операции.1. утренние операции',
    'Д у. загрузка сделок. получение tibco. фоновое выполнение',
    'Д у. загрузка сделок. создание сделок. фоновое выполнение',
    'Д у. загрузка сделок. получение tibco. фоновое выполнение розничное д у',
    'Д у. загрузка сделок. создание сделок. фоновое выполнение розничное д у',
    'Д у. исполнение сделок т+n. исполнение в потоках. фоновое выполнение_ потоковое исполнение сделок',
    'Д у. исполнение сделок т+n. исполнение в потоках. фоновое выполнение потоковое_ т минус1',
    'Д у. пакетный отчет брокера. получение s q l. фоновое выполнение',
    'Д у. пакетный отчет брокера. создание операций. фоновое выполнение',
    'Д у. загрузка выписок. получение w e b_ v t b. заполнить w e b_ v t b',
    'Д у. загрузка выписок. разбор выписок. заполнить w e b_ v t b',
    'Д у. загрузка выписок. создание документов. разобрать отмеченные',
    'Д у. сверка денежных средств. сверка. фоновое выполнение',
    'Д у. сверка денежных средств е р с. сверка. фоновое выполнение',
    'Д у. синхронизация н с и. фоновое выполнение',
    'Д у. синхронизация н с и. фоновое выполнение поручения',
    'Д у. загрузка котировок. получение tibco. фоновое выполнение',
    'Д у. загрузка котировок. создание котировок. фоновое выполнение',
    'Д у. контроль котировок. отчет. фоновое выполнение',
    'Д у. сверка. сделок с отчетом брокера. фоновое выполнение',
    'Д у. сверка. сделок с отчетом брокера. фоновое проведение',
    'Д у. сверка ц б. сверка. фоновое выполнение',
    'Д у. расторжение договоров р д у. фоновое договоры из д о к расторжению',
    'Д у. начисление вознаграждения р д у. начисление. ручной',
    'Д у. расчет вознаграждения р д у. расчет. фоновое выполнение',
    'Отчет управляющего д у 482 п',
    'Выгрузка отчетов управляющего 482 п',
    'Д у. экспорт h n w i. выгрузка. фоновое выполнение',
    'Д у. распределение доходов. создание операций.вн распределение доходов по ценным бумагам',
    'Д у. сверка. отрицательные остатки на р с. формирование отчета. ручной',
]

EPOCH = datetime.datetime(1, 1, 1)


def to_dt(v):
    """1С-дата в миллисекундах от 0001-01-01 -> datetime."""
    try:
        return EPOCH + datetime.timedelta(seconds=float(v) / 1000.0)
    except (TypeError, ValueError, OverflowError):
        return None


def parse_local(v):
    if isinstance(v, datetime.datetime):
        return v
    s = str(v).strip()
    for fmt in ('%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M'):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def dop_inf(comment):
    """Достаёт ДопИнф из JSON-комментария замера."""
    if not comment:
        return ''
    try:
        return str(json.loads(str(comment)).get('ДопИнф', ''))
    except (ValueError, AttributeError):
        m = re.search(r'"ДопИнф"\s*:\s*"(.*?)"', str(comment))
        return m.group(1) if m else str(comment)[:120]


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    ws = wb['TDSheet']
    rows = ws.iter_rows(values_only=True)
    next(rows)

    data = collections.defaultdict(list)
    for r in rows:
        ko = r[0]
        if not ko:
            continue
        key = str(ko).strip()
        if key not in PROBE:
            continue
        try:
            sec = float(r[4])
        except (TypeError, ValueError):
            continue
        try:
            weight = float(r[5]) if r[5] is not None else 0.0
        except (TypeError, ValueError):
            weight = 0.0
        data[key].append({
            'sec': sec,
            'w': weight,
            'start': to_dt(r[1]),
            'local': parse_local(r[10]),
            'user': str(r[9] or ''),
            'err': str(r[11] or '').strip(),
            'inf': dop_inf(r[6]),
        })

    out = []
    for key in PROBE:
        recs = data.get(key, [])
        out.append('=' * 100)
        out.append('OP: %s   (N=%d)' % (key, len(recs)))
        if not recs:
            out.append('  НЕТ ДАННЫХ')
            continue
        users = collections.Counter(x['user'] for x in recs)
        out.append('  users: %s' % ', '.join('%s=%d' % (u, c) for u, c in users.most_common(4)))
        hours = collections.Counter(x['local'].hour for x in recs if x['local'])
        out.append('  hours(local, top): %s' % sorted(hours.items(), key=lambda kv: -kv[1])[:6])
        top = sorted(recs, key=lambda x: -x['w'])[:8]
        out.append('  --- TOP-8 по весу ---')
        for x in top:
            out.append('   w=%-10.0f sec=%-11.2f loc=%-20s err=%-3s %s'
                       % (x['w'], x['sec'],
                          x['local'].strftime('%d.%m %H:%M:%S') if x['local'] else '-',
                          x['err'], x['inf'][:95]))
        slow = sorted(recs, key=lambda x: -x['sec'])[:5]
        out.append('  --- TOP-5 по длительности ---')
        for x in slow:
            out.append('   sec=%-11.2f w=%-10.0f loc=%-20s %s'
                       % (x['sec'], x['w'],
                          x['local'].strftime('%d.%m %H:%M:%S') if x['local'] else '-',
                          x['inf'][:95]))

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('OK ->', OUT)


if __name__ == '__main__':
    main()
