#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет, инициализируется ли РаботаСЛимитами без расширения замеров."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
for ext in conn.РасширенияКонфигурации.Получить():
    if conn.String(ext.Имя) == "FO_LimitProfile":
        ext.Активно = False
        ext.Записать()
        print("deactivated")
pythoncom.CoUninitialize()

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
try:
    value = conn.РаботаСЛимитами.ПланПроверкиМакет()
    print("maket", type(value))
except Exception as error:
    print("FAIL", str(error)[:400])
