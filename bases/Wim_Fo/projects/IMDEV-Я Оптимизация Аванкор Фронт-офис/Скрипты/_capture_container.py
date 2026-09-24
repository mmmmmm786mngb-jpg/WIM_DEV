#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимает вместилище самого большого прогона и последние замеры."""

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
query = conn.NewObject("Запрос")
query.Текст = (
    "ВЫБРАТЬ ПЕРВЫЕ 5 К.Вместилище КАК Вместилище, КОЛИЧЕСТВО(*) КАК N "
    "ИЗ РегистрСведений.КэшВмКратко КАК К "
    "СГРУППИРОВАТЬ ПО К.Вместилище "
    "УПОРЯДОЧИТЬ ПО N УБЫВ"
)
selection = query.Выполнить().Выбрать()
while selection.Следующий():
    value = selection.Вместилище
    text = ""
    try:
        text = conn.XMLСтрока(value)
    except Exception as error:
        text = "xml-fail " + str(error)
    print("rows", selection.N, "string", conn.String(value), "xml", text)

measures = conn.NewObject("Запрос")
measures.Текст = (
    "ВЫБРАТЬ ПЕРВЫЕ 8 Замеры.КлючеваяОперация.Наименование КАК Имя, "
    "Замеры.ВремяВыполнения КАК Секунды, Замеры.ВесЗамера КАК Вес "
    "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
    "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера УБЫВ"
)
selection = measures.Выполнить().Выбрать()
while selection.Следующий():
    print("measure", conn.String(selection.Имя), selection.Секунды, selection.Вес)
