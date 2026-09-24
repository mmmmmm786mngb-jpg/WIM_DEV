#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Один прогон FO_SHAPE: базис, зоны и время обработки проверки."""

import importlib.util
import os

import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pack_base", os.path.join(HERE, "run_pack_baseline.py"))
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


def collect(conn, text):
    query = conn.NewObject("Запрос")
    query.Текст = text
    selection = query.Выполнить().Выбрать()
    refs = []
    while selection.Следующий():
        refs.append(selection.Ссылка)
    return refs


def summary(conn, container):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ К.Зона КАК Зона, КОЛИЧЕСТВО(*) КАК N, "
        "МИНИМУМ(К.Базис) КАК МинБазис, МАКСИМУМ(К.Базис) КАК МаксБазис "
        "ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Вместилище = &Вместилище "
        "СГРУППИРОВАТЬ ПО К.Зона"
    )
    query.УстановитьПараметр("Вместилище", container)
    selection = query.Выполнить().Выбрать()
    lines = []
    while selection.Следующий():
        lines.append("%s n=%s basis %s..%s" % (
            conn.String(selection.Зона), selection.N, selection.МинБазис, selection.МаксБазис))
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 16 К.Лимит.Наименование КАК Лимит, К.Фокус.Наименование КАК Фокус, "
        "К.Зона КАК Зона, К.Базис КАК Базис, К.Описание КАК Описание "
        "ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Вместилище = &Вместилище И К.Лимит.Наименование ПОДОБНО \"FO_SHAPE S%\" "
        "И (К.Фокус.Наименование = \"FO_SHAPE 001\" ИЛИ К.Фокус.Наименование = \"FO_SHAPE 090\") "
        "УПОРЯДОЧИТЬ ПО Лимит, Фокус"
    )
    query.УстановитьПараметр("Вместилище", container)
    selection = query.Выполнить().Выбрать()
    while selection.Следующий():
        lines.append("%s | %s | %s | %s | %s" % (
            conn.String(selection.Лимит),
            conn.String(selection.Фокус),
            conn.String(selection.Зона),
            selection.Базис,
            conn.String(selection.Описание).replace("\n", " ")[:140],
        ))
    return lines


def main():
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(pack.CONN)
    portfolios = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Портфели ГДЕ Наименование ПОДОБНО \"FO_SHAPE %\" УПОРЯДОЧИТЬ ПО Наименование",
    )
    limits = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты ГДЕ Наименование ПОДОБНО \"FO_SHAPE S%\" "
        "ИЛИ Наименование ПОДОБНО \"FO_SHAPE C%\" УПОРЯДОЧИТЬ ПО Наименование",
    )
    elapsed, result, container = pack.run_post(conn, portfolios, limits)
    pack.safe_print("post %s refusal %s rows_limits %s" % (format(elapsed, ".3f"), result.Отказ, len(limits)))
    pack.safe_print("desc " + str(result.Описание).replace("\n", " ")[:300])
    for line in summary(conn, container):
        pack.safe_print(line)
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 4 Замеры.КлючеваяОперация.Наименование КАК Имя, "
        "Замеры.ВремяВыполнения КАК Секунды, Замеры.ВесЗамера КАК Вес "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера УБЫВ"
    )
    selection = query.Выполнить().Выбрать()
    while selection.Следующий():
        pack.safe_print("%s %s %s" % (conn.String(selection.Имя), selection.Секунды, selection.Вес))


if __name__ == "__main__":
    main()
