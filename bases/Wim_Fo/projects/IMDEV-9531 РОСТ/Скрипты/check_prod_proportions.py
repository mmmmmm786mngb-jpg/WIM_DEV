#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сколько строк отбора РОСТ видит на сегодняшних данных T9531PROP."""

import os
import tempfile
import time

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"


def main():
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 т.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК т "
        "ГДЕ т.ИмяОбъекта = &Имя И НЕ т.ПометкаУдаления"
    )
    query.УстановитьПараметр("Имя", "СозданиеТорговыхПорученийРОСТ")
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    item = selection.Ссылка.ПолучитьОбъект()
    path = os.path.join(tempfile.gettempdir(), "rost_prop_check.epf")
    item.ХранилищеОбработки.Получить().Записать(path)
    processor = conn.ВнешниеОбработки.Создать(path, False)
    title = ""
    processor.УстановитьПользовательскиеНастройки(item.ХранилищеНастроек.Получить(), title)
    query.Текст = "ВЫБРАТЬ НАЧАЛОПЕРИОДА(&Д, ДЕНЬ) КАК Д"
    query.УстановитьПараметр("Д", conn.ТекущаяДатаСеанса())
    day = query.Выполнить().Выбрать()
    day.Следующий()
    today = day.Д

    started = time.perf_counter()
    processor.ОбновитьСписокПортфелейПокупка("", 0)
    print("buy", int(processor.СписокПортфелейПокупка.Количество()), "sec", round(time.perf_counter() - started, 2))

    started = time.perf_counter()
    processor.ЗаполнитьСписокПродажаАктивов(True, "", 0)
    print("sale", int(processor.СписокПортфелейПродажа.Количество()), "sec", round(time.perf_counter() - started, 2))

    started = time.perf_counter()
    processor.РеинвестОбновитьСписокПотфелей(today, True, 0, 0, "", 0)
    print("reinvest", int(processor.СписокПортфелейРеинвестирование.Количество()), "sec", round(time.perf_counter() - started, 2))
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
