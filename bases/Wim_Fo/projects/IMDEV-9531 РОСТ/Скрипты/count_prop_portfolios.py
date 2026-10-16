#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pythoncom
import win32com.client

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(
    "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;")
query = conn.NewObject("Запрос")
query.Текст = (
    "ВЫБРАТЬ ПОДСТРОКА(П.ВнешнийКод, 1, 12) КАК Префикс, КОЛИЧЕСТВО(*) КАК Кво "
    "ИЗ Справочник.Портфели КАК П ГДЕ П.ВнешнийКод ПОДОБНО &Маска "
    "СГРУППИРОВАТЬ ПО ПОДСТРОКА(П.ВнешнийКод, 1, 12)"
)
query.УстановитьПараметр("Маска", "T9531PROP%")
selection = query.Выполнить().Выбрать()
total = 0
while selection.Следующий():
    count = int(selection.Кво)
    total += count
    print("%s %s" % (conn.String(selection.Префикс), count))
print("total", total)
pythoncom.CoUninitialize()
