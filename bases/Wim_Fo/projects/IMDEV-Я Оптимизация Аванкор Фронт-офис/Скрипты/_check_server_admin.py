#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет вход admin в серверную базу."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
user = conn.ПользователиИнформационнойБазы.ТекущийПользователь()
print("login", user.Имя)
print("LOGIN OK")
