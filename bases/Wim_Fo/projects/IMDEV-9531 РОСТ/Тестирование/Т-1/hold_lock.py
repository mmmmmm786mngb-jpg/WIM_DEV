# -*- coding: utf-8 -*-
"""Держит исключительную управляемую блокировку всей таблицы на dev ФО заданное время (проверка 1.23).

Нужна, чтобы проведения поручений РОСТ в это время ждали блокировку и падали по таймауту (конфликт блокировок):
так проверяется повтор проведения (ПровестиПоручение) и защита цикла потока (ЗаписатьОшибкуПортфеля).

    python hold_lock.py <пространство блокировки> <секунд> [<задержка старта, с>]
    python hold_lock.py РегистрНакопления.ПрогнозПоПоручению 30
    python hold_lock.py РегистрСведений.ВТБ_СтатусыПортфелей 45 5
"""
import datetime
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "1_18"))
import run_1_18_tests as base  # noqa: E402


def main():
    space, seconds = sys.argv[1], float(sys.argv[2])
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    fo = base.stage4.connect("wim_fo")
    time.sleep(delay)
    fo.НачатьТранзакцию()
    try:
        lock = fo.NewObject("БлокировкаДанных")
        item = lock.Добавить(space)
        item.Режим = fo.РежимБлокировкиДанных.Исключительный
        lock.Заблокировать()
        print(datetime.datetime.now().strftime("%H:%M:%S"), "блокировка", space, "на", seconds, "с", flush=True)
        time.sleep(seconds)
    finally:
        fo.ОтменитьТранзакцию()
        print(datetime.datetime.now().strftime("%H:%M:%S"), "блокировка снята", flush=True)


if __name__ == "__main__":
    main()
