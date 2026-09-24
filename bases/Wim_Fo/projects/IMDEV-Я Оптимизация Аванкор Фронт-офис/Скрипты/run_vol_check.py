#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Прогон пост-контроля FO_VOL и сводка зон."""

import importlib.util
import os

import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "pack_base", os.path.join(HERE, "run_pack_baseline.py"))
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


def main():
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(pack.CONN)
    portfolios = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Портфели ГДЕ Наименование ПОДОБНО \"FO_VOL %\" "
        "УПОРЯДОЧИТЬ ПО Наименование",
    )
    limits = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты ГДЕ Наименование ПОДОБНО \"FO_VOL S%\" "
        "УПОРЯДОЧИТЬ ПО Наименование",
    )
    pack.safe_print("portfolios %s limits %s" % (len(portfolios), len(limits)))
    elapsed, result = pack.run_post(conn, portfolios, limits)[:2]
    pack.safe_print("seconds " + format(elapsed, ".3f"))
    pack.safe_print("refusal " + str(result.Отказ))
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ К.Зона КАК Зона, КОЛИЧЕСТВО(*) КАК N "
        "ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Лимит.Наименование ПОДОБНО \"FO_VOL S%\" "
        "СГРУППИРОВАТЬ ПО К.Зона"
    )
    selection = query.Выполнить().Выбрать()
    while selection.Следующий():
        pack.safe_print("zone %s %s" % (conn.String(selection.Зона), selection.N))
    measure = conn.NewObject("Запрос")
    measure.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 8 Замеры.КлючеваяОперация.Наименование КАК Имя, "
        "Замеры.ВремяВыполнения КАК Секунды, Замеры.ВесЗамера КАК Вес "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера УБЫВ"
    )
    rows = measure.Выполнить().Выбрать()
    while rows.Следующий():
        pack.safe_print("%s | %s | %s" % (conn.String(rows.Имя), rows.Секунды, rows.Вес))


if __name__ == "__main__":
    main()
