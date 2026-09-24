#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Доводит число портфелей FO_SHAPE до 3000.
1-80 и 101-2400 без нарушения, 81-100 и 2401-3000 в хвосте с нарушением.
Лимиты пост-контроля ставятся на каждый новый портфель.
"""

import importlib.util
import os
from datetime import datetime

import pythoncom

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("shape", os.path.join(HERE, "build_shape_data.py"))
shape = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shape)

TARGET = 3000
OK_UNTIL = 2400


def portfolio_name(index):
    if index < 1000:
        return "FO_SHAPE %03d" % index
    return "FO_SHAPE %d" % index


def existing_names(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Наименование ИЗ Справочник.Портфели "
        "ГДЕ Наименование ПОДОБНО \"FO_SHAPE %\""
    )
    selection = query.Выполнить().Выбрать()
    names = set()
    while selection.Следующий():
        names.add(conn.String(selection.Наименование))
    return names


def post_limits(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты ГДЕ НЕ ПометкаУдаления И ("
        "Наименование ПОДОБНО \"FO_SHAPE S%\" ИЛИ Наименование ПОДОБНО \"FO_SHAPE C%\" "
        "ИЛИ Наименование ПОДОБНО \"FO_REP S%\" ИЛИ Наименование ПОДОБНО \"FO_REP C%\") "
        "УПОРЯДОЧИТЬ ПО Наименование"
    )
    selection = query.Выполнить().Выбрать()
    refs = []
    while selection.Следующий():
        refs.append(selection.Ссылка)
    return refs


def limit_class(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 Т.КлассЛимита КАК Класс "
        "ИЗ Документ.УстановкаЛимитов КАК Т "
        "ГДЕ Т.Проведен И Т.ОбъектНазначения.Наименование = \"FO_SHAPE 001\""
    )
    selection = query.Выполнить().Выбрать()
    if not selection.Следующий():
        raise RuntimeError("no installation for FO_SHAPE 001")
    return selection.Класс


def asset_specs(conn):
    shape.ensure_assets(conn)
    rows = []
    for name, ok_cost, tail_cost in (
        ("FO_SHAPE OFZ RUB", 700, 100),
        ("FO_SHAPE BOND USD", 50, 600),
        ("FO_SHAPE SHARE RUB", 100, 50),
        ("FO_SHAPE SHARE USD", 20, 0),
        ("FO_SHAPE FUND RUB", 80, 50),
        ("RUB", 40, 200),
        ("USD", 10, 0),
        ("FO_SHAPE SUB RF", 0, 30),
    ):
        ref = shape.find_by_name(conn, "Активы", name)
        if ref is None:
            raise RuntimeError("asset " + name)
        rows.append((ref, ok_cost, tail_cost))
    return rows


def write_one_position(conn, portfolio, index, specs, day, empty, place, sub, account, model, position, actual):
    mark = actual.СоздатьМенеджерЗаписи()
    mark.Портфель = portfolio
    mark.Дата = day
    mark.Записать()
    record_set = position.СоздатьНаборЗаписей()
    record_set.Отбор.Портфель.Установить(portfolio)
    record_set.Отбор.Дата.Установить(day)
    record_set.Очистить()
    for asset, ok_cost, tail_cost in specs:
        cost = ok_cost if index <= OK_UNTIL else tail_cost
        if cost == 0:
            continue
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


def install_one(conn, portfolio, limits, limit_class_ref):
    doc = getattr(conn.Документы, "УстановкаЛимитов").СоздатьДокумент()
    doc.Дата = datetime.now().replace(microsecond=0)
    doc.ВидОперации = conn.Перечисления.ВидыОперацийУстановкиЛимитов.ПоПортфелю
    doc.ОбъектНазначения = portfolio
    doc.КлассЛимита = limit_class_ref
    doc.Подтвержден = False
    for limit_ref in limits:
        line = doc.Лимиты.Добавить()
        line.Лимит = limit_ref
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)


def main():
    pythoncom.CoInitialize()
    conn = shape.connect()
    currency = shape.currency_ref(conn, "RUB")
    names = existing_names(conn)
    limits = post_limits(conn)
    limit_class_ref = limit_class(conn)
    specs = asset_specs(conn)
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    empty = shape.empty_date(conn)
    position = getattr(conn.РегистрыСведений, "ФактическаяПозиция")
    actual = getattr(conn.РегистрыСведений, "ДатаАктуальностиФактическойПозиции")
    rsa = getattr(conn.РегистрыСведений, "РегистрРСА_СЧА")
    place = getattr(conn.Справочники, "МестаХранения").ПустаяСсылка()
    sub = getattr(conn.Справочники, "Субпортфели").ПустаяСсылка()
    account = getattr(conn.Справочники, "СчетаУчетаЕПС").ПустаяСсылка()
    model = conn.Перечисления.ТипыПортфелей.ПустаяСсылка()
    shape.safe_print("limits %s existing %s" % (len(limits), len(names)))
    created = 0
    for index in range(1, TARGET + 1):
        name = portfolio_name(index)
        if name in names:
            continue
        item = getattr(conn.Справочники, "Портфели").СоздатьЭлемент()
        item.Наименование = name
        item.Валюта = currency
        item.Записать()
        portfolio = item.Ссылка
        record = rsa.СоздатьМенеджерЗаписи()
        record.Период = day
        record.Портфель = portfolio
        record.РСА = 1000
        record.СЧА = 1000
        record.СА = 1000
        record.Записать()
        write_one_position(
            conn, portfolio, index, specs, day, empty, place, sub, account, model, position, actual)
        install_one(conn, portfolio, limits, limit_class_ref)
        created += 1
        if created % 50 == 0:
            shape.safe_print("created %s last %s" % (created, name))
    shape.safe_print("EXPAND DONE created %s" % created)


if __name__ == "__main__":
    main()
