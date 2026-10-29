# -*- coding: utf-8 -*-
"""Прогон ТестСервисаДепозитовПИФ на dev ФО (wim_fo) против dev ПИФ (http://localhost/wim_pif) перед передачей на Т-1.

    python run_test_pif_deposits_dev.py <метка> [ДатаЗапроса YYYY-MM-DD] [ЧислоВызовов]

Адрес сервиса и учетная запись задаются явно (адрес dev ПИФ, учетная запись из реестра баз, id wim_pif): настройки
обработки загрузки депозитов в dev ФО могут указывать на другие базы. Лог - Тестирование/reports/test_pif_<метка>_<время>.txt.
"""
import datetime
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
STAND = os.path.join(os.path.dirname(PROJECT), "IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО",
                     "Тестирование", "Стенд_МО_ФО")
sys.path.insert(0, STAND)
import stand_common  # noqa: E402

EPF = os.path.join(PROJECT, "Т-1", "ТестДепозитовПИФ", "ТестСервисаДепозитовПИФ.epf")
WSDL = "http://localhost/wim_pif/ws/deposits?wsdl"


def main():
    label = sys.argv[1]
    day = datetime.datetime.strptime(sys.argv[2], "%Y-%m-%d") if len(sys.argv) > 2 else datetime.datetime.now()
    calls = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    pif = stand_common._registry_db("wim_pif")
    fo = stand_common.connect("wim_fo")
    obj = fo.ВнешниеОбработки.Создать(EPF, False)
    started = time.time()
    text = obj.СобратьЛог(stand_common.date_1c(fo, day.replace(hour=0, minute=0, second=0, microsecond=0)), calls,
                          label, WSDL, pif["user"], pif.get("password", ""))
    out = os.path.join(PROJECT, "Тестирование", "reports",
                       "test_pif_%s_%s.txt" % (label, datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("сбор %.1f с, строк %d, файл %s" % (time.time() - started, text.count("\n") + 1, out))
    for line in text.split("\n"):
        if line.startswith("ИТОГ") or "ОШИБКА" in line:
            print(line)


if __name__ == "__main__":
    main()
