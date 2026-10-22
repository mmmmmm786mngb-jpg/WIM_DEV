# -*- coding: utf-8 -*-
"""Прогон диагностики T9531_ДанныеТ1 на dev ФО через внешнее соединение (проверка перед передачей на Т-1).

    python run_diag_dev.py [ДД.ММ.ГГГГ ...]   - даты купона, по умолчанию 18.09.2026 и 16.10.2026
"""
import datetime
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
TASK = os.path.dirname(TESTS)
sys.path.insert(0, os.path.join(TESTS, "1_18"))
import run_1_18_tests as base  # noqa: E402

EPF = os.path.join(TASK, "Т-1", "T9531_ДанныеТ1.epf")


def main():
    dates = sys.argv[1:] or ["18.09.2026", "16.10.2026"]
    fo = base.stage4.connect("wim_fo")
    obj = fo.ВнешниеОбработки.Создать(EPF, False)
    for text in dates:
        day = datetime.datetime.strptime(text, "%d.%m.%Y").replace(hour=12)  # полдень: COM переводит время по поясу, начало дня уезжает на прошлые сутки
        data = obj.Диагностика(day, 60)
        print("=" * 30, text)
        print(obj.ТекстРезультата(data))
        out = os.path.join(HERE, "reports", "diag_dev_%s.json" % day.strftime("%Y%m%d"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(obj.JSONРезультата(data))
        print("json", out)


if __name__ == "__main__":
    main()
