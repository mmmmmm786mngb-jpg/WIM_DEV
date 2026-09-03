#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IMDEV-9393: интерактивная копия Excel для сценария по потокам.

Копия таблицы ключевых операций, где:
  - колонка "Потоков макс" заменена на "БУДЕТ ПОТОКОВ" (яркая, редактируемая);
  - после предела по договорам добавлены расчётные колонки (голубые) с формулами Excel:
    при изменении БУДЕТ ПОТОКОВ пересчитываются КВО и связанные показатели.

Запуск из корня репозитория:
    python "bases\\Wim_Du\\projects\\IMDEV-9393 ...\\Скрипты\\build_whatif_xlsx.py"
"""

import json
import os
import sys

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_report import (  # noqa: E402
    cell_values, fmt_limit, verdict,
)
from operations_registry import DOGOVOROV_PLAN  # noqa: E402

PROJECT = os.path.join(
    'bases', 'Wim_Du', 'projects',
    'IMDEV-9393 Создать общую таблицу текущей длительности ключевых операций')
IN_JSON = os.path.join(PROJECT, 'Тестирование', 'reports', 'durations_9393.json')
OUT_XLSX = os.path.join(PROJECT, 'Документация', 'KeyOperationsDuration_WhatIf.xlsx')

TARGET_K = DOGOVOROV_PLAN / 1000.0  # 250

# Базовые колонки (как в основном отчёте, но threads_max -> БУДЕТ ПОТОКОВ).
BASE_COLUMNS = [
    ('no', '#', 4),
    ('name', 'Ключевая операция', 40),
    ('periodicity', 'Периодичность', 11),
    ('schedule', 'Время запуска', 18),
    ('object', 'Объект', 28),
    ('source', 'Источник', 12),
    ('threads_now', 'Потоков сейчас', 9),
    ('threads_will', 'БУДЕТ ПОТОКОВ', 10),
    ('min_now', 'Длительность сейчас, мин', 11),
    ('min_max', 'Длительность макс, мин', 10),
    ('min_linear', 'Прогноз x10 линейный, мин', 11),
    ('min_model', 'Прогноз расчётный, мин', 10),
    ('depends', 'Зависит от клиентов', 10),
    ('limit', 'Предел при текущих потоках, тыс.', 12),
    ('window', 'Окно, мин', 8),
]

# Расчётные колонки: формулы Excel, голубая подсветка.
CALC_COLUMNS = [
    ('quota', 'РАСЧЕТНОЕ КВО, тыс. договоров', 12),
    ('dur_will', 'Длительность при БУДЕТ ПОТОКОВ, мин', 12),
    ('speedup', 'Ускорение, раз', 9),
    ('slack', 'Запас до окна, мин', 10),
    ('ok250', 'Выдержит 250 тыс.?', 11),
    ('need250', 'Нужно потоков для 250 тыс.', 11),
]

COMMENT_COL = ('comment', 'Комментарий', 45)

FILL = {
    'crit': PatternFill('solid', fgColor='FDECEA'),
    'warn': PatternFill('solid', fgColor='FFF8E1'),
    'ok': PatternFill('solid', fgColor='EAF7EE'),
    'none': PatternFill('solid', fgColor='E9ECEF'),
    'pending': PatternFill('solid', fgColor='FFE0B2'),
    'grp': PatternFill('solid', fgColor='D6E2F0'),
    'head': PatternFill('solid', fgColor='17365D'),
    'head_will': PatternFill('solid', fgColor='EF6C00'),
    'head_calc': PatternFill('solid', fgColor='0277BD'),
    'will': PatternFill('solid', fgColor='FFEB3B'),
    'will_lock': PatternFill('solid', fgColor='FFF9C4'),
    'calc': PatternFill('solid', fgColor='B3E5FC'),
    'calc_head_row': PatternFill('solid', fgColor='E1F5FE'),
}
THIN = Side(style='thin', color='C8D0DA')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def scales_with_threads(row):
    """Можно ли менять потоки и ждать пропорционального эффекта.

    Параметры:
        row - строка операции из JSON

    Возвращаемое значение:
        Булево - Истина, если потоков сейчас > 1 (есть пул) или в коде
        есть запас по потокам; иначе строка однопоточная.
    """
    if row.get('no_measurement') or row.get('no_forecast'):
        return False
    if not row.get('depends'):
        return False
    if row.get('limit_contracts') is None:
        return False
    now = int(row.get('threads_now') or 1)
    maximum = int(row.get('threads_max') or now)
    reserve = bool(row.get('threads_reserve'))
    return now > 1 or maximum > now or reserve


def to_number(value, numeric_keys, key):
    """Приводит значение ячейки к числу, где это уместно."""
    if key not in numeric_keys:
        return value
    if value in ('-', 'нет замеров', 'не зависит', 'нужен замер', '> 1 000', 'от сделок'):
        return None if key == 'limit' else value
    if isinstance(value, str) and 'дог' in value:
        try:
            return float(value.split()[0].replace(',', '.'))
        except ValueError:
            return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def build():
    with open(IN_JSON, encoding='utf-8') as handle:
        payload = json.load(handle)

    rows = payload['rows']
    meta = payload['meta']
    all_cols = BASE_COLUMNS + CALC_COLUMNS + [COMMENT_COL]
    col_index = {key: index for index, (key, _t, _w) in enumerate(all_cols, start=1)}

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = 'Сценарий по потокам'

    total_cols = len(all_cols)
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    sheet['A1'] = (
        'IMDEV-9393. Интерактивный сценарий по потокам. '
        'Меняйте жёлтую колонку "БУДЕТ ПОТОКОВ" - голубые колонки пересчитаются формулами. '
        'Цель: %.0f тыс. договоров. Сформировано %s.'
        % (TARGET_K, meta['built']))
    sheet['A1'].font = Font(bold=True, size=12, color='17365D')

    sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
    sheet['A2'] = (
        'Формулы (для строк с пулом потоков): '
        'КВО = Предел × (БУДЕТ ПОТОКОВ / Потоков сейчас); '
        'Длительность = Сейчас × (Потоков сейчас / БУДЕТ ПОТОКОВ); '
        'Ускорение = БУДЕТ / Сейчас; '
        'Запас = Окно − Длительность; '
        'Выдержит 250 тыс. = КВО >= 250; '
        'Нужно потоков для 250 тыс. = ОКILING(Потоков сейчас × 250 / Предел). '
        'Однопоточные и строки без предела: КВО = предел (или прочерк), смена потоков не ускоряет.')
    sheet['A2'].font = Font(size=9, color='455A64')
    sheet['A2'].alignment = Alignment(wrap_text=True)
    sheet.row_dimensions[2].height = 48

    header = 4
    for index, (key, title, width) in enumerate(all_cols, start=1):
        cell = sheet.cell(row=header, column=index, value=title)
        cell.font = Font(bold=True, color='FFFFFF', size=10)
        cell.alignment = Alignment(wrap_text=True, vertical='bottom')
        cell.border = BORDER
        if key == 'threads_will':
            cell.fill = FILL['head_will']
        elif key in {k for k, _t, _w in CALC_COLUMNS}:
            cell.fill = FILL['head_calc']
        else:
            cell.fill = FILL['head']
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = sheet.cell(row=header + 1, column=3)
    sheet.row_dimensions[header].height = 36

    numeric_base = {
        'threads_now', 'min_now', 'min_max', 'min_linear', 'min_model', 'limit', 'window',
    }

    line = header
    number = 0
    data_rows = []  # (excel_row, scales, has_limit_number)

    for row in rows:
        line += 1
        if row.get('kind') == 'group':
            cell = sheet.cell(row=line, column=1, value=row['name'])
            cell.font = Font(bold=True, color='17365D', size=11)
            sheet.merge_cells(start_row=line, start_column=1,
                              end_row=line, end_column=total_cols)
            for index in range(1, total_cols + 1):
                sheet.cell(row=line, column=index).fill = FILL['grp']
                sheet.cell(row=line, column=index).border = BORDER
            continue

        number += 1
        mark = verdict(row)
        scales = scales_with_threads(row)
        values = cell_values(row, number)
        # cell_values order matches original COLUMNS; map to our base keys.
        # Original: no,name,periodicity,schedule,object,source,threads_now,threads_max,
        #           min_now,min_max,min_linear,min_model,depends,limit,window,comment
        mapping = {
            'no': values[0],
            'name': values[1],
            'periodicity': values[2],
            'schedule': values[3],
            'object': values[4],
            'source': values[5],
            'threads_now': values[6],
            'threads_will': values[7],  # стартовое = бывший макс / сейчас
            'min_now': values[8],
            'min_max': values[9],
            'min_linear': values[10],
            'min_model': values[11],
            'depends': values[12],
            'limit': values[13],
            'window': values[14],
            'comment': values[15],
        }
        if row.get('real_name'):
            mapping['name'] = '%s\nреальное название: %s' % (row['name'], row['real_name'])

        # Стартовое БУДЕТ ПОТОКОВ = потоков сейчас (сценарий "без изменений").
        # Для масштабируемых можно подставить threads_max как подсказку кода - нет,
        # архитектор сам вводит; стартуем от текущего факта.
        mapping['threads_will'] = int(row.get('threads_now') or 1)

        limit_num = to_number(mapping['limit'], {'limit'}, 'limit')
        has_limit = isinstance(limit_num, (int, float))

        for key, _title, _w in BASE_COLUMNS:
            value = mapping[key]
            if key in numeric_base:
                value = to_number(value, numeric_base, key)
            if key == 'limit' and has_limit:
                value = float(limit_num)
            elif key == 'limit' and not has_limit:
                value = mapping['limit']  # текст прочерка
            cell = sheet.cell(row=line, column=col_index[key], value=value)
            cell.border = BORDER
            cell.alignment = Alignment(
                wrap_text=key in ('name', 'object', 'schedule'),
                vertical='top',
                horizontal='right' if key in (
                    'no', 'threads_now', 'threads_will', 'min_now', 'min_max',
                    'min_linear', 'min_model', 'limit', 'window') else 'left')
            if key == 'threads_will':
                cell.fill = FILL['will'] if scales else FILL['will_lock']
                cell.font = Font(bold=True, size=11, color='E65100')
                cell.number_format = '0'
            elif key == 'name':
                cell.fill = FILL[mark]
                cell.font = Font(bold=True, size=10)
            else:
                cell.fill = FILL[mark]
                cell.font = Font(size=10)
            if key in ('min_now', 'min_max', 'min_linear', 'min_model') and isinstance(value, float):
                cell.number_format = '0.0'
            if key == 'limit' and has_limit:
                cell.number_format = '0.0'

        # --- Формулы расчётных колонок ---
        r = line
        c_now = get_column_letter(col_index['threads_now'])
        c_will = get_column_letter(col_index['threads_will'])
        c_dur = get_column_letter(col_index['min_now'])
        c_lim = get_column_letter(col_index['limit'])
        c_win = get_column_letter(col_index['window'])

        # Условие: есть числовой предел и потоки > 0
        ok_scale = (
            'AND(ISNUMBER({lim}{r}),ISNUMBER({now}{r}),ISNUMBER({will}{r}),'
            '{now}{r}>0,{will}{r}>0)'
            .format(lim=c_lim, now=c_now, will=c_will, r=r))

        formulas = {
            # КВО = предел * будет / сейчас (только если операция масштабируется потоками)
            'quota': (
                '=IF({ok},{lim}{r}*{will}{r}/{now}{r},IF(ISNUMBER({lim}{r}),{lim}{r},"-"))'
                if scales else
                '=IF(ISNUMBER({lim}{r}),{lim}{r},"-")'
            ).format(ok=ok_scale, lim=c_lim, will=c_will, now=c_now, r=r),
            # Длительность падает пропорционально потокам
            'dur_will': (
                '=IF({ok},{dur}{r}*{now}{r}/{will}{r},IF(ISNUMBER({dur}{r}),{dur}{r},"-"))'
                if scales else
                '=IF(ISNUMBER({dur}{r}),{dur}{r},"-")'
            ).format(ok=ok_scale, dur=c_dur, now=c_now, will=c_will, r=r),
            'speedup': (
                '=IF({ok},{will}{r}/{now}{r},1)'
                if scales else
                '=1'
            ).format(ok=ok_scale, will=c_will, now=c_now, r=r),
            'slack': (
                '=IF(AND(ISNUMBER({win}{r}),ISNUMBER({dw}{r})),{win}{r}-{dw}{r},"-")'
                .format(win=c_win, dw=get_column_letter(col_index['dur_will']), r=r)
            ),
            'ok250': (
                '=IF(ISNUMBER({q}{r}),IF({q}{r}>={tgt},"Да","Нет"),"-")'
                .format(q=get_column_letter(col_index['quota']), r=r, tgt=TARGET_K)
            ),
            'need250': (
                '=IF({ok},ROUNDUP({now}{r}*{tgt}/{lim}{r},0),"-")'
                if scales else
                '="-"'
            ).format(ok=ok_scale, now=c_now, lim=c_lim, r=r, tgt=TARGET_K),
        }

        # slack ссылается на dur_will - нужно писать dur_will до slack.
        # Уже так в dict order for py3.7+ but slack formula uses col letter of dur_will
        # which exists. Order of writing cells:
        write_order = ['quota', 'dur_will', 'speedup', 'slack', 'ok250', 'need250']
        # Fix slack formula after we know dur_will column - already uses col_index

        for key in write_order:
            cell = sheet.cell(row=line, column=col_index[key], value=formulas[key])
            cell.fill = FILL['calc']
            cell.border = BORDER
            cell.font = Font(size=10, color='01579B')
            cell.alignment = Alignment(horizontal='right', vertical='top')
            if key in ('quota', 'dur_will', 'speedup', 'slack'):
                cell.number_format = '0.0'

        comment_cell = sheet.cell(
            row=line, column=col_index['comment'], value=mapping['comment'])
        comment_cell.fill = FILL[mark]
        comment_cell.border = BORDER
        comment_cell.alignment = Alignment(wrap_text=True, vertical='top')
        comment_cell.font = Font(size=9)

        data_rows.append((line, scales, has_limit))

    last_data = line
    sheet.auto_filter.ref = 'A%d:%s%d' % (
        header, get_column_letter(total_cols), last_data)

    # Условное форматирование: Выдержит 250 тыс. = Нет -> красный
    ok250_letter = get_column_letter(col_index['ok250'])
    ok_range = '%s%d:%s%d' % (ok250_letter, header + 1, ok250_letter, last_data)
    sheet.conditional_formatting.add(
        ok_range,
        CellIsRule(operator='equal', formula=['"Нет"'],
                   fill=PatternFill('solid', fgColor='FFCDD2'),
                   font=Font(color='B71C1C', bold=True)))
    sheet.conditional_formatting.add(
        ok_range,
        CellIsRule(operator='equal', formula=['"Да"'],
                   fill=PatternFill('solid', fgColor='C8E6C9'),
                   font=Font(color='1B5E20', bold=True)))

    # ------------------------------------------------------------------ Легенда
    legend = book.create_sheet('Как пользоваться')
    legend.column_dimensions['A'].width = 28
    legend.column_dimensions['B'].width = 110
    blocks = [
        ('Интерактивный файл',
         'Это копия таблицы IMDEV-9393 для сценария "что будет, если увеличить потоки". '
         'Основной отчёт KeyOperationsDuration.xlsx не меняйте - правки только здесь.'),
        ('Жёлтая колонка БУДЕТ ПОТОКОВ',
         'Редактируйте число потоков в строке операции. Стартовое значение = "Потоков сейчас". '
         'Для однопоточных операций ячейка бледно-жёлтая: смена потоков физически не ускорит '
         '(в коде нет пула), формулы КВО остаются на уровне текущего предела.'),
        ('Голубые расчётные колонки',
         'Пересчитываются формулами Excel автоматически при изменении БУДЕТ ПОТОКОВ.'),
        ('РАСЧЕТНОЕ КВО, тыс. договоров',
         'Предел при текущих потоках × (БУДЕТ ПОТОКОВ / Потоков сейчас). '
         'Допущение: длительность обратно пропорциональна числу потоков.'),
        ('Длительность при БУДЕТ ПОТОКОВ, мин',
         'Длительность сейчас × (Потоков сейчас / БУДЕТ ПОТОКОВ).'),
        ('Ускорение, раз',
         'БУДЕТ ПОТОКОВ / Потоков сейчас.'),
        ('Запас до окна, мин',
         'Окно − длительность при БУДЕТ ПОТОКОВ. Отрицательное = не укладывается в окно '
         'уже на текущем объёме базы.'),
        ('Выдержит 250 тыс.?',
         'Да, если РАСЧЕТНОЕ КВО >= 250. Подсветка: зелёный / красный.'),
        ('Нужно потоков для 250 тыс.',
         'Сколько потоков нужно, чтобы предел стал не ниже 250 тыс. договоров '
         '(округлено вверх). Для однопоточных - прочерк.'),
        ('Важно',
         'Это оценочная модель для обсуждения с архитектором. Реальное ускорение от потоков '
         'нужно подтверждать замером: упираются блокировки, SQL, внешние сервисы.'),
    ]
    legend['A1'] = 'Как пользоваться интерактивным файлом'
    legend['A1'].font = Font(bold=True, size=14, color='0277BD')
    line = 2
    for title, text in blocks:
        line += 1
        a = legend.cell(row=line, column=1, value=title)
        a.font = Font(bold=True, size=10, color='01579B')
        a.fill = FILL['calc']
        a.alignment = Alignment(vertical='top', wrap_text=True)
        b = legend.cell(row=line, column=2, value=text)
        b.font = Font(size=10)
        b.alignment = Alignment(wrap_text=True, vertical='top')
        legend.row_dimensions[line].height = 48

    os.makedirs(os.path.dirname(OUT_XLSX), exist_ok=True)
    book.save(OUT_XLSX)
    print('What-if XLSX ->', OUT_XLSX)
    print('Data rows:', len(data_rows),
          'scalable:', sum(1 for _r, s, _h in data_rows if s))


if __name__ == '__main__':
    build()
