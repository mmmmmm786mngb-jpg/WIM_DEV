#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ждет уже запущенное фоновое задание замера."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
filt = conn.NewObject("Структура")
filt.Вставить("Ключ", "FO_LimitProfile")
filt.Вставить("ИмяМетода", "Распорядители.ПроверкаИОтправка")
jobs = conn.ФоновыеЗадания.ПолучитьФоновыеЗадания(filt)
print("jobs", jobs.Count() if hasattr(jobs, "Count") else "n/a")
job = None
try:
    job = jobs.Get(0)
except Exception:
    for item in jobs:
        job = item
        break
if job is None:
    print("no job")
    raise SystemExit(1)
print("state before", conn.String(job.Состояние))
updated = job.ОжидатьЗавершенияВыполнения(1800)
print("state after", conn.String(updated.Состояние))
info = updated.ИнформацияОбОшибке
if info is not None:
    try:
        print("error", conn.String(info.Описание)[:800])
    except Exception as error:
        print("error object", str(error)[:200])
print("WAIT DONE")
