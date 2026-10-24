#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Исходные данные покупки и продажи T9531PROP на dev ФО.

Тот же порядок, что в прогонах 1.18-1.21:
  ОчиститьСделки - сделки выборки за сегодня;
  ПропорцииПрод - 20 портфелей покупки (ввод и статус "Поиск ДС"),
    50 портфелей продажи по 2 бумаги (статус "Расторжение инициировано"),
    реинвест не пересоздается, статусы и позиции обновляются;
  ПозицияНаВчера - фактическая позиция выборки копируется на вчера
    (тестовый режим читает позицию предыдущего рабочего дня).

    python prepare_purchase_sale.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "1_18"))
import run_1_18_tests as base  # noqa: E402

stage4 = base.stage4


def main():
    fo = stage4.connect("wim_fo")
    test_ref = base.harness_ref(fo)
    for name in ("ОчиститьСделки", "ПропорцииПрод", "ПозицияНаВчера"):
        step = base.service(fo, test_ref, name, name + " 1.24")
        stage4.log(step["шаг"], step["состояние"], step["длительность_с"], (step.get("ошибка") or "")[:400])
        stage4.log((step.get("лог") or "").replace("\n", " | ")[:500])
        if step.get("ошибка"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
