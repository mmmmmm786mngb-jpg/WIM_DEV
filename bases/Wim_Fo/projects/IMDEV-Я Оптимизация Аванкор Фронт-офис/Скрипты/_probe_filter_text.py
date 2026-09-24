#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pythoncom
import win32com.client
pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(
    "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
)
query = conn.NewObject("Запрос")
query.Текст = (
    "ВЫБРАТЬ Наименование, УсловияОтбораОсновные "
    "ИЗ Справочник.Лимиты ГДЕ Наименование В (\"FO_SHAPE S01\", \"FO_SHAPE S04\", \"FO_SHAPE S17\")"
)
selection = query.Выполнить().Выбрать()
while selection.Следующий():
    print("---")
    print(conn.String(selection.Наименование))
    print(conn.String(selection.УсловияОтбораОсновные))
