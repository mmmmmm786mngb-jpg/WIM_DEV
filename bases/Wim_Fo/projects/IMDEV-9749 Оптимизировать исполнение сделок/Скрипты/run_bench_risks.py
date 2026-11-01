#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Регрессия четырех сценариев исполнения: РЕПО, РЕПО с активами, сумма, два портфеля, затем 6 потоков."""

import datetime
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

STAND = (
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Fo\projects"
    r"\IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО"
    r"\Тестирование\Стенд_МО_ФО"
)
sys.path.insert(0, STAND)

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
EPF = os.path.join(PROJECT, "Тестирование", "BenchParallelExecution.epf")
REPORTS = os.path.join(PROJECT, "Тестирование", "reports")


def structure(conn, values):
    result = conn.NewObject("Структура")
    for key, value in values.items():
        result.Вставить(key, value)
    return result


def main():
    import stand_common as stand

    conn = stand.connect("wim_fo")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORTS, "bench_risks_%s.txt" % stamp)
    call = structure(conn, {
        "ЭтоВнешняяОбработка": True,
        "ИмяОбработки": EPF,
        "ИмяМетода": "ПрогнатьРиски",
        "ПараметрыВыполнения": structure(conn, {
            "ПутьЛога": path,
            "Маркер": "TRSK",
            "ПутьОбработки": EPF,
        }),
    })
    address = conn.ПоместитьВоВременноеХранилище("", conn.NewObject("УникальныйИдентификатор"))
    args = conn.NewObject("Массив")
    args.Добавить(call)
    args.Добавить(address)
    job = conn.ФоновыеЗадания.Выполнить(
        "ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", args, None, "TRSK risks")
    uid = job.УникальныйИдентификатор
    started = time.time()
    print("job started", flush=True)
    active = conn.СостояниеФоновогоЗадания.Активно
    while time.time() - started < 1800:
        job = conn.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != active:
            break
        time.sleep(5)
    print("state", conn.String(job.Состояние), "after %.0f s" % (time.time() - started), flush=True)
    if job.ИнформацияОбОшибке:
        print(conn.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке), flush=True)
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as handle:
            print(handle.read(), flush=True)
        print("REPORT", path, flush=True)
    else:
        print("log file missing", path, flush=True)


if __name__ == "__main__":
    main()
