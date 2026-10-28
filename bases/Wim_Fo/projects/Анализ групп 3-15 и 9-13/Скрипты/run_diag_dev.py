# -*- coding: utf-8 -*-
"""Прогон ДиагностикаОперацийФО на dev ФО через внешнее соединение (проверка перед передачей на Т-1).

    python run_diag_dev.py [ДнейИстории] [deep] - по умолчанию 30; deep - глубокий анализ (9.6); лог в Тестирование/reports
"""
import datetime
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ROST_TESTS = os.path.join(os.path.dirname(PROJECT), "IMDEV-9531 РОСТ", "Тестирование")
sys.path.insert(0, os.path.join(ROST_TESTS, "1_18"))
import run_1_18_tests as base  # noqa: E402

EPF = os.path.join(PROJECT, "Т-1", "ДиагностикаОперацийФО.epf")


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    fo = base.stage4.connect("wim_fo")
    obj = fo.ВнешниеОбработки.Создать(EPF, False)
    started = time.time()
    deep = len(sys.argv) > 2 and sys.argv[2] == "deep"
    text = obj.СобратьЛог(days, False, deep)
    out = os.path.join(PROJECT, "Тестирование", "reports",
                       "diag_dev_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("сбор %.1f с, строк %d, файл %s" % (time.time() - started, text.count("\n") + 1, out))


if __name__ == "__main__":
    main()
