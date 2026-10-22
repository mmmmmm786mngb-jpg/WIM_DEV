# -*- coding: utf-8 -*-
"""События журнала регистрации IMDEV-9531 (повтор проведения, ошибка портфеля в потоке) за последние N минут на dev ФО.
    python jr_events.py 15
"""
import datetime
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "1_18"))
import run_1_18_tests as base  # noqa: E402

minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 15
fo = base.stage4.connect("wim_fo")
start = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
table = fo.NewObject("ТаблицаЗначений")
events = fo.NewObject("Массив")
for name in ("IMDEV-9531.ПовторПроведенияПоручения", "IMDEV-9531.ОшибкаПортфеляВПотоке"):
    events.Добавить(name)
flt = fo.NewObject("Структура")
flt.Вставить("ДатаНачала", start)
flt.Вставить("Событие", events)
fo.ВыгрузитьЖурналРегистрации(table, flt)
counts = {}
for i in range(table.Количество()):
    row = table.Получить(i)
    counts[row.Событие] = counts.get(row.Событие, 0) + 1
    if counts[row.Событие] <= 3:
        print(str(row.Дата)[11:19], row.Событие, "|", str(row.Комментарий)[:220].replace("\n", " "))
print("итого:", counts)
