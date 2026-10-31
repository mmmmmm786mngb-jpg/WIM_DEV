#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка, что тестовые документы TEXEC1000 удалены."""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

STAND = (
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Fo\projects"
    r"\IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО"
    r"\Тестирование\Стенд_МО_ФО"
)
sys.path.insert(0, STAND)
import stand_common as stand  # noqa: E402


def main():
    conn = stand.connect("wim_fo")
    orders = stand.query(
        conn,
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.Поручение ГДЕ КомментарийКлиента = &Маркер",
        {"Маркер": "TEXEC1000"},
    )
    deals = stand.query(
        conn,
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.Сделка ГДЕ НомерСделки ПОДОБНО &Маска",
        {"Маска": "TEXEC1000%"},
    )
    print("orders", orders[0]["Количество"], "deals", deals[0]["Количество"])


if __name__ == "__main__":
    main()
