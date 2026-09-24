#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pythoncom
import win32com.client
CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
try:
    conn.Распорядители.FO_LimitProfile_Добавить("probe", 1)
    print("direct call ok")
except Exception as error:
    print("direct fail", str(error)[:500])
