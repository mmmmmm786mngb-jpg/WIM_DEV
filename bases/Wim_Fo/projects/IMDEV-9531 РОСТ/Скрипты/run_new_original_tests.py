#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прогон режимов РОСТ через обработку из НОВЫЙ_ОРИГИНАЛ на WIN_FO_server.

Обработка запускается тестовой обвязкой в фоновом задании с ЭтоТест = Истина:
цена берется из регистра котировок, документы проводятся, проверка и отправка
вызываются так же, как из формы и регламентного задания. Команда через БСП
(ЭтоТест из настроек) не запускается.
"""

import json
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

NEW_EPF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "НОВЫЙ_ОРИГИНАЛ",
)
SERIES = "9531"
ONLY = [
    "Покупка.Команда",
    "Покупка.Форма",
    "Продажа.Команда",
    "Продажа.Форма",
    "Реинвест.Форма",
    "Реинвест.Потоки",
    "Блокировки.Потоки",
]
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Тестирование",
    "reports",
    "new_original_run.json",
)


def main():
    stage4.EPF_FILES["замеры"] = NEW_EPF_DIR
    fo = stage4.connect("wim_fo")
    stage4.log("prep", SERIES)
    stage4.step_prep(fo, SERIES)
    stage4.log("data", SERIES)
    stage4.step_data(fo, SERIES)

    fo = stage4.connect("wim_fo")
    bond, _asset = stage4.ensure_bond(fo)
    test_ref = stage4.test_epf(fo)
    params = fo.NewObject("Структура")
    params.Вставить("Сценарий", "Купоны")
    params.Вставить("Облигация", bond)
    params.Вставить("ДатаКупона", stage4.today_1c(fo))
    params.Вставить("РазмерКупона", 40)
    params.Вставить("КупоновВперед", 10)
    params.Вставить("ДатаДокумента", fo.ТекущаяДатаСеанса())
    coupons = stage4.run_harness(fo, test_ref, params, "купон на сегодня, документ текущей датой")

    fo = stage4.connect("wim_fo")
    stage4.log("rost", SERIES, "через", NEW_EPF_DIR)
    stage4.step_rost(fo, SERIES, "замеры", ONLY)

    state = stage4.load_state(SERIES)
    since = state["runs"][-1]["начало"]
    fo = stage4.connect("wim_fo")
    measures = stage4.measurements(fo, since)
    orders = stage4.orders_snapshot(fo, SERIES, "замеры")
    payload = {
        "series": SERIES,
        "epf": os.path.join(NEW_EPF_DIR, "внСозданиеТорговыхПорученийРОСТ.epf"),
        "coupons": coupons,
        "run": state["runs"][-1],
        "measurements": measures,
        "orders": orders,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
    stage4.log("saved", OUT, "measures", len(measures), "orders", len(orders))


if __name__ == "__main__":
    main()
