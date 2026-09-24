#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовые данные FO_SHAPE по форме ночной проверки из выгрузки лимитов.

Обычный фронт-офис: один набор 482 без активов в РЕПО, короткие отборы
по виду актива и валюте номинала, вариант процент от РСА, часть лимитов
с одним текстом отбора и разными порогами. Розница в том же наборе
представлена лимитами состава с одним квалификатором и лимитами поручений
с пустым основным отбором.
"""

import os
import traceback
from datetime import datetime

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
PORTFOLIO_COUNT = 100
OK_COUNT = 80
MARK = "FO_SHAPE"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def connect():
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN)


def type_of(conn, name):
    return conn.NewObject("ОписаниеТипов", name).Типы().Get(0)


def find_by_name(conn, catalog, name):
    ref = getattr(conn.Справочники, catalog).НайтиПоНаименованию(name, True)
    if ref.Пустая():
        return None
    return ref


def query_date(conn, year, month, day):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%s, %s, %s) КАК D" % (year, month, day)
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    return selection.D


def empty_date(conn):
    return query_date(conn, 1, 1, 1)


def kind_ref(conn, name):
    return getattr(conn.ПланыВидовХарактеристик.ВидыАктивов, name)


def currency_ref(conn, name):
    ref = find_by_name(conn, "Валюты", name)
    if ref is None:
        raise RuntimeError("currency " + name)
    return ref


def ensure_issuer(conn):
    name = "FO_SHAPE эмитент"
    found = find_by_name(conn, "Контрагенты", name)
    if found is not None:
        return found
    item = getattr(conn.Справочники, "Контрагенты").СоздатьЭлемент()
    item.Наименование = name
    item.Записать()
    return item.Ссылка


def ensure_bond(conn, name, kind, currency, issuer, maturity):
    found = find_by_name(conn, "Облигации", name)
    if found is not None:
        return found
    item = getattr(conn.Справочники, "Облигации").СоздатьЭлемент()
    item.Наименование = name
    item.ВидАктива = kind
    item.ВалютаНоминальнойСтоимости = currency
    item.НоминальнаяСтоимость = 1000
    item.Эмитент = issuer
    item.ДатаПогашения = maturity
    item.Записать()
    return item.Ссылка


def ensure_share(conn, name, kind, currency, issuer):
    found = find_by_name(conn, "Акции", name)
    if found is not None:
        return found
    item = getattr(conn.Справочники, "Акции").СоздатьЭлемент()
    item.Наименование = name
    item.ВидАктива = kind
    item.ВалютаНоминальнойСтоимости = currency
    item.Эмитент = issuer
    item.Записать()
    return item.Ссылка


def ensure_fund(conn, name, kind, currency, issuer):
    found = find_by_name(conn, "ПаиПИФ", name)
    if found is not None:
        return found
    item = getattr(conn.Справочники, "ПаиПИФ").СоздатьЭлемент()
    item.Наименование = name
    item.ВидАктива = kind
    item.ВалютаНоминальнойСтоимости = currency
    item.Эмитент = issuer
    item.Записать()
    return item.Ссылка


def ensure_asset(conn, name, kind, currency, issuer, obj):
    found = find_by_name(conn, "Активы", name)
    if found is not None:
        return found
    item = getattr(conn.Справочники, "Активы").СоздатьЭлемент()
    item.Наименование = name
    item.ВидАктива = kind
    item.ВалютаНоминальнойСтоимости = currency
    item.Эмитент = issuer
    item.Объект = obj
    item.Записать()
    return item.Ссылка


def existing_currency_asset(conn, name):
    found = find_by_name(conn, "Активы", name)
    if found is None:
        raise RuntimeError("currency asset " + name)
    return found


def ensure_assets(conn):
    issuer = ensure_issuer(conn)
    rub = currency_ref(conn, "RUB")
    usd = currency_ref(conn, "USD")
    maturity = query_date(conn, 2030, 12, 31)
    bond_rub_kind = kind_ref(conn, "ОблигацииГосРФ")
    bond_fx_kind = kind_ref(conn, "ОблигацииПрочихНерезидентов")
    share_rub_kind = kind_ref(conn, "АкцииОбыкновенныеАО")
    share_fx_kind = kind_ref(conn, "АкцииИГ")
    fund_kind = kind_ref(conn, "ПаиПИФ")
    specs = []
    bond_rub = ensure_bond(conn, "FO_SHAPE OFZ RUB", bond_rub_kind, rub, issuer, maturity)
    specs.append(("bond_rub", ensure_asset(conn, "FO_SHAPE OFZ RUB", bond_rub_kind, rub, issuer, bond_rub), 700, 100))
    bond_fx = ensure_bond(conn, "FO_SHAPE BOND USD", bond_fx_kind, usd, issuer, maturity)
    specs.append(("bond_fx", ensure_asset(conn, "FO_SHAPE BOND USD", bond_fx_kind, usd, issuer, bond_fx), 50, 600))
    share_rub = ensure_share(conn, "FO_SHAPE SHARE RUB", share_rub_kind, rub, issuer)
    specs.append(("share_rub", ensure_asset(conn, "FO_SHAPE SHARE RUB", share_rub_kind, rub, issuer, share_rub), 100, 50))
    share_fx = ensure_share(conn, "FO_SHAPE SHARE USD", share_fx_kind, usd, issuer)
    specs.append(("share_fx", ensure_asset(conn, "FO_SHAPE SHARE USD", share_fx_kind, usd, issuer, share_fx), 20, 0))
    fund = ensure_fund(conn, "FO_SHAPE FUND RUB", fund_kind, rub, issuer)
    specs.append(("fund", ensure_asset(conn, "FO_SHAPE FUND RUB", fund_kind, rub, issuer, fund), 80, 50))
    specs.append(("cash_rub", existing_currency_asset(conn, "RUB"), 40, 200))
    specs.append(("cash_fx", existing_currency_asset(conn, "USD"), 10, 0))
    tail_kind = kind_ref(conn, "ОблигацииСубРФ")
    tail_bond = ensure_bond(conn, "FO_SHAPE SUB RF", tail_kind, rub, issuer, maturity)
    specs.append(("tail_bond", ensure_asset(conn, "FO_SHAPE SUB RF", tail_kind, rub, issuer, tail_bond), 0, 30))
    safe_print("assets " + str(len(specs)))
    return {
        "rub": rub,
        "usd": usd,
        "bonds": kind_ref(conn, "Облигации"),
        "bond_rub": bond_rub_kind,
        "bond_fx": bond_fx_kind,
        "shares": kind_ref(conn, "Акции"),
        "share_rub": share_rub_kind,
        "share_fx": share_fx_kind,
        "funds": fund_kind,
        "cash": kind_ref(conn, "Валюты"),
        "receipts": kind_ref(conn, "ДепозитарныеРасписки"),
        "tail_bond": tail_kind,
        "specs": specs,
    }


def ensure_portfolios(conn, currency):
    refs = []
    for index in range(1, PORTFOLIO_COUNT + 1):
        name = "FO_SHAPE %03d" % index
        found = find_by_name(conn, "Портфели", name)
        if found is None:
            item = getattr(conn.Справочники, "Портфели").СоздатьЭлемент()
            item.Наименование = name
            item.Валюта = currency
            item.Записать()
            found = item.Ссылка
        refs.append(found)
        if index % 25 == 0:
            safe_print("portfolios " + str(index))
    return refs


def write_market_value(conn, portfolios):
    """РСА для варианта процента от РСА читается из регистра, а не из строк позиции."""
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    register = getattr(conn.РегистрыСведений, "РегистрРСА_СЧА")
    for index, portfolio in enumerate(portfolios, start=1):
        record = register.СоздатьМенеджерЗаписи()
        record.Период = day
        record.Портфель = portfolio
        record.РСА = 1000
        record.СЧА = 1000
        record.СА = 1000
        record.Записать()
        if index % 25 == 0:
            safe_print("rsa " + str(index))


def write_position(conn, portfolios, specs):
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    empty = empty_date(conn)
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
        for spec in specs:
            cost = spec[2] if index <= OK_COUNT else spec[3]
            if cost == 0:
                continue
            row = record_set.Добавить()
            row.Период = day
            row.Дата = day
            row.Портфель = portfolio
            row.Актив = spec[1]
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
        if index % 25 == 0:
            safe_print("position " + str(index))


def ensure_dataset(conn, limit_class):
    source_name = "FO_SHAPE источник позиции"
    source = find_by_name(conn, "ИсточникиДанныхДляПроверкиЛимитов", source_name)
    if source is None:
        item = getattr(conn.Справочники, "ИсточникиДанныхДляПроверкиЛимитов").СоздатьЭлемент()
        item.Наименование = source_name
        item.ВидИсточника = conn.Перечисления.ВидыОсновныхИсточниковДанных.ТекущаяПозиция
        item.КлассЛимита = limit_class
        item.Записать()
        source = item.Ссылка
    order_source_name = "FO_SHAPE источник поручения"
    order_source = find_by_name(conn, "ИсточникиДанныхДляПроверкиЛимитов", order_source_name)
    if order_source is None:
        item = getattr(conn.Справочники, "ИсточникиДанныхДляПроверкиЛимитов").СоздатьЭлемент()
        item.Наименование = order_source_name
        item.ВидИсточника = conn.Перечисления.ВидыОсновныхИсточниковДанных.Поручение
        item.КлассЛимита = limit_class
        item.Записать()
        order_source = item.Ссылка
    dataset = ensure_dataset_item(
        conn, "FO_SHAPE набор 482", source, limit_class, True)
    order_dataset = ensure_dataset_item(
        conn, "FO_SHAPE набор поручение", order_source, limit_class, False)
    return dataset, order_dataset


def ensure_dataset_item(conn, name, source, limit_class, with_position):
    found = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", name)
    item = getattr(conn.Справочники, "НаборыДанныхДляПроверкиЛимитов").СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
    item.Наименование = name
    item.ИсточникДанных = source
    item.КлассЛимита = limit_class
    item.ИспользоватьРепрайсинг = False
    item.ИспользоватьСвойДеноминатор = False
    item.ИспользоватьУКР = False
    item.ПриводитьКВалютеПорогов = False
    item.ОграничиватьПлановуюПозициюПоДатеРасчетов = True
    item.ВсегдаИспользоватьСоставПозицииИзНабораДанных = True
    item.СоставПозиции.Очистить()
    if with_position:
        kinds = conn.Перечисления.ВидыПозицийПортфеля
        for kind in (kinds.Плановая, kinds.Прогнозная, kinds.ПрогнознаяАктивыВОбратномРЕПО, kinds.Фактическая):
            row = item.СоставПозиции.Добавить()
            row.ВидПозиции = kind
    item.Записать()
    return item.Ссылка


def pack_filter(conn, parts):
    settings = conn.NewObject("НастройкиКомпоновкиДанных")
    group = settings.Отбор.Элементы.Добавить(type_of(conn, "ГруппаЭлементовОтбораКомпоновкиДанных"))
    group.Использование = True
    group.ТипГруппы = conn.ТипГруппыЭлементовОтбораКомпоновкиДанных.ГруппаИ
    comparisons = conn.ВидСравненияКомпоновкиДанных
    names = {"eq": comparisons.Равно, "ne": comparisons.НеРавно, "in": comparisons.ВИерархии}
    texts = []
    for index, (field, mode, value) in enumerate(parts):
        element = group.Элементы.Добавить(type_of(conn, "ЭлементОтбораКомпоновкиДанных"))
        element.Использование = True
        element.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", field)
        element.ВидСравнения = names[mode]
        element.ПравоеЗначение = value
        sign = {"eq": "=", "ne": "<>", "in": "В ИЕРАРХИИ"}[mode]
        texts.append("(#Т.%s %s (&П%s_О))" % (field, sign, index))
    query_text = " И ".join(texts)
    packed = conn.ЗначениеВСтрокуВнутр(conn.NewObject("ХранилищеЗначения", settings))
    return packed, query_text


def ensure_variant(conn):
    name = "FO_SHAPE процент от РСА"
    found = find_by_name(conn, "ВариантыПроверкиПороговЛимитов", name)
    item = getattr(conn.Справочники, "ВариантыПроверкиПороговЛимитов").СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
    item.Наименование = name
    item.Вариант = conn.Перечисления.ВариантыПроверкиПороговЛимитов.ПроцентОтРСА
    item.ФункцияПроверкиПорога = conn.Перечисления.ВидыФункцийПроверкиПороговЛимитов.ПоОбщемуИтогу
    item.Записать()
    return item.Ссылка


def save_limit(conn, name, kind, dataset, limit_class, variant, packed, query_text, qualifier):
    found = find_by_name(conn, "Лимиты", name)
    item = getattr(conn.Справочники, "Лимиты").СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
    item.Наименование = name
    item.СпособНастройкиЛимита = conn.Перечисления.СпособыНастройкиЛимита.Внутренний
    item.ВидЛимита = kind
    item.НаборДанныхДляПроверкиЛимитов = dataset
    item.КлассЛимита = limit_class
    item.Тестовый = False
    item.Подтвержден = False
    item.ПакетныйРежим = False
    item.ИспользоватьПулДанныхИзМодификатора = False
    if variant is not None:
        item.ВариантПроверкиПорога = variant
    item.НастройкиПодготовкиСпискаАктивов = "" if qualifier and kind == conn.Перечисления.ВидыЛимитов.Поручение else packed
    item.УсловияОтбораОсновные = "" if qualifier and kind == conn.Перечисления.ВидыЛимитов.Поручение else query_text
    item.Квалификаторы.Очистить()
    if qualifier:
        row = item.Квалификаторы.Добавить()
        row.Описание = name
        row.Квалификатор = packed
        row.УсловияОтбора = query_text
        if kind == conn.Перечисления.ВидыЛимитов.Поручение:
            item.НастройкиПодготовкиСпискаАктивов = ""
            item.УсловияОтбораОсновные = ""
    item.Записать()
    try:
        getattr(conn.Справочники, "Лимиты").СохранитьНастройкиЛимита(item.Ссылка)
    except Exception as error:
        safe_print("settings cache " + name + " " + str(error)[:180])
    return item.Ссылка


def ensure_limits(conn, dataset, order_dataset, limit_class, variant, refs):
    structure = conn.Перечисления.ВидыЛимитов.Структура
    composition = conn.Перечисления.ВидыЛимитов.Состав
    order_kind = conn.Перечисления.ВидыЛимитов.Поручение
    rub = refs["rub"]
    usd = refs["usd"]
    bond_rub = pack_filter(conn, [("ВидАктива", "in", refs["bond_rub"]), ("ВалютаНоминала", "eq", rub)])
    bond_fx = pack_filter(conn, [("ВидАктива", "in", refs["bonds"]), ("ВалютаНоминала", "ne", rub)])
    share_rub = pack_filter(conn, [("ВидАктива", "in", refs["shares"]), ("ВалютаНоминала", "eq", rub)])
    share_fx = pack_filter(conn, [("ВидАктива", "in", refs["share_fx"]), ("ВалютаНоминала", "eq", usd)])
    fund = pack_filter(conn, [("ВидАктива", "eq", refs["funds"]), ("ВалютаНоминала", "eq", rub)])
    cash_rub = pack_filter(conn, [("ВидАктива", "eq", refs["cash"]), ("ВалютаНоминала", "eq", rub)])
    cash_fx = pack_filter(conn, [("ВидАктива", "eq", refs["cash"]), ("ВалютаНоминала", "ne", rub)])
    receipts = pack_filter(conn, [("ВидАктива", "in", refs["receipts"])])
    tail_only = pack_filter(conn, [("ВидАктива", "in", refs["tail_bond"])])
    order_bond = pack_filter(conn, [("ВидАктива", "eq", refs["bond_rub"])])
    order_absent = pack_filter(conn, [("ВидАктива", "in", refs["receipts"])])
    plan = [
        ("FO_SHAPE S01", structure, dataset, bond_rub, False, 80),
        ("FO_SHAPE S02", structure, dataset, bond_rub, False, 90),
        ("FO_SHAPE S03", structure, dataset, bond_rub, False, 80),
        ("FO_SHAPE S04", structure, dataset, bond_fx, False, 10),
        ("FO_SHAPE S05", structure, dataset, bond_fx, False, 10),
        ("FO_SHAPE S06", structure, dataset, bond_fx, False, 10),
        ("FO_SHAPE S07", structure, dataset, bond_fx, False, 70),
        ("FO_SHAPE S08", structure, dataset, share_rub, False, 20),
        ("FO_SHAPE S09", structure, dataset, share_rub, False, 25),
        ("FO_SHAPE S10", structure, dataset, share_fx, False, 15),
        ("FO_SHAPE S11", structure, dataset, fund, False, 15),
        ("FO_SHAPE S12", structure, dataset, fund, False, 20),
        ("FO_SHAPE S13", structure, dataset, cash_rub, False, 10),
        ("FO_SHAPE S14", structure, dataset, cash_rub, False, 10),
        ("FO_SHAPE S15", structure, dataset, cash_rub, False, 50),
        ("FO_SHAPE S16", structure, dataset, cash_fx, False, 5),
        ("FO_SHAPE S17", structure, dataset, receipts, False, 1),
        ("FO_SHAPE S18", structure, dataset, receipts, False, 1),
        ("FO_SHAPE C01", composition, dataset, tail_only, True, None),
        ("FO_SHAPE C02", composition, dataset, tail_only, True, None),
        ("FO_SHAPE C03", composition, dataset, receipts, True, None),
        ("FO_SHAPE C04", composition, dataset, receipts, True, None),
        ("FO_SHAPE C05", composition, dataset, receipts, True, None),
        ("FO_SHAPE C06", composition, dataset, receipts, True, None),
        ("FO_SHAPE O01", order_kind, order_dataset, order_bond, True, None),
        ("FO_SHAPE O02", order_kind, order_dataset, order_absent, True, None),
    ]
    limits = []
    for name, kind, limit_dataset, packed_pair, qualifier, threshold in plan:
        packed, query_text = packed_pair
        use_variant = None if kind == order_kind else variant
        limits.append((
            save_limit(conn, name, kind, limit_dataset, limit_class, use_variant, packed, query_text, qualifier),
            threshold,
            kind != order_kind and kind != composition,
        ))
        safe_print("limit " + name)
    return limits


def ensure_thresholds(conn, limits):
    manager = getattr(conn.Справочники, "НастройкиПороговДляПроверкиЛимитов")
    register = getattr(conn.РегистрыСведений, "ПорогиЛимитов")
    empty_portfolio = getattr(conn.Справочники, "Портфели").ПустаяСсылка()
    period = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cache = {}
    written = 0
    for limit_ref, threshold, need in limits:
        if not need or threshold is None:
            continue
        setting = cache.get(threshold)
        if setting is None:
            name = "FO_SHAPE порог %s" % threshold
            found = find_by_name(conn, "НастройкиПороговДляПроверкиЛимитов", name)
            item = manager.СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
            item.Наименование = name
            item.ИспользоватьРасширеннуюУстановкуПорогов = False
            item.СложныеПороги.Очистить()
            row = item.СложныеПороги.Добавить()
            row.ПоУмолчанию = True
            row.МаксДоляЖелтаяЗона = max(threshold - 5, 1)
            row.МаксДоляКраснаяЗона = threshold
            item.Записать()
            setting = item.Ссылка
            cache[threshold] = setting
        record = register.СоздатьМенеджерЗаписи()
        record.Период = period
        record.Лимит = limit_ref
        record.Портфель = empty_portfolio
        record.НастройкаПороговДляПроверкиЛимитов = setting
        record.Записать()
        written += 1
    safe_print("thresholds " + str(written))


def ensure_installations(conn, portfolios, limits, limit_class):
    structure_and_composition = []
    order_limits = []
    for limit_ref, _threshold, is_structure in limits:
        name = conn.String(limit_ref)
        if " O0" in name:
            order_limits.append(limit_ref)
        else:
            structure_and_composition.append(limit_ref)
    install_on(conn, portfolios, structure_and_composition, limit_class, "post")
    install_on(conn, portfolios[:50], order_limits, limit_class, "pre")


def install_on(conn, portfolios, limit_refs, limit_class, label):
    posted = 0
    for portfolio in portfolios:
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов КАК Т "
            "ГДЕ Т.Проведен И Т.ОбъектНазначения = &Портфель И НЕ Т.ПометкаУдаления"
        )
        query.УстановитьПараметр("Портфель", portfolio)
        selection = query.Выполнить().Выбрать()
        if selection.Следующий():
            doc = selection.Ссылка.ПолучитьОбъект()
        else:
            doc = getattr(conn.Документы, "УстановкаЛимитов").СоздатьДокумент()
            doc.Дата = datetime.now().replace(microsecond=0)
            doc.ВидОперации = conn.Перечисления.ВидыОперацийУстановкиЛимитов.ПоПортфелю
            doc.ОбъектНазначения = portfolio
            doc.КлассЛимита = limit_class
            doc.Подтвержден = False
        present = {}
        for index in range(doc.Лимиты.Количество()):
            line = doc.Лимиты.Получить(index)
            present[conn.String(line.Лимит)] = line
        changed = False
        for limit_ref in limit_refs:
            key = conn.String(limit_ref)
            if key not in present:
                line = doc.Лимиты.Добавить()
                line.Лимит = limit_ref
                changed = True
        if doc.Лимиты.Количество() > 0 and (changed or not doc.Проведен):
            doc.Записать(conn.РежимЗаписиДокумента.Проведение)
            posted += 1
        if posted and posted % 25 == 0:
            safe_print(label + " docs " + str(posted))
    safe_print(label + " installations " + str(posted))


def retarget_extra_orders(conn, bond):
    """Только 10 поручений остаются по ОФЗ, остальные по акции, чтобы пред-контроль в основном проходил."""
    share = find_by_name(conn, "Активы", "FO_SHAPE SHARE RUB")
    if share is None:
        return
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Ссылка ИЗ Документ.Поручение "
        "ГДЕ Проведен И КомментарийКлиента = &Метка УПОРЯДОЧИТЬ ПО Номер"
    )
    query.УстановитьПараметр("Метка", MARK)
    selection = query.Выполнить().Выбрать()
    index = 0
    while selection.Следующий():
        index += 1
        if index <= 10:
            continue
        doc = selection.Ссылка.ПолучитьОбъект()
        if conn.String(doc.Актив) == "FO_SHAPE SHARE RUB":
            continue
        doc.Актив = share
        doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    safe_print("orders retargeted, bond stays " + conn.String(bond))


def ensure_orders(conn, portfolios, asset):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ Документ.Поручение "
        "ГДЕ Проведен И КомментарийКлиента = &Метка"
    )
    query.УстановитьПараметр("Метка", MARK)
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    existing = int(selection.N)
    if existing >= 50:
        retarget_extra_orders(conn, asset)
        safe_print("orders already " + str(existing))
        return
    currency = currency_ref(conn, "RUB")
    manager = getattr(conn.Документы, "Поручение")
    for index in range(existing, 50):
        doc = manager.СоздатьДокумент()
        doc.ЗаполнитьРеквизитыНовогоПоручения()
        doc.Дата = datetime.now().replace(microsecond=0)
        doc.ВидОперации = conn.Перечисления.ВидыПоручений.Сделка
        doc.Направление = conn.Перечисления.ВидыОперацийСделки.Покупка
        doc.Актив = asset
        doc.Портфель = portfolios[index]
        doc.ВалютаРасчетов = currency
        doc.Количество = 10
        doc.ИсходнаяЦена = 100
        doc.ИсходнаяСумма = 1000
        doc.ДатаПоставки = doc.Дата
        doc.ДатаОплаты = doc.Дата
        doc.ЗаполнениеПоПортфелю = False
        doc.КомментарийКлиента = MARK
        line = doc.РаспределениеПоПортфелям.Добавить()
        line.Портфель = portfolios[index]
        line.Количество = 10
        doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    safe_print("orders 50")


def write_note(lines):
    path = os.path.join(ROOT, "Тестирование", "reports", "shape_data.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    safe_print(path)


def main():
    conn = connect()
    limit_class = conn.NewObject("Запрос")
    limit_class.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.КлассыЛимитов ГДЕ НЕ ПометкаУдаления"
    selection = limit_class.Выполнить().Выбрать()
    selection.Следующий()
    limit_class = selection.Ссылка
    assets = ensure_assets(conn)
    portfolios = ensure_portfolios(conn, assets["rub"])
    write_position(conn, portfolios, assets["specs"])
    write_market_value(conn, portfolios)
    dataset, order_dataset = ensure_dataset(conn, limit_class)
    variant = ensure_variant(conn)
    limits = ensure_limits(conn, dataset, order_dataset, limit_class, variant, assets)
    ensure_thresholds(conn, limits)
    ensure_installations(conn, portfolios, limits, limit_class)
    ensure_orders(conn, portfolios, assets["specs"][0][1])
    write_note([
        "FO_SHAPE данные по форме выгрузки лимитов",
        "Портфелей %s, из них обычная доля %s, повышенная доля валютных облигаций %s" % (
            PORTFOLIO_COUNT, OK_COUNT, PORTFOLIO_COUNT - OK_COUNT),
        "Набор позиции: Плановая, Прогнозная, Прогнозная активы в обратном РЕПО, Фактическая. Активы в РЕПО не включены, как в обычном фронт-офисе после 21.09.2026.",
        "Лимитов структуры 18, состава 6, поручений 2.",
        "Вариант: процент от РСА по общему итогу.",
        "Одинаковый отбор и одинаковый порог: S01 и S03, S04 S05 S06, S13 и S14, S17 и S18, C01 и C02.",
        "Одинаковый отбор и разный порог: S01/S02, S04/S07, S08/S09, S11/S12, S13/S15.",
        "Нарушение остается у 20 хвостовых портфелей: валютные облигации, рублевый остаток и субфедеральная облигация.",
        "Поручения FO_SHAPE: 50, актив OFZ RUB.",
        "Стоимость обычного портфеля 1000: OFZ 700, облигация USD 50, акция RUB 100, акция USD 20, пай 80, RUB 40, USD 10.",
        "РСА, СЧА и СА портфеля в регистре рыночной стоимости: 1000.",
    ])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        safe_print(traceback.format_exc()[-2000:])
        raise
