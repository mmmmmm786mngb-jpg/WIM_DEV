#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка, что документы TREG удалены."""

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


def count(conn, text):
    return stand.query(conn, text, {"Маска": "TREG%"})[0]["Количество"]


def main():
    conn = stand.connect("wim_fo")
    orders = count(conn, "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.Поручение ГДЕ КомментарийКлиента = \"TREG\"")
    deals = count(conn, "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.Сделка ГДЕ НомерСделки ПОДОБНО &Маска")
    posted = stand.query(
        conn,
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.ИсполнениеПоСделке КАК Исп "
        "ГДЕ Исп.Дата >= &Начало И Исп.Дата < &Конец",
        {
            "Начало": stand.date_1c(conn, __import__("datetime").datetime(2099, 3, 15)),
            "Конец": stand.date_1c(conn, __import__("datetime").datetime(2099, 3, 16)),
        },
    )[0]["Количество"]
    print("orders", orders, "deals", deals, "exec2099", posted)


if __name__ == "__main__":
    main()
