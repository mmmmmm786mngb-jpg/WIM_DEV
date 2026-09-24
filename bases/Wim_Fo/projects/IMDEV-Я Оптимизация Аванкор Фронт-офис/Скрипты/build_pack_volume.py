#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Объемные данные FO_VOL: 100 портфелей, активы, позиция, 50 лимитов.
Большая часть портфелей должна проходить лимиты доли, хвост должен нарушать.
"""

import os
import traceback
from datetime import datetime

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
PORTFOLIO_COUNT = 100
OK_COUNT = 80


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def connect():
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN)


def query_rows(conn, text, params=None):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for key, value in params.items():
            query.УстановитьПараметр(key, value)
    selection = query.Выполнить().Выбрать()
    rows = []
    while selection.Следующий():
        rows.append((
            selection.Ссылка if hasattr(selection, "Ссылка") else None,
            conn.String(selection.Имя) if hasattr(selection, "Имя") else "",
        ))
    return rows


def query_one(conn, text, params=None):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for key, value in params.items():
            query.УстановитьПараметр(key, value)
    selection = query.Выполнить().Выбрать()
    if not selection.Следующий():
        return None
    return selection.Ссылка


def find_by_name(conn, catalog, name):
    ref = getattr(conn.Справочники, catalog).НайтиПоНаименованию(name, True)
    if ref.Пустая():
        return None
    return ref


def type_of(conn, name):
    return conn.NewObject("ОписаниеТипов", name).Типы().Get(0)


def empty_date(conn):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(1, 1, 1) КАК D"
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    return selection.D


def filter_string(conn, field_name, right_value):
    settings = conn.NewObject("НастройкиКомпоновкиДанных")
    item = settings.Отбор.Элементы.Добавить(type_of(conn, "ЭлементОтбораКомпоновкиДанных"))
    item.Использование = True
    item.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", field_name)
    item.ВидСравнения = conn.ВидСравненияКомпоновкиДанных.Равно
    item.ПравоеЗначение = right_value
    return conn.ЗначениеВСтрокуВнутр(conn.NewObject("ХранилищеЗначения", settings))


def greater_filter(conn):
    settings = conn.NewObject("НастройкиКомпоновкиДанных")
    item = settings.Отбор.Элементы.Добавить(type_of(conn, "ЭлементОтбораКомпоновкиДанных"))
    item.Использование = True
    item.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", "Количество")
    item.ВидСравнения = conn.ВидСравненияКомпоновкиДанных.Больше
    item.ПравоеЗначение = 1
    return conn.ЗначениеВСтрокуВнутр(conn.NewObject("ХранилищеЗначения", settings))


def ensure_portfolios(conn, currency):
    refs = []
    for index in range(1, PORTFOLIO_COUNT + 1):
        name = "FO_VOL %03d" % index
        found = find_by_name(conn, "Портфели", name)
        if found is None:
            item = getattr(conn.Справочники, "Портфели").СоздатьЭлемент()
            item.Наименование = name
            if currency is not None:
                item.Валюта = currency
            item.Записать()
            found = item.Ссылка
        refs.append(found)
        if index % 20 == 0:
            safe_print("portfolios " + str(index))
    return refs


def ensure_assets(conn, kinds):
    """Берет три уже записанных актива. Новые без полного набора реквизитов база не пишет."""
    asset_query = conn.NewObject("Запрос")
    asset_query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 3 Ссылка, Наименование КАК Имя, ВидАктива "
        "ИЗ Справочник.Активы ГДЕ НЕ ПометкаУдаления"
    )
    selection = asset_query.Выполнить().Выбрать()
    assets = []
    specs = []
    costs = ((500, 20), (100, 10000), (20, 10))
    index = 0
    while selection.Следующий() and index < 3:
        assets.append(selection.Ссылка)
        specs.append((conn.String(selection.Имя), selection.ВидАктива, costs[index][0], costs[index][1]))
        safe_print("asset use " + conn.String(selection.Имя))
        index += 1
    if len(assets) < 2:
        raise RuntimeError("need at least 2 assets")
    return assets, specs


def write_position(conn, portfolios, assets, specs, day, empty):
    position = getattr(conn.РегистрыСведений, "ФактическаяПозиция")
    actual = getattr(conn.РегистрыСведений, "ДатаАктуальностиФактическойПозиции")
    place = getattr(conn.Справочники, "МестаХранения").ПустаяСсылка()
    sub = getattr(conn.Справочники, "Субпортфели").ПустаяСсылка()
    account = getattr(conn.Справочники, "СчетаУчетаЕПС").ПустаяСсылка()
    model = conn.Перечисления.ТипыПортфелей.ПустаяСсылка()
    for index, portfolio in enumerate(portfolios, start=1):
        mark = actual.СоздатьМенеджерЗаписи()
        mark.Портфель = portfolio
        mark.Дата = day
        mark.Записать()
        record_set = position.СоздатьНаборЗаписей()
        record_set.Отбор.Портфель.Установить(portfolio)
        record_set.Отбор.Дата.Установить(day)
        record_set.Прочитать()
        record_set.Очистить()
        for asset_index, asset in enumerate(assets):
            cost = specs[asset_index][2] if index <= OK_COUNT else specs[asset_index][3]
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
        if index % 20 == 0:
            safe_print("position " + str(index))


def fill_limit(conn, item, name, kind, dataset, limit_class, variant, packed, query_text, qualifier):
    item.Наименование = name
    item.СпособНастройкиЛимита = conn.Перечисления.СпособыНастройкиЛимита.Внутренний
    item.ВидЛимита = kind
    item.НаборДанныхДляПроверкиЛимитов = dataset
    item.КлассЛимита = limit_class
    if variant is not None and str(kind).find("Поручение") < 0:
        try:
            item.ВариантПроверкиПорога = variant
        except Exception:
            pass
    item.Тестовый = False
    item.Подтвержден = True
    item.НастройкиПодготовкиСпискаАктивов = packed
    item.УсловияОтбораОсновные = query_text
    if qualifier:
        item.Квалификаторы.Очистить()
        row = item.Квалификаторы.Добавить()
        row.Описание = name
        row.Квалификатор = packed
        row.УсловияОтбора = query_text
    item.Записать()
    return item.Ссылка


def ensure_limits(conn, position_dataset, order_dataset, limit_class, variant, bond_kind):
    limits = []
    packed_bond = filter_string(conn, "ВидАктива", bond_kind)
    packed_any = filter_string(conn, "ВидАктива", bond_kind)
    packed_greater = greater_filter(conn)
    structure = conn.Перечисления.ВидыЛимитов.Структура
    composition = conn.Перечисления.ВидыЛимитов.Состав
    order_kind = conn.Перечисления.ВидыЛимитов.Поручение
    for index in range(1, 31):
        name = "FO_VOL S%02d" % index
        limits.append(save_limit(
            conn, name, structure, position_dataset, limit_class, variant,
            packed_bond, "(#Т.ВидАктива = &П0_О)", False))
    for index in range(1, 13):
        name = "FO_VOL C%02d" % index
        limits.append(save_limit(
            conn, name, composition, position_dataset, limit_class, variant,
            packed_any, "(#Т.ВидАктива = &П0_К)", True))
    for index in range(1, 6):
        name = "FO_VOL O%02d" % index
        limits.append(save_limit(
            conn, name, order_kind, order_dataset, limit_class, None,
            packed_any, "(#Т.ВидАктива = &П0_К)", True))
    for index in range(1, 4):
        name = "FO_VOL X%02d" % index
        limits.append(save_limit(
            conn, name, structure, position_dataset, limit_class, variant,
            packed_greater, "(#Т.Количество > &П0_О)", False))
    safe_print("limits " + str(len(limits)))
    return limits


def save_limit(conn, name, kind, dataset, limit_class, variant, packed, query_text, qualifier):
    found = find_by_name(conn, "Лимиты", name)
    if found is None:
        item = getattr(conn.Справочники, "Лимиты").СоздатьЭлемент()
    else:
        item = found.ПолучитьОбъект()
        if qualifier:
            item.Квалификаторы.Очистить()
    ref = fill_limit(conn, item, name, kind, dataset, limit_class, variant, packed, query_text, qualifier)
    return ref


def ensure_installations(conn, portfolios, limits, limit_class):
    settings = conn.NewObject("Структура")
    settings.Вставить("Порог", 30)
    settings.Вставить("Комментарий", "FO_VOL")
    storage = conn.NewObject("ХранилищеЗначения", settings)
    for index, portfolio in enumerate(portfolios, start=1):
        rows_query = conn.NewObject("Запрос")
        rows_query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов КАК Т "
            "ГДЕ Т.Проведен И Т.ОбъектНазначения = &Портфель И НЕ Т.ПометкаУдаления"
        )
        rows_query.УстановитьПараметр("Портфель", portfolio)
        selection = rows_query.Выполнить().Выбрать()
        if selection.Следующий():
            doc = selection.Ссылка.ПолучитьОбъект()
        else:
            doc = getattr(conn.Документы, "УстановкаЛимитов").СоздатьДокумент()
            doc.Дата = datetime.now().replace(microsecond=0)
            doc.ВидОперации = conn.Перечисления.ВидыОперацийУстановкиЛимитов.ПоПортфелю
            doc.ОбъектНазначения = portfolio
            doc.КлассЛимита = limit_class
            doc.Подтвержден = True
        present = {}
        for line_index in range(doc.Лимиты.Количество()):
            line = doc.Лимиты.Получить(line_index)
            present[conn.String(line.Лимит)] = line
        for limit_ref in limits:
            key = conn.String(limit_ref)
            line = present.get(key)
            if line is None:
                line = doc.Лимиты.Добавить()
                line.Лимит = limit_ref
            line.НастройкиЛимита = storage
            line.НастройкиУстановлены = True
        doc.Записать(conn.РежимЗаписиДокумента.Проведение)
        if index % 20 == 0:
            safe_print("installations " + str(index))


def main():
    conn = connect()
    tech = query_one(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.Портфели ГДЕ Наименование = \"Технический портфель\"",
    )
    currency = None
    if tech is not None:
        currency = tech.ПолучитьОбъект().Валюта
    kinds = []
    kind_query = conn.NewObject("Запрос")
    kind_query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 5 Ссылка, Наименование КАК Имя "
        "ИЗ ПланВидовХарактеристик.ВидыАктивов ГДЕ НЕ ПометкаУдаления"
    )
    kind_sel = kind_query.Выполнить().Выбрать()
    while kind_sel.Следующий():
        kinds.append(kind_sel.Ссылка)
        safe_print("kind " + conn.String(kind_sel.Имя))
    if not kinds:
        raise RuntimeError("no asset kinds")
    position_dataset = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", "FO_GEN набор позиции")
    order_dataset = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", "FO_GEN набор")
    if position_dataset is None or order_dataset is None:
        raise RuntimeError("FO_GEN datasets missing")
    limit_class = query_one(
        conn, "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.КлассыЛимитов ГДЕ НЕ ПометкаУдаления")
    variant = query_one(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.ВариантыПроверкиПороговЛимитов "
        "ГДЕ НЕ ПометкаУдаления И Наименование ПОДОБНО \"%РСА%\"",
    )
    if variant is None:
        variant = query_one(
            conn,
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.ВариантыПроверкиПороговЛимитов ГДЕ НЕ ПометкаУдаления",
        )
    safe_print("variant " + conn.String(variant))
    portfolios = ensure_portfolios(conn, currency)
    assets, specs = ensure_assets(conn, kinds)
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    write_position(conn, portfolios, assets, specs, day, empty_date(conn))
    limits = ensure_limits(
        conn, position_dataset, order_dataset, limit_class, variant, specs[min(1, len(specs) - 1)][1])
    structure_limits = limits[:30]
    ensure_installations(conn, portfolios, structure_limits + limits[30:42], limit_class)
    safe_print("ready portfolios=%s limits=%s ok_until=%s" % (len(portfolios), len(limits), OK_COUNT))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        safe_print(traceback.format_exc()[-1800:])
        raise
