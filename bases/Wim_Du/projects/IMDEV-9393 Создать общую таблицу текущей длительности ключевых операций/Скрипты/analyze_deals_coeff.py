#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Анализ дневной статистики сделок: коэффициент роста к базе договоров."""

import collections
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calc_durations as cd
from operations_registry import DOGOVOROV_PLAN, DOGOVOROV_SEYCHAS, OPERATIONS


def load_all():
    prod = cd.load(cd.PROD_XLSX)
    if os.path.isfile(cd.EXTRA_XLSX):
        cd.merge_records(prod, cd.load(cd.EXTRA_XLSX))
    return prod


def daily_weights(records, key, min_weight=0):
    by_day = collections.defaultdict(lambda: {'w': 0.0, 'sec': 0.0, 'n': 0})
    for record in records.get(key, []):
        if record['error'] or not record.get('local'):
            continue
        if record['weight'] < min_weight:
            continue
        day = record['local'].date()
        by_day[day]['w'] += record['weight']
        by_day[day]['sec'] += record['sec']
        by_day[day]['n'] += 1
    return by_day


def summarize(name, weights):
    if not weights:
        print('  no data')
        return
    print(
        '  deals/day: min=%.0f p25=%.0f median=%.0f mean=%.0f p75=%.0f max=%.0f'
        % (
            min(weights),
            statistics.quantiles(weights, n=4)[0] if len(weights) >= 4 else weights[0],
            statistics.median(weights),
            statistics.mean(weights),
            statistics.quantiles(weights, n=4)[2] if len(weights) >= 4 else weights[-1],
            max(weights),
        )
    )
    # Коэффициент "нагрузки" относительно медианы: max/median и mean/median.
    med = statistics.median(weights)
    if med > 0:
        print(
            '  vs median: mean/med=%.2f  max/med=%.2f  p75/med=%.2f'
            % (
                statistics.mean(weights) / med,
                max(weights) / med,
                (statistics.quantiles(weights, n=4)[2] / med) if len(weights) >= 4 else 1.0,
            )
        )


def main():
    prod = load_all()
    print('BASE now=%d plan=%d kratnost=%.1f' % (DOGOVOROV_SEYCHAS, DOGOVOROV_PLAN, DOGOVOROV_PLAN / DOGOVOROV_SEYCHAS))

    for op_id in ('ispolnenie_sdelok', 'zagruzka_sdelok'):
        spec = [item for item in OPERATIONS if item.get('id') == op_id][0]
        print('=' * 72)
        print(op_id)
        print(spec['name'])

        # 1) По каждому ключу - сумма весов за день
        for key in spec['keys']:
            by_day = daily_weights(prod, key, min_weight=0)
            days = sorted(by_day)
            weights = [by_day[day]['w'] for day in days]
            print('-' * 72)
            print('KEY:', key)
            print('days=%d  %s .. %s' % (len(days), days[0] if days else '-', days[-1] if days else '-'))
            summarize(key, weights)
            print('last 20 days:')
            for day in days[-20:]:
                block = by_day[day]
                print(
                    '  %s  deals=%7.0f  sec=%7.0f  n=%3d'
                    % (day, block['w'], block['sec'], block['n'])
                )

        # 2) Отобранные прогоны (как в calc_durations)
        picked = cd.select(prod, spec)
        print('-' * 72)
        print('SELECTED contour runs:', len(picked))
        by_day = collections.defaultdict(list)
        for record in picked:
            if record.get('local'):
                by_day[record['local'].date()].append(record)

        rows = []
        for day in sorted(by_day):
            best = max(by_day[day], key=lambda item: item['weight'])
            intensity = best['weight'] / DOGOVOROV_SEYCHAS
            rows.append({
                'day': day,
                'deals': best['weight'],
                'sec': best['sec'],
                'intensity': intensity,
            })
            print(
                '  %s  deals=%7.0f  sec=%7.0f  deals_per_contract=%.4f'
                % (day, best['weight'], best['sec'], intensity)
            )

        if not rows:
            continue

        deals = [row['deals'] for row in rows]
        ints = [row['intensity'] for row in rows]
        med_deals = statistics.median(deals)
        med_int = statistics.median(ints)
        mean_int = statistics.mean(ints)
        # Наивный x10 от медианы сделок дня
        naive_250 = med_deals * 10
        # Через интенсивность на текущую базу 25 тыс.
        via_int_250 = med_int * DOGOVOROV_PLAN
        # Если интенсивность не константа: регрессия deals ~ a + b*??? у нас нет ряда базы.
        # Коэффициент к наивному x10: K = via_int / naive = (med_int*250k)/(med_deals*10)
        # При med_deals ~= med_int*25k получим K~1.
        coef_k = via_int_250 / naive_250 if naive_250 else None
        print('SUMMARY intensity (deals / %d contracts):' % DOGOVOROV_SEYCHAS)
        print(
            '  median=%.4f  mean=%.4f  min=%.4f  max=%.4f'
            % (med_int, mean_int, min(ints), max(ints))
        )
        print('  median deals/day=%.0f' % med_deals)
        print('  naive deals@250k = median_deals * 10 = %.0f' % naive_250)
        print('  via intensity     = median_int * 250000 = %.0f' % via_int_250)
        print('  K = via_intensity / (median_deals*10) = %.3f' % coef_k)
        print(
            '  NOTE: K~1 means median deals already ≈ intensity*25k; '
            'constant intensity => deals grow exactly x10 with contracts.'
        )
        # Разброс интенсивности как "нелинейность дня"
        if med_int > 0:
            print(
                '  day-to-day spread: max_int/med_int=%.2f  mean_int/med_int=%.2f'
                % (max(ints) / med_int, mean_int / med_int)
            )
        # Корреляция sec vs deals (насколько время растёт со сделками)
        if len(rows) >= 5:
            xs = [row['deals'] for row in rows]
            ys = [row['sec'] for row in rows]
            mean_x = statistics.mean(xs)
            mean_y = statistics.mean(ys)
            num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
            den = (
                sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys)
            ) ** 0.5
            corr = num / den if den else 0
            # простой наклон sec = a + b*deals
            den_b = sum((x - mean_x) ** 2 for x in xs)
            slope = num / den_b if den_b else 0
            intercept = mean_y - slope * mean_x
            print('  corr(deals, sec)=%.3f  sec ≈ %.1f + %.4f * deals' % (corr, intercept, slope))
            # Экстраполяция времени на deals@250k через интенсивность
            deals_250 = via_int_250
            sec_250 = intercept + slope * deals_250
            print(
                '  extrapolate sec@deals250k(intensity): %.0f s (%.1f min)'
                % (sec_250, sec_250 / 60)
            )
            sec_naive = intercept + slope * naive_250
            print(
                '  extrapolate sec@deals*10: %.0f s (%.1f min)'
                % (sec_naive, sec_naive / 60)
            )


if __name__ == '__main__':
    main()
