#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создает сотрудника со снимком PNG только в хранилище значения."""

import pythoncom
import win32com.client


def main():
    pythoncom.CoInitialize()
    try:
        connect = "File='C:\\Users\\Acer\\Documents\\1C\\EmployeePhotos';App='PyCOM';Locale=ru_RU;"
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(connect)
        binary = conn.NewObject(
            "ДвоичныеДанные",
            r"C:\Users\Acer\Documents\1C\EmployeePhotosFiles\sample.png",
        )
        storage = conn.NewObject("ХранилищеЗначения", binary, conn.NewObject("СжатиеДанных", 9))
        item = conn.NewObject("СправочникМенеджер.Сотрудники").СоздатьЭлемент()
        item.Наименование = "Тест PNG из базы"
        item.СпособХраненияФотографии = conn.Перечисления.СпособыХраненияФотографий.ВИнформационнойБазе
        item.Фотография = storage
        item.Записать()
        print("OK created")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
