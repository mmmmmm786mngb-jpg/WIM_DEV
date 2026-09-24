#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет, что серверная база открывается и в ней есть данные выгрузки."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
user = conn.ПользователиИнформационнойБазы.ТекущийПользователь()
query = conn.NewObject("Запрос")
query.Текст = (
    "ВЫБРАТЬ "
    "(ВЫБРАТЬ КОЛИЧЕСТВО(*) ИЗ Справочник.Портфели ГДЕ Наименование ПОДОБНО \"FO_FO %\") КАК Фо, "
    "(ВЫБРАТЬ КОЛИЧЕСТВО(*) ИЗ Справочник.Лимиты ГДЕ Родитель.Наименование = \"482-п ДУ\" И НЕ ЭтоГруппа) КАК Лимиты"
)
# Nested selects in the select list failed earlier. Count separately.
for title, text in (
    ("portfolios", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ Справочник.Портфели ГДЕ Наименование ПОДОБНО \"FO_FO %\""),
    ("limits", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ Справочник.Лимиты ГДЕ Родитель.Наименование = \"482-п ДУ\" И НЕ ЭтоГруппа"),
):
    query.Текст = text
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    print(title, selection.N)
print("user", user.Имя)
print("VERIFY OK")
