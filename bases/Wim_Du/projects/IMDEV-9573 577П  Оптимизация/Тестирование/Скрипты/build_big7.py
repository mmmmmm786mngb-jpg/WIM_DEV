# -*- coding: utf-8 -*-
"""Документ 577-П с большим разделом 7 без реального заполнения: только раздел 7, строки дает генератор
T9573_ТестДанные (КоличествоСтрок). Печатает время генерации и записи, память процесса.

python build_big7.py <номер> <строк>
"""
import os
import sys
import time

import psutil

import stand


def mem():
    return round(psutil.Process().memory_info().private / 2**20)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number, rows = sys.argv[1], int(sys.argv[2])
    c = stand.connect()
    c.ХранилищеОбщихНастроек.Сохранить("T9573", "КоличествоСтрок", rows)
    obj = getattr(c.Документы, stand.DOC).СоздатьДокумент()
    obj.Заполнить(None)
    obj.Дата = stand.date_1c(c, "2026-10-08T12:00:00")
    obj.Номер = number
    obj.УправляющаяКомпания = stand.uk(c)
    obj.НачалоПериода = stand.date_1c(c, "2026-06-01T00:00:00")
    obj.КонецПериода = stand.date_1c(c, "2026-06-30T00:00:00")
    obj.ПредставлениеПериода = "июнь 2026"
    for n in range(1, 12):
        setattr(obj, f"ВыгружатьРаздел{n}", n == 7)
    print("start, процесс", mem(), "МБ", flush=True)
    t = time.time()
    obj.ЗаполнитьОтчет()
    print(f"заполнение {time.time() - t:.1f} с, Раздел7 = {obj.Раздел7.Количество()}, процесс {mem()} МБ", flush=True)
    t = time.time()
    obj.Записать()
    print(f"запись {time.time() - t:.1f} с, процесс {mem()} МБ", flush=True)
    print("ссылка", c.ПолучитьНавигационнуюСсылку(obj.Ссылка), flush=True)
    c.ХранилищеОбщихНастроек.Сохранить("T9573", "КоличествоСтрок", 2000)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc, flush=True)
    sys.stdout.flush()
    os._exit(0)
