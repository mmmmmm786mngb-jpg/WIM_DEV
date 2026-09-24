#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет, виден ли метод расширения в серверном фоновом задании."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
arguments = conn.NewObject("Массив")
arguments.Add("probe")
arguments.Add(1)
try:
    job = conn.ФоновыеЗадания.Выполнить(
        "Распорядители.FO_LimitProfile_Добавить", arguments, "FO_LimitProfileProbe", "probe")
except Exception as error:
    print("start fail", str(error)[:500])
    raise SystemExit(1)
updated = job.ОжидатьЗавершенияВыполнения(60)
print("state", conn.String(updated.Состояние))
info = updated.ИнформацияОбОшибке
if info is not None:
    print("error", conn.String(info.ПодробноеПредставлениеОшибки)[:800])
else:
    print("no error")
print("PROBE METHOD DONE")
