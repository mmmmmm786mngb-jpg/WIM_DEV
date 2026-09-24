#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Последние штатные замеры проверки на сервере."""

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
query = conn.NewObject("Запрос")
query.Текст = (
    "ВЫБРАТЬ ПЕРВЫЕ 12 Замеры.КлючеваяОперация.Наименование КАК Имя, "
    "Замеры.ВремяВыполнения КАК Секунды, Замеры.ВесЗамера КАК Вес "
    "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
    "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера УБЫВ"
)
selection = query.Выполнить().Выбрать()
while selection.Следующий():
    print("%s\t%s\t%s" % (conn.String(selection.Имя), selection.Секунды, selection.Вес))
