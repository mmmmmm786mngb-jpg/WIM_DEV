#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пост-контроль 3000 портфелей FO_SHAPE и сверка двух вместилищ.
Полные строки в файл не выгружаются: расхождения считает запрос.
"""

import importlib.util
import os
import sys

import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
spec = importlib.util.spec_from_file_location("shape", os.path.join(HERE, "run_shape_round.py"))
shape = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shape)


def xml_of(conn, value):
    return conn.XMLСтрока(value)


def uuid_from_xml(conn, text):
    type_uuid = conn.NewObject("ОписаниеТипов", "УникальныйИдентификатор").Типы().Get(0)
    return conn.XMLЗначение(type_uuid, text)


def summary(conn, container):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Вместилище = &Вместилище"
    )
    query.УстановитьПараметр("Вместилище", container)
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    count = selection.N
    lines = ["rows\t%s" % count, "container\t%s" % xml_of(conn, container)]
    lines.extend(shape.measures(conn))
    lines.extend(shape.zones(conn, container))
    return lines


def compare(conn, old_xml, new_xml):
    old_id = uuid_from_xml(conn, old_xml)
    new_id = uuid_from_xml(conn, new_xml)
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ А.Лимит КАК Лимит, А.Фокус КАК Фокус, А.Поручение КАК Поручение, "
        "А.Зона КАК Зона, А.Базис КАК Базис, А.Отказ КАК Отказ, А.Описание КАК Описание "
        "ПОМЕСТИТЬ Старый "
        "ИЗ РегистрСведений.КэшВмКратко КАК А ГДЕ А.Вместилище = &Старый; "
        "ВЫБРАТЬ Б.Лимит КАК Лимит, Б.Фокус КАК Фокус, Б.Поручение КАК Поручение, "
        "Б.Зона КАК Зона, Б.Базис КАК Базис, Б.Отказ КАК Отказ, Б.Описание КАК Описание "
        "ПОМЕСТИТЬ Новый "
        "ИЗ РегистрСведений.КэшВмКратко КАК Б ГДЕ Б.Вместилище = &Новый; "
        "ВЫБРАТЬ ПЕРВЫЕ 20 "
        "А.Лимит.Наименование КАК Лимит, А.Фокус.Наименование КАК Фокус, "
        "А.Зона КАК ЗонаСтарая, Б.Зона КАК ЗонаНовая, "
        "А.Базис КАК БазисСтарый, Б.Базис КАК БазисНовый, "
        "А.Отказ КАК ОтказСтарый, Б.Отказ КАК ОтказНовый, "
        "А.Описание КАК ОписаниеСтарое, Б.Описание КАК ОписаниеНовое "
        "ИЗ Старый КАК А "
        "ЛЕВОЕ СОЕДИНЕНИЕ Новый КАК Б "
        "ПО А.Лимит = Б.Лимит И А.Фокус = Б.Фокус И А.Поручение = Б.Поручение "
        "ГДЕ Б.Лимит ЕСТЬ NULL ИЛИ А.Зона <> Б.Зона ИЛИ А.Базис <> Б.Базис "
        "ИЛИ А.Отказ <> Б.Отказ ИЛИ А.Описание <> Б.Описание"
    )
    query.УстановитьПараметр("Старый", old_id)
    query.УстановитьПараметр("Новый", new_id)
    selection = query.Выполнить().Выбрать()
    rows = []
    while selection.Следующий():
        rows.append("%s\t%s\t%s\t%s\t%s\t%s" % (
            conn.String(selection.Лимит),
            conn.String(selection.Фокус),
            conn.String(selection.ЗонаСтарая),
            conn.String(selection.ЗонаНовая),
            selection.БазисСтарый,
            selection.БазисНовый,
        ))
    count_query = conn.NewObject("Запрос")
    count_query.Текст = (
        "ВЫБРАТЬ А.Лимит КАК Лимит, А.Фокус КАК Фокус, А.Поручение КАК Поручение, "
        "А.Зона КАК Зона, А.Базис КАК Базис, А.Отказ КАК Отказ, А.Описание КАК Описание "
        "ПОМЕСТИТЬ Старый "
        "ИЗ РегистрСведений.КэшВмКратко КАК А ГДЕ А.Вместилище = &Старый; "
        "ВЫБРАТЬ Б.Лимит КАК Лимит, Б.Фокус КАК Фокус, Б.Поручение КАК Поручение, "
        "Б.Зона КАК Зона, Б.Базис КАК Базис, Б.Отказ КАК Отказ, Б.Описание КАК Описание "
        "ПОМЕСТИТЬ Новый "
        "ИЗ РегистрСведений.КэшВмКратко КАК Б ГДЕ Б.Вместилище = &Новый; "
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N "
        "ИЗ Старый КАК А "
        "ЛЕВОЕ СОЕДИНЕНИЕ Новый КАК Б "
        "ПО А.Лимит = Б.Лимит И А.Фокус = Б.Фокус И А.Поручение = Б.Поручение "
        "ГДЕ Б.Лимит ЕСТЬ NULL ИЛИ А.Зона <> Б.Зона ИЛИ А.Базис <> Б.Базис "
        "ИЛИ А.Отказ <> Б.Отказ ИЛИ А.Описание <> Б.Описание"
    )
    count_query.УстановитьПараметр("Старый", old_id)
    count_query.УстановитьПараметр("Новый", new_id)
    count_selection = count_query.Выполнить().Выбрать()
    count_selection.Следующий()
    return count_selection.N, rows


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "vol3000"
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(shape.pack.CONN)
    portfolios = shape.collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Портфели ГДЕ Наименование ПОДОБНО \"FO_SHAPE %\" "
        "УПОРЯДОЧИТЬ ПО Наименование",
    )
    limits = shape.collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты "
        "ГДЕ Наименование ПОДОБНО \"FO_SHAPE S%\" ИЛИ Наименование ПОДОБНО \"FO_SHAPE C%\" "
        "ИЛИ Наименование ПОДОБНО \"FO_REP S%\" ИЛИ Наименование ПОДОБНО \"FO_REP C%\" "
        "УПОРЯДОЧИТЬ ПО Наименование",
    )
    shape.pack.safe_print("portfolios %s limits %s" % (len(portfolios), len(limits)))
    elapsed, result, container = shape.pack.run_post(conn, portfolios, limits)
    shape.pack.safe_print("post finished %s refusal %s" % (format(elapsed, ".3f"), result.Отказ))
    lines = [
        "label\t%s" % label,
        "portfolios\t%s" % len(portfolios),
        "limits\t%s" % len(limits),
        "seconds\t%s" % format(elapsed, ".3f"),
        "refusal\t%s" % result.Отказ,
    ]
    lines.extend(summary(conn, container))
    path = os.path.join(ROOT, "Тестирование", "reports", "shape_volume_%s.txt" % label)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    shape.pack.safe_print("post %s rows see %s" % (format(elapsed, ".3f"), path))
    shape.pack.safe_print("VOLUME DONE %s" % label)


if __name__ == "__main__":
    main()
