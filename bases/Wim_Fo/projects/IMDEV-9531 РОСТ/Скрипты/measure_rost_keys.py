#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замеры ключевой операции создания торговых поручений РОСТ в регистре ЗамерыВремени."""

import json
import os
import time

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Тестирование",
    "reports",
    "measure_rost_keys.json",
)


def as_text(conn, value):
    try:
        return str(conn.String(value))
    except Exception:
        return str(value)


def main():
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ "
        "Замеры.ДатаНачалаЗамера КАК Старт, "
        "Замеры.КлючеваяОперация.Наименование КАК Имя, "
        "Замеры.ВремяВыполнения КАК Секунды, "
        "Замеры.ВесЗамера КАК Вес, "
        "Замеры.Комментарий КАК Комментарий "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "ГДЕ Замеры.КлючеваяОперация.Наименование ПОДОБНО &Шаблон "
        "УПОРЯДОЧИТЬ ПО Замеры.ВремяВыполнения УБЫВ"
    )
    query.УстановитьПараметр("Шаблон", "%торговых поручений%")
    started = time.perf_counter()
    selection = query.Выполнить().Выбрать()
    rows = []
    while selection.Следующий():
        rows.append({
            "name": as_text(conn, selection.Имя),
            "seconds": float(selection.Секунды),
            "weight": int(selection.Вес),
            "comment": as_text(conn, selection.Комментарий),
            "started": as_text(conn, selection.Старт),
        })
    payload = {"sec": round(time.perf_counter() - started, 3), "rows": rows}
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print("rows " + str(len(rows)))
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
