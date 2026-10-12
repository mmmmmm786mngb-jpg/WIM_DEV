# -*- coding: utf-8 -*-
"""Заполнить тестовый документ 577-П через COM: ЗаполнитьОтчет (генератор T9573_ТестДанные) и запись.

python fill_doc.py <номер>
"""
import os
import sys
import time

import stand


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    conn = stand.connect()
    ref = stand.doc_by_number(conn, sys.argv[1])
    obj = ref.ПолучитьОбъект()
    t0 = time.time()
    obj.ЗаполнитьОтчет()
    t1 = time.time()
    counts = {n: getattr(obj, f"Раздел{n}").Количество() for n in range(1, 12)}
    obj.ОбменДанными.Загрузка = True
    obj.Записать(conn.РежимЗаписиДокумента.Запись)
    print(f"заполнение {t1 - t0:.1f} s, запись {time.time() - t1:.1f} s")
    print("строк по разделам", counts)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
