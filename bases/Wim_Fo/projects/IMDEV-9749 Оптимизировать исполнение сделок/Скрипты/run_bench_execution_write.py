#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Запуск замера ОбновитьДанныеИсполнения с записью (BenchExecutionWrite) фоновым заданием на сервере ФО.

Параметр командной строки - число поручений в группе (по умолчанию 1000, групп три).
"""

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
import stand_common as stand  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
EPF = os.path.join(PROJECT, "Тестирование", "BenchExecutionWrite.epf")
LOG = os.path.join(
    PROJECT, "Тестирование", "reports",
    "bench_execution_write_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
)


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    print("EPF", EPF, flush=True)
    print("LOG", LOG, flush=True)
    conn = stand.connect("wim_fo")
    call = conn.NewObject("Структура")
    inner = conn.NewObject("Структура")
    inner.Вставить("ПутьЛога", LOG)
    inner.Вставить("Количество", count)
    call.Вставить("ЭтоВнешняяОбработка", True)
    call.Вставить("ИмяОбработки", EPF)
    call.Вставить("ИмяМетода", "ВыполнитьТест")
    call.Вставить("ПараметрыВыполнения", inner)
    address = conn.ПоместитьВоВременноеХранилище("", conn.NewObject("УникальныйИдентификатор"))
    args = conn.NewObject("Массив")
    args.Добавить(call)
    args.Добавить(address)
    job = conn.ФоновыеЗадания.Выполнить(
        "ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки",
        args,
        None,
        "TEXECW",
    )
    uid = job.УникальныйИдентификатор
    print("job started", flush=True)
    active = conn.СостояниеФоновогоЗадания.Активно
    deadline = time.time() + 2400
    state = None
    while time.time() < deadline:
        job = conn.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        state = job.Состояние
        if state != active:
            break
        time.sleep(5)
    print("state", conn.String(state), flush=True)
    if job.ИнформацияОбОшибке:
        print(conn.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке), flush=True)
    if os.path.exists(LOG):
        print("REPORT", LOG, flush=True)
        with open(LOG, encoding="utf-8-sig") as handle:
            print(handle.read(), flush=True)
    else:
        print("log file missing", flush=True)


if __name__ == "__main__":
    main()
