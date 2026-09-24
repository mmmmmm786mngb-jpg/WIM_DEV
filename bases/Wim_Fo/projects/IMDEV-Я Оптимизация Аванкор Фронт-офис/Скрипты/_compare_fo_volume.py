#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверяет два прогона FO_FO: без расширения и с расширением."""

import os
import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OLD = "87128643-7435-403f-85c1-1408d4179f0a"
NEW = "8cfb31d3-e528-41fc-bc82-767089489121"
OUT = os.path.join(ROOT, "Тестирование", "reports", "fo_volume_cmp.txt")

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
type_uuid = conn.NewObject("ОписаниеТипов", "УникальныйИдентификатор").Типы().Get(0)
old_id = conn.XMLЗначение(type_uuid, OLD)
new_id = conn.XMLЗначение(type_uuid, NEW)
query = conn.NewObject("Запрос")
query.Текст = (
    "ВЫБРАТЬ А.Лимит КАК Лимит, А.Фокус КАК Фокус, А.Поручение КАК Поручение, "
    "А.Зона КАК Зона, А.Базис КАК Базис, А.Отказ КАК Отказ, А.Описание КАК Описание "
    "ПОМЕСТИТЬ Старый "
    "ИЗ РегистрСведений.КэшВмКратко КАК А ГДЕ А.Вместилище = &Старый "
    "; "
    "ВЫБРАТЬ Б.Лимит КАК Лимит, Б.Фокус КАК Фокус, Б.Поручение КАК Поручение, "
    "Б.Зона КАК Зона, Б.Базис КАК Базис, Б.Отказ КАК Отказ, Б.Описание КАК Описание "
    "ПОМЕСТИТЬ Новый "
    "ИЗ РегистрСведений.КэшВмКратко КАК Б ГДЕ Б.Вместилище = &Новый "
    "; "
    "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N "
    "ИЗ Старый КАК А "
    "ЛЕВОЕ СОЕДИНЕНИЕ Новый КАК Б "
    "ПО А.Лимит = Б.Лимит И А.Фокус = Б.Фокус И А.Поручение = Б.Поручение "
    "ГДЕ Б.Лимит ЕСТЬ NULL "
    "ИЛИ А.Зона <> Б.Зона "
    "ИЛИ А.Базис <> Б.Базис "
    "ИЛИ А.Отказ <> Б.Отказ "
    "ИЛИ А.Описание <> Б.Описание"
)
query.УстановитьПараметр("Старый", old_id)
query.УстановитьПараметр("Новый", new_id)
selection = query.Выполнить().Выбрать()
selection.Следующий()
mismatch = selection.N
lines = [
    "old %s" % OLD,
    "new %s" % NEW,
    "mismatch %s" % mismatch,
    "off обработка 379.382 проверка 534.798",
    "on обработка 398.632 проверка 542.902",
]
with open(OUT, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
print("mismatch", mismatch)
print("COMPARE DONE")
