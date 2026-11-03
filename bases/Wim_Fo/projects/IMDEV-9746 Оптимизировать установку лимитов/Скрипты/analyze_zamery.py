"""IMDEV-9746. Анализ замеров РаспространениеПравилЛимитов* из выгрузок регистра ЗамерыВремени (xlsx).

Запуск: python analyze_zamery.py <файл.xlsx> [<файл2.xlsx> ...]
Колонки выгрузки: Ключевая операция, Дата начала замера, Номер сеанса, ..., Время выполнения в секундах,
Вес замера, Комментарий (JSON с полем ДопИнф), Дата записи, Дата окончания, Пользователь, ...
Нужен openpyxl.
"""
import collections
import json
import re
import statistics as st
import sys
from datetime import datetime

import openpyxl

TOP = 'Распространение правил лимитов'
STEP_SEARCH = TOP + '. поиск новых клиентов'
STEP_CREATE = TOP + '. создание установок'
STEP_MAIL = TOP + '. рассылка'


def dop_inf(row):
    try:
        text = json.loads(row[6]).get('ДопИнф', '')
    except (TypeError, ValueError):
        return {}
    result = {}
    for part in text.split(';'):
        if ':' in part:
            key, value = part.split(':', 1)
            value = value.strip()
            result[key.strip()] = int(value) if re.fullmatch(r'\d+', value) else value
    return result


def quantile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p * len(values)))] if values else 0


def load(path):
    sheet = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))[1:]
    return rows, [r for r in rows if str(r[0]).startswith(TOP)]


def report(path):
    all_rows, rows = load(path)
    print('#' * 10, path, '- замеров операции:', len(rows))
    dates = [datetime.strptime(r[7], '%d.%m.%Y %H:%M:%S') for r in rows]
    print('Период:', min(dates), '-', max(dates))
    print('Ошибки:', collections.Counter(r[11] for r in rows), 'Пользователи:', collections.Counter(r[9] for r in rows))

    by_key = collections.defaultdict(list)
    for r in rows:
        by_key[r[0]].append(r)
    for key, items in by_key.items():
        t = [r[4] for r in items]
        print(f'{key}: n={len(t)} сумма={sum(t):.0f} ср={st.mean(t):.2f} мед={st.median(t):.2f} '
              f'p95={quantile(t, .95):.2f} макс={max(t):.2f}')

    days = collections.defaultdict(lambda: [0, 0.0, 0, 0.0, 0.0, 0.0])
    for r in rows:
        day = days[r[7][:10]]
        if r[0] == TOP:
            day[0] += 1
            day[1] += r[4]
            day[2] += dop_inf(r).get('Распространено', 0)
        elif r[0] == STEP_CREATE:
            day[3] += r[4]
        elif r[0] == STEP_SEARCH:
            day[4] += r[4]
        elif r[0] == STEP_MAIL:
            day[5] += r[4]
    print('День        Запусков  Всего,с  Пар  Создание  Поиск  Рассылка  с/пару')
    for d in sorted(days, key=lambda x: datetime.strptime(x, '%d.%m.%Y')):
        v = days[d]
        per_pair = v[3] / v[2] if v[2] else 0
        print(f'{d} {v[0]:8} {v[1]:8.1f} {v[2]:4} {v[3]:9.1f} {v[4]:6.1f} {v[5]:9.1f} {per_pair:7.2f}')

    created = [r for r in by_key[STEP_CREATE] if dop_inf(r).get('Распространено', 0) > 0]
    per_pair = [r[4] / dop_inf(r)['Распространено'] for r in created]
    if per_pair:
        print(f'Создание установок на пару: n={len(per_pair)} мед={st.median(per_pair):.3f} '
              f'p90={quantile(per_pair, .9):.3f} макс={max(per_pair):.2f}')
        xs = [dop_inf(r)['Распространено'] for r in created]
        ys = [r[4] for r in created]
        if len(set(xs)) > 1:
            mx, my = st.mean(xs), st.mean(ys)
            b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
            print(f'Линейная модель: создание = {my - b * mx:.3f} + {b:.3f} * пар')

    # Пересечение шага создания установок с другими ключевыми операциями базы (конкуренция за данные)
    for other in ['Действующие лимиты', 'Проверка', 'Обработать пакет']:
        others = [r for r in all_rows if r[0] == other]
        overlap, alone = [], []
        for c, value in zip(created, per_pair):
            (overlap if any(o[1] < c[8] and o[8] > c[1] for o in others) else alone).append(value)
        if overlap and alone:
            print(f'Пересечение с "{other}": n={len(overlap)} мед={st.median(overlap):.2f} ср={st.mean(overlap):.2f}; '
                  f'без пересечения n={len(alone)} мед={st.median(alone):.2f} ср={st.mean(alone):.2f}')

    print('Самые долгие запуски:')
    for r in sorted(by_key[TOP], key=lambda r: -r[4])[:5]:
        print('  ', r[7], r[4], json.loads(r[6]).get('ДопИнф'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for file_path in sys.argv[1:]:
        report(file_path)
