# -*- coding: utf-8 -*-
"""Стенд: выгрузить документ 577-П прежним алгоритмом (T9573_СтараяВыгрузкаCSV.epf) и потоковой
обработкой (СформироватьВыгрузкуCSVПоток.epf) в COM-сеансе, затем сравнить каталоги compare_csv.py.

python run_csv_compare.py <номер>
"""
import os
import subprocess
import sys
import time

import stand

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
OLD_EPF = os.path.join(TASK, "Тестирование", "Обработки", "T9573_СтараяВыгрузкаCSV.epf")
NEW_EPF = os.path.join(TASK, "СформироватьВыгрузкуCSVПоток.epf")


def processing(conn, path):
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    return conn.ВнешниеОбработки.Создать(path, False, protection)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number = sys.argv[1]
    base = os.path.join(TASK, "Тестирование", "Результаты", f"csv_{number}")
    dir_old, dir_new = os.path.join(base, "old") + "\\", os.path.join(base, "new") + "\\"
    for d in (dir_old, dir_new):
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))

    conn = stand.connect()
    ref = stand.doc_by_number(conn, number)

    t0 = time.time()
    times = processing(conn, OLD_EPF).Выгрузить(ref, dir_old)
    t_old = time.time() - t0
    print(f"прежняя выгрузка: {t_old:.1f} s")
    print("  по разделам, мс:", times.replace("\n", "; "))

    params = conn.NewObject("Структура")
    params.Вставить("ДокументСсылка", ref)
    params.Вставить("Каталог", dir_new)
    address = conn.ПоместитьВоВременноеХранилище(None, conn.NewObject("УникальныйИдентификатор"))
    t0 = time.time()
    processing(conn, NEW_EPF).ВыгрузитьВФоне(params, address)
    t_new = time.time() - t0
    result = conn.ПолучитьИзВременногоХранилища(address)
    print(f"потоковая выгрузка: {t_new:.1f} s")
    print("  ", result.Описание.splitlines()[0])

    report = os.path.join(base, "сравнение.txt")
    sys.stdout.flush()
    code = subprocess.call([sys.executable, "-X", "utf8", os.path.join(HERE, "compare_csv.py"), dir_old, dir_new, report])
    with open(report, "a", encoding="utf-8") as f:
        f.write(f"\nВремя: прежняя {t_old:.1f} s, потоковая {t_new:.1f} s\nПрежняя по разделам, мс: {times}\n")
    print("код сравнения", code)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
