#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect ДоговорДУ.Пул values."""

import pythoncom
import win32com.client

def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;")
        q = conn.NewObject("Запрос")
        q.Текст = (
            "ВЫБРАТЬ "
            "КОЛИЧЕСТВО(Т.Ссылка) КАК Кнт, "
            "КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Т.Пул) КАК Пулов "
            "ИЗ Справочник.ДоговорДУ КАК Т "
            "ГДЕ Т.Пул <> ЗНАЧЕНИЕ(Справочник.Пул.ПустаяСсылка)"
        )
        r = q.Выполнить().Выгрузить()[0]
        print("WithPul=" + str(int(r.Кнт)) + " DistinctPul=" + str(int(r.Пулов)))

        q.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 10 "
            "Т.Код КАК Код, "
            "Т.Пул КАК Пул, "
            "ПРЕДСТАВЛЕНИЕ(Т.Пул) КАК ПулПредст "
            "ИЗ Справочник.ДоговорДУ КАК Т "
            "ГДЕ Т.Пул <> ЗНАЧЕНИЕ(Справочник.Пул.ПустаяСсылка)"
        )
        r2 = q.Выполнить().Выгрузить()
        print("SAMPLES:")
        for row in r2:
            print("  " + str(row.Код) + " | " + str(row.ПулПредст))

        # how termination test finds pool
        q.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 5 Т.Наименование КАК Имя "
            "ИЗ Справочник.Пул КАК Т"
        )
        try:
            r3 = q.Выполнить().Выгрузить()
            print("PulRows=" + str(r3.Count()))
        except Exception as e:
            print("PulQueryErr=" + str(e))
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    main()
