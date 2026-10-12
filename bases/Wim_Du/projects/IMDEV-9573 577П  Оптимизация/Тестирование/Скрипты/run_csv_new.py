# -*- coding: utf-8 -*-
"""Стенд: выгрузить документ 577-П только потоковой обработкой (СформироватьВыгрузкуCSVПоток.epf).

python run_csv_new.py <номер>
Файлы - в ../Результаты/csv_<номер>/new; печатает время и итог обработки.
"""
import os
import sys
import time

import stand

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
NEW_EPF = os.path.join(TASK, "СформироватьВыгрузкуCSVПоток.epf")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number = sys.argv[1]
    out = os.path.join(TASK, "Тестирование", "Результаты", f"csv_{number}", "new") + "\\"
    os.makedirs(out, exist_ok=True)
    conn = stand.connect()
    ref = stand.doc_by_number(conn, number)
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    processing = conn.ВнешниеОбработки.Создать(NEW_EPF, False, protection)
    params = conn.NewObject("Структура")
    params.Вставить("ДокументСсылка", ref)
    params.Вставить("Каталог", out)
    address = conn.ПоместитьВоВременноеХранилище(None, conn.NewObject("УникальныйИдентификатор"))
    t0 = time.time()
    processing.ВыгрузитьВФоне(params, address)
    print(f"потоковая выгрузка {number}: {time.time() - t0:.1f} s")
    print(conn.ПолучитьИзВременногоХранилища(address).Описание)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
