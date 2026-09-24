#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Печатает ошибки применимости расширения замеров."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
for ext in conn.РасширенияКонфигурации.Получить():
    if conn.String(ext.Имя) != "FO_LimitProfile":
        continue
    print("active", ext.Активно, "safe", ext.БезопасныйРежим)
    problems = ext.ПроверитьВозможностьПрименения()
    print("problems", problems.Count())
    index = 0
    for problem in problems:
        print(index, conn.String(problem)[:300])
        index += 1
        if index > 20:
            break
print("APPLY DONE")
