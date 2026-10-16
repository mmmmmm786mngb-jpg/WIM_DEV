#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Выборка в пропорциях ПРОД: 20 покупка, 50 продажа x 2 бумаги, 6694 реинвест."""

import os
import sys

STAND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "IMDEV-9530  Замеры ФО",
    "Тестирование",
    "Стенд_замеры",
)
sys.path.insert(0, STAND)
import run_stage4_tests as stage4  # noqa: E402


def main():
    fo = stage4.connect("wim_fo")
    test_ref = stage4.test_epf(fo)
    params = fo.NewObject("Структура")
    params.Вставить("Сценарий", "ПропорцииПрод")
    out = stage4.run_harness(fo, test_ref, params, "пропорции ПРОД", timeout=7200)
    stage4.log(out.get("состояние"), out.get("длительность_с"), (out.get("ошибка") or "")[:500])
    stage4.log(out.get("лог"))
    for message in out.get("сообщения") or []:
        stage4.log("msg", message)


if __name__ == "__main__":
    main()
