#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет, что после записи формы снимок лежит только в файле."""

import pythoncom
import win32com.client


def main():
    pythoncom.CoInitialize()
    try:
        connect = "File='C:\\Users\\Acer\\Documents\\1C\\EmployeePhotos';App='PyCOM';Locale=ru_RU;"
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(connect)
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ Наименование, ИмяФайлаФотографии "
            "ИЗ Справочник.Сотрудники "
            "ГДЕ Наименование = &Наименование"
        )
        query.УстановитьПараметр("Наименование", "Тест PNG из базы")
        row = query.Выполнить().Выгрузить()[0]
        print("file=" + str(row.ИмяФайлаФотографии))
        manager = conn.NewObject("СправочникМенеджер.Сотрудники")
        ref = manager.НайтиПоНаименованию("Тест PNG из базы")
        obj = ref.ПолучитьОбъект()
        data = obj.Фотография.Получить()
        print("storage_type=" + str(type(data).__name__))
        print("storage_empty=" + str(data is None))
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
