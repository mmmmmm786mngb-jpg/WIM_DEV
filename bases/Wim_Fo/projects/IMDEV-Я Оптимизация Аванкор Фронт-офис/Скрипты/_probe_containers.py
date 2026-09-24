#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pythoncom
import win32com.client
CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
query = conn.NewObject("Запрос")
query.Текст = "ВЫБРАТЬ КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Вместилище) КАК N ИЗ РегистрСведений.КэшВмКратко"
selection = query.Выполнить().Выбрать()
selection.Следующий()
print("containers", selection.N)
