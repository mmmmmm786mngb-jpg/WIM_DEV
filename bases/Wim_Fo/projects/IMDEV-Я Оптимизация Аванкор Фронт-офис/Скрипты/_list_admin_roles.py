#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимает роли пользователя admin локальной файловой базы."""

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
users = conn.ПользователиИнформационнойБазы
user = users.НайтиПоИмени("admin")
print("name", user.Имя)
print("full", user.ПолноеИмя)
print("standard", user.АутентификацияСтандартная)
print("os", user.АутентификацияОС)
print("show", user.ПоказыватьВСпискеВыбора)
roles = user.Роли
print("roles type", type(roles))
try:
    print("count", roles.Количество())
except Exception as error:
    print("count fail", error)
index = 0
try:
    for role in roles:
        print("role", index, conn.String(role.Имя))
        index += 1
except Exception as error:
    print("iter fail", error)
print("ROLES", index)
