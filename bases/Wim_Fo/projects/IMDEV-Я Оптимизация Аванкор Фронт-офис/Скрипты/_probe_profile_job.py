#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Смотрит, записала ли проверка результат и что сказал фоновое задание."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
query = conn.NewObject("Запрос")
query.Текст = "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ РегистрСведений.КэшВмКратко"
selection = query.Выполнить().Выбрать()
selection.Следующий()
print("rows", selection.N)
filt = conn.NewObject("Структура")
filt.Вставить("Ключ", "FO_LimitProfile")
jobs = conn.ФоновыеЗадания.ПолучитьФоновыеЗадания(filt)
job = None
for item in jobs:
    job = item
    break
print("state", conn.String(job.Состояние))
info = job.ИнформацияОбОшибке
print("info is none", info is None)
if info is not None:
    print("detail", conn.String(info.ПодробноеПредставлениеОшибки)[:1000])
messages = job.ПолучитьСообщенияПользователю()
print("messages", messages.Count())
print("PROBE DONE")
