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
    "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ Справочник.Портфели "
    "ГДЕ Наименование ПОДОБНО \"FO_SHAPE %\""
)
selection = query.Выполнить().Выбрать()
selection.Следующий()
print("count", selection.N)
