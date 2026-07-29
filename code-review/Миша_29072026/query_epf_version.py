#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump all additional processings from WIM_DU."""

import sys

import pythoncom
import win32com.client


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_DU';")
        q = conn.NewObject("Запрос")
        q.Текст = """
        ВЫБРАТЬ
            Доп.Наименование КАК Наименование,
            Доп.ИмяОбъекта КАК ИмяОбъекта,
            Доп.Версия КАК Версия,
            Доп.ИмяФайла КАК ИмяФайла,
            Доп.ПометкаУдаления КАК ПометкаУдаления
        ИЗ
            Справочник.ДополнительныеОтчетыИОбработки КАК Доп
        """
        result = q.Выполнить().Выгрузить()
        n = result.Количество()
        safe_print("TOTAL " + str(n))
        for i in range(n):
            row = result.Get(i)
            safe_print("---")
            safe_print("Name: " + str(row.Наименование))
            safe_print("Object: " + str(row.ИмяОбъекта))
            safe_print("Version: " + str(row.Версия))
            safe_print("File: " + str(row.ИмяФайла))
            safe_print("Deleted: " + str(row.ПометкаУдаления))
    except Exception as e:
        safe_print("ERROR: " + str(e))
        return 1
    finally:
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
