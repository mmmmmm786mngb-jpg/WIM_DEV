#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Включает расширение замеров и снимает безопасный режим на серверной базе."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
OFF = ("FO_BlotterPrelim", "FO_LimitShare", "FO_CheckSafe")
found = False
for ext in conn.РасширенияКонфигурации.Получить():
    name = conn.String(ext.Имя)
    print("ext", name, "active", ext.Активно, "safe", ext.БезопасныйРежим)
    if name in OFF and ext.Активно:
        ext.Активно = False
        ext.Записать()
        print("turned off", name)
        continue
    if name != "FO_LimitProfile":
        continue
    found = True
    ext.Активно = True
    ext.БезопасныйРежим = False
    ext.ИспользоватьОсновныеРолиДляВсехПользователей = True
    try:
        ext.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
    except Exception as error:
        print("protection", str(error)[:180])
    ext.Записать()
    print("updated", name)
if not found:
    raise SystemExit("extension not found")
print("EXT DONE")
