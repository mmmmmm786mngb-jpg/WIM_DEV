#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Включает FO_PortionIndex и печатает ошибки применимости."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
target = None
for ext in conn.РасширенияКонфигурации.Получить():
    name = conn.String(ext.Имя)
    print("ext", name, "active", ext.Активно, "safe", ext.БезопасныйРежим)
    if name == "FO_PortionIndex":
        target = ext
if target is None:
    raise SystemExit("extension not found")
target.Активно = True
target.БезопасныйРежим = False
target.ИспользоватьОсновныеРолиДляВсехПользователей = True
try:
    target.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
except Exception as error:
    print("protection", str(error)[:180])
target.Записать()
problems = target.ПроверитьВозможностьПрименения()
print("problems", problems.Count())
index = 0
for problem in problems:
    print("problem", conn.String(problem)[:500])
    index += 1
    if index > 30:
        break
print("APPLY DONE")
