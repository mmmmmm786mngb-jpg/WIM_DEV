# -*- coding: utf-8 -*-
"""Прогон ДиагностикаСервисаДепозитовПИФ на dev ПИФ (WIM_PIF) через внешнее соединение перед передачей на Т-1.

    python run_diag_pif_dev.py [ДатаЗапроса YYYY-MM-DD] [ПользовательСервиса] [--count]

Подключение берется из реестра баз C:\\1c\\Cursor_1c\\WIM_DEV\\.v8-project.json (id wim_pif).
Лог пишется в Тестирование/reports/diag_pif_dev_<дата>.txt.
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

EPF = os.path.join(PROJECT, "Т-1", "ПИФ", "ДиагностикаСервисаДепозитовПИФ.epf")


def main():
    args = [a for a in sys.argv[1:] if a and not a.startswith("--")]
    count = "--count" in sys.argv
    day = datetime.datetime.strptime(args[0], "%Y-%m-%d") if args else datetime.datetime.now()
    user = args[1] if len(args) > 1 else ""
    pif = stand_common.connect("wim_pif")
    obj = pif.ВнешниеОбработки.Создать(EPF, False)
    started = time.time()
    text = obj.СобратьЛог(day, user, True, count)
    out = os.path.join(PROJECT, "Тестирование", "reports",
                       "diag_pif_dev_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("сбор %.1f с, строк %d, файл %s" % (time.time() - started, text.count("\n") + 1, out))


if __name__ == "__main__":
    main()
