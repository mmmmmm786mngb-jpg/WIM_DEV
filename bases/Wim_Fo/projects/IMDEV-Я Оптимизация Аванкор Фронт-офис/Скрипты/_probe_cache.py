#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pythoncom
import win32com.client
CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
query = conn.NewObject("Запрос")
for name in ("КэшВмКратко", "КэшВмДетально", "КэшВмПланПроверки", "КэшВмПозиция"):
    query.Текст = "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ РегистрСведений." + name
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    print(name, selection.N)
