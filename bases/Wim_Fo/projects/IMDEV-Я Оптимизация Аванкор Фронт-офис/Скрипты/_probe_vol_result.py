#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pythoncom
import win32com.client

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(
    "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
)

def one(text):
    query = conn.NewObject("Запрос")
    query.Текст = text
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    return selection

row = one("ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ Справочник.ВариантыПроверкиПороговЛимитов")
print("variants", row.N)
query = conn.NewObject("Запрос")
query.Текст = "ВЫБРАТЬ ПЕРВЫЕ 8 Наименование КАК Имя ИЗ Справочник.ВариантыПроверкиПороговЛимитов"
selection = query.Выполнить().Выбрать()
while selection.Следующий():
    print("var", conn.String(selection.Имя))
print("position rows", row.N)
row = one("ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ РегистрСведений.ДатаАктуальностиФактическойПозиции")
print("actuality rows", row.N)
query = conn.NewObject("Запрос")
query.Текст = (
    "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N "
    "ИЗ РегистрСведений.ДатаАктуальностиФактическойПозиции КАК D "
    "ВНУТРЕННЕЕ СОЕДИНЕНИЕ РегистрСведений.ФактическаяПозиция КАК T "
    "ПО D.Портфель = T.Портфель И D.Дата = T.Дата "
    "ГДЕ D.Портфель.Наименование ПОДОБНО \"FO_VOL %\""
)
selection = query.Выполнить().Выбрать()
selection.Следующий()
print("joined position", selection.N)
selection = query.Выполнить().Выбрать()
print("joined", selection.N)
