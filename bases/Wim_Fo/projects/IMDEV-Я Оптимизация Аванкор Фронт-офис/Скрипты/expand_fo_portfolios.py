#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Доводит число портфелей FO_FO до 3000.
001-050 уже есть. 051-2400 копируют позицию 001, 2401-3000 ту же позицию с четырехкратной стоимостью.
На каждый новый портфель проводятся те же лимиты группы 482-п ДУ.
"""

import importlib.util
import os
from datetime import datetime

import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fo", os.path.join(HERE, "load_fo_limits.py"))
fo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fo)

TARGET = 3000
TAIL_FROM = 2401


def portfolio_name(index):
    if index < 1000:
        return "FO_FO %03d" % index
    return "FO_FO %d" % index


def existing_names(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Наименование ИЗ Справочник.Портфели "
        "ГДЕ Наименование ПОДОБНО \"FO_FO %\""
    )
    selection = query.Выполнить().Выбрать()
    names = set()
    while selection.Следующий():
        names.add(conn.String(selection.Наименование))
    return names


def template_rows(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Актив, МестоХранения, Стоимость "
        "ИЗ РегистрСведений.ФактическаяПозиция "
        "ГДЕ Портфель.Наименование = \"FO_FO 001\""
    )
    table = query.Выполнить().Выгрузить()
    rows = []
    for index in range(table.Количество()):
        row = table.Получить(index)
        rows.append((row.Актив, row.МестоХранения, row.Стоимость))
    if not rows:
        raise RuntimeError("FO_FO 001 has no position")
    return rows


def limit_refs(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты "
        "ГДЕ НЕ ЭтоГруппа И НЕ ПометкаУдаления И Родитель.Наименование = &Группа"
    )
    query.УстановитьПараметр("Группа", fo.GROUP_NAME)
    selection = query.Выполнить().Выбрать()
    refs = []
    while selection.Следующий():
        refs.append(selection.Ссылка)
    if not refs:
        raise RuntimeError("no limits in group")
    return refs


def write_copied_positions(conn, portfolios, rows):
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    empty = fo.query_date(conn, 1, 1, 1)
    position = conn.РегистрыСведений.ФактическаяПозиция
    actual = conn.РегистрыСведений.ДатаАктуальностиФактическойПозиции
    sub = conn.Справочники.Субпортфели.ПустаяСсылка()
    account = conn.Справочники.СчетаУчетаЕПС.ПустаяСсылка()
    model = conn.Перечисления.ТипыПортфелей.ПустаяСсылка()
    for index, portfolio in enumerate(portfolios, start=1):
        mark = actual.СоздатьМенеджерЗаписи()
        mark.Портфель = portfolio
        mark.Дата = day
        mark.Записать()
        record_set = position.СоздатьНаборЗаписей()
        record_set.Отбор.Портфель.Установить(portfolio)
        record_set.Отбор.Дата.Установить(day)
        for asset, place, cost in rows:
            row = record_set.Добавить()
            row.Период = day
            row.Дата = day
            row.Портфель = portfolio
            row.Актив = asset
            row.МестоХранения = place
            row.Субпортфель = sub
            row.ДатаПартии = empty
            row.ТипПортфеля = model
            row.СчетУчета = account
            row.Количество = 10
            row.Стоимость = cost
            row.АмортизированнаяСтоимость = cost
            row.НКД = 0
            row.Задолженность = 0
            row.СуммаДенежныхСредствСЗадолженностью = 0
            row.ПервоначальнаяСтоимость = cost
        record_set.Записать()
        if index % 200 == 0:
            fo.safe_print("position %s" % index)


def main():
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(fo.CONN)
    names = existing_names(conn)
    rub = fo.find_by_name(conn, "Валюты", "RUB")
    rows = template_rows(conn)
    limits = [(ref, "", "") for ref in limit_refs(conn)]
    limit_class = fo.ensure_class(conn)
    fo.safe_print("have %s template %s limits %s" % (len(names), len(rows), len(limits)))

    created = []
    tail = []
    normal = []
    for index in range(1, TARGET + 1):
        name = portfolio_name(index)
        if name in names:
            continue
        item = conn.Справочники.Портфели.СоздатьЭлемент()
        item.Наименование = name
        item.Валюта = rub
        item.Записать()
        created.append(item.Ссылка)
        if index >= TAIL_FROM:
            tail.append(item.Ссылка)
        else:
            normal.append(item.Ссылка)
        if len(created) % 100 == 0:
            fo.safe_print("created %s" % len(created))
    fo.safe_print("new portfolios %s" % len(created))
    if not created:
        fo.safe_print("EXPAND DONE nothing to add")
        return

    fo.write_rsa(conn, created)
    fo.safe_print("rsa %s" % len(created))
    write_copied_positions(conn, normal, rows)
    write_copied_positions(conn, tail, [(asset, place, cost * 4) for asset, place, cost in rows])
    fo.safe_print("positions %s" % len(created))
    posted = fo.install(conn, created, limits, limit_class)
    fo.safe_print("EXPAND DONE created %s posted %s" % (len(created), posted))


if __name__ == "__main__":
    main()
