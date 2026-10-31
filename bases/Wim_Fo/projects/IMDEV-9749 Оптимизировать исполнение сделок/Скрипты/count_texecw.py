#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка, что тестовые поручения TEXECW и их записи регистров удалены."""

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
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.Поручение КАК Поручения "
        "ГДЕ Поручения.КомментарийКлиента = &Маркер",
        {"Маркер": "TEXECW"},
    )
    # После удаления документов записи регистров остаются с битой ссылкой: ищем записи без документа
    orphans = stand.query(
        conn,
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ РегистрСведений.СтатусыПоручений КАК Статусы "
        "ГДЕ Статусы.Поручение.Ссылка ЕСТЬ NULL",
        {},
    )
    ext_orphans = stand.query(
        conn,
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ РегистрСведений.РасширенияПоручений КАК Расш "
        "ГДЕ Расш.Поручение.Ссылка ЕСТЬ NULL",
        {},
    )
    print("orders", orders[0]["Количество"],
          "status orphans", orphans[0]["Количество"],
          "ext orphans", ext_orphans[0]["Количество"])


if __name__ == "__main__":
    main()
