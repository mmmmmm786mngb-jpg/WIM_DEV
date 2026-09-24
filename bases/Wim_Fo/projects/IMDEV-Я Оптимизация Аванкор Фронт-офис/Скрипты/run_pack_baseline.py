#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовая пачка FO_PACK и эталон текущего алгоритма до расширения.
Пост-контроль по трем портфелям и трем структурным лимитам одного набора.
"""

import os
import time
import traceback
from datetime import datetime

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT = os.path.join(ROOT, "Тестирование", "reports", "pack_baseline.txt")
DATASET_NAME = "FO_GEN набор позиции"
NAMES = ("FO_PACK структура 1", "FO_PACK структура 2", "FO_PACK структура 3")
PORTFOLIOS = ("FO_PACK портфель 2", "FO_PACK портфель 3")


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
        rows.append(selection)
    return rows


def find_by_name(conn, catalog, name):
    ref = getattr(conn.Справочники, catalog).НайтиПоНаименованию(name, True)
    if ref.Пустая():
        return None
    return ref


def type_of(conn, name):
    return conn.NewObject("ОписаниеТипов", name).Типы().Get(0)


def simple_filter(conn, right_value):
    settings = conn.NewObject("НастройкиКомпоновкиДанных")
    item = settings.Отбор.Элементы.Добавить(type_of(conn, "ЭлементОтбораКомпоновкиДанных"))
    item.Использование = True
    item.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", "ВидАктива")
    item.ВидСравнения = conn.ВидСравненияКомпоновкиДанных.Равно
    item.ПравоеЗначение = right_value
    storage = conn.NewObject("ХранилищеЗначения", settings)
    return conn.ЗначениеВСтрокуВнутр(storage)


def ensure_portfolios(conn):
    refs = []
    base = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка КАК Ссылка ИЗ Справочник.Портфели ГДЕ НЕ ПометкаУдаления",
    )[0].Ссылка
    refs.append(base)
    for name in PORTFOLIOS:
        found = find_by_name(conn, "Портфели", name)
        if found is None:
            item = getattr(conn.Справочники, "Портфели").СоздатьЭлемент()
            item.Наименование = name
            item.Записать()
            found = item.Ссылка
            safe_print("portfolio created " + name)
        else:
            safe_print("portfolio exists " + name)
        refs.append(found)
    return refs


def ensure_limits(conn):
    dataset = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", DATASET_NAME)
    if dataset is None:
        raise RuntimeError("dataset missing")
    limit_class = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка КАК Ссылка ИЗ Справочник.КлассыЛимитов ГДЕ НЕ ПометкаУдаления",
    )[0].Ссылка
    variant = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка КАК Ссылка ИЗ Справочник.ВариантыПроверкиПороговЛимитов "
        "ГДЕ НЕ ПометкаУдаления",
    )
    variant_ref = variant[0].Ссылка if variant else None
    refs = []
    for index, name in enumerate(NAMES, start=1):
        found = find_by_name(conn, "Лимиты", name)
        if found is None:
            item = getattr(conn.Справочники, "Лимиты").СоздатьЭлемент()
        else:
            item = found.ПолучитьОбъект()
        item.Наименование = name
        item.СпособНастройкиЛимита = conn.Перечисления.СпособыНастройкиЛимита.Внутренний
        item.ВидЛимита = conn.Перечисления.ВидыЛимитов.Структура
        item.НаборДанныхДляПроверкиЛимитов = dataset
        item.КлассЛимита = limit_class
        if variant_ref is not None:
            item.ВариантПроверкиПорога = variant_ref
        item.Тестовый = False
        item.Подтвержден = True
        item.НастройкиПодготовкиСпискаАктивов = simple_filter(conn, "FO_PACK_" + str(index))
        item.УсловияОтбораОсновные = "(#Т.ВидАктива = &П0_О)"
        item.Записать()
        refs.append(item.Ссылка)
        safe_print("limit ready " + name)
    return refs, limit_class


def ensure_installation(conn, portfolio, limits, limit_class):
    rows = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов КАК Т "
        "ГДЕ Т.Проведен И Т.ОбъектНазначения = &Портфель И НЕ Т.ПометкаУдаления",
        {"Портфель": portfolio},
    )
    if rows:
        doc = rows[0].Ссылка.ПолучитьОбъект()
    else:
        doc = getattr(conn.Документы, "УстановкаЛимитов").СоздатьДокумент()
        doc.Дата = datetime.now().replace(microsecond=0)
        doc.ВидОперации = conn.Перечисления.ВидыОперацийУстановкиЛимитов.ПоПортфелю
        doc.ОбъектНазначения = portfolio
        doc.КлассЛимита = limit_class
        doc.Подтвержден = True
    settings = conn.NewObject("Структура")
    settings.Вставить("Порог", 10)
    settings.Вставить("Комментарий", "FO_PACK")
    storage = conn.NewObject("ХранилищеЗначения", settings)
    for limit_ref in limits:
        found = None
        for index in range(doc.Лимиты.Количество()):
            line = doc.Лимиты.Получить(index)
            if conn.String(line.Лимит) == conn.String(limit_ref):
                found = line
                break
        if found is None:
            found = doc.Лимиты.Добавить()
            found.Лимит = limit_ref
        found.НастройкиЛимита = storage
        found.НастройкиУстановлены = True
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    safe_print("installation posted")


def new_array(conn, values):
    array = conn.NewObject("Массив")
    for value in values:
        array.Add(value)
    return array


def run_post(conn, portfolios, limits, orders=None, pretrade=False):
    empty = new_array(conn, [])
    today = datetime.now().replace(microsecond=0)
    empty_date = query_rows(conn, "ВЫБРАТЬ ДАТАВРЕМЯ(1, 1, 1) КАК D")[0].D
    container = conn.NewObject("УникальныйИдентификатор")
    params = conn.NewObject("Структура")
    params.Вставить("Вид", conn.Перечисления.ВидыРаспорядителей.ПроверкаИОтправка)
    params.Вставить("Метод", "Распорядители.ПроверкаИОтправка")
    params.Вставить("МетодНаКлиенте", "РаспорядителиКлиент.ПроверкаИОтправка_Вход")
    params.Вставить("Наименование", "FO_PACK post")
    params.Вставить("ЭраРаспорядителей", True)
    params.Вставить("АдресРезультатаРасш", conn.ПоместитьВоВременноеХранилище(None))
    params.Вставить("ИспользоватьФоновыеЗадания", False)
    params.Вставить("ФормироватьЛогОтладки", False)
    params.Вставить("ВестиУчетПоСубпортфелям", False)
    params.Вставить("РежимТестирования", True)
    params.Вставить("РежимТестированияЛимитов", True)
    params.Вставить("Профиль", getattr(conn.Справочники, "НастройкиПрофилейБлоттера").ПустаяСсылка())
    params.Вставить("ИдентификаторФормы", None)
    params.Вставить("КлючеваяОперация", getattr(conn.Справочники, "КлючевыеОперации").Проверка)
    params.Вставить("ПоказатьРезультатОбработки", False)
    params.Вставить("ОписаниеОперации", "FO_PACK")
    params.Вставить("ФормуИнициаторЗакрыть", False)
    params.Вставить("Поручения", new_array(conn, orders or []))
    params.Вставить("Портфели", new_array(conn, portfolios))
    params.Вставить("Лимиты", new_array(conn, limits))
    params.Вставить("ОтправитьПослеПроверки", False)
    params.Вставить("ДатаПроверки", today)
    params.Вставить("ДатаФактПозиции", empty_date)
    params.Вставить("ДатаОграниченияПлановойПозиции", empty_date)
    params.Вставить("СоставПозиции", empty)
    params.Вставить("ЭтоПретрейд", pretrade)
    params.Вставить("ПроверкаПоручений", pretrade)
    params.Вставить("ИспользоватьДатуАктуальности", True)
    params.Вставить("СоставПозицииИзДополнительныхНастроек", empty)
    params.Вставить("ВыводитьПредупрежденияПриПретрейде", False)
    params.Вставить("ВозможенЗапускПроверки", True)
    params.Вставить("ВозможенЗапускПроверкиОписание", "")
    params.Вставить("Вместилище", container)
    params.Вставить("РазослатьВедомости", False)
    params.Вставить("РазослатьВедомостиПоручений", False)
    params.Вставить("ОбновлятьРасширения", False)
    params.Вставить("ПланПроверки", conn.NewObject("ХранилищеЗначения", getattr(conn, "РаботаСЛимитами").ПланПроверкиМакет()))
    params.Вставить("КонтролироватьОтклонениеЦены", False)
    params.Вставить("БезВопросаПодтверждения", True)
    params.Вставить("ОткрыватьСправкуРасчетПриНарушениях", False)
    started = time.perf_counter()
    result = getattr(conn, "Распорядители").ПроверкаИОтправка(params)
    elapsed = time.perf_counter() - started
    return elapsed, result, container


def main():
    lines = []
    conn = connect()
    portfolios = ensure_portfolios(conn)
    limits, limit_class = ensure_limits(conn)
    for portfolio in portfolios:
        ensure_installation(conn, portfolio, limits, limit_class)
    orders = query_rows(conn, "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ Документ.Поручение ГДЕ Проведен")
    lines.append("orders posted " + str(orders[0].N))
    elapsed, result, container = run_post(conn, portfolios, limits)
    lines.append("post seconds " + format(elapsed, ".3f"))
    lines.append("post refusal " + str(result.Отказ))
    lines.append("post description")
    lines.append(str(result.Описание))
    measure_query = conn.NewObject("Запрос")
    measure_query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 15 Замеры.КлючеваяОперация.Наименование КАК Имя, "
        "Замеры.ВремяВыполнения КАК Секунды, Замеры.ВесЗамера КАК Вес "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера УБЫВ"
    )
    lines.append("cache")
    cache_query = conn.NewObject("Запрос")
    cache_query.Текст = (
        "ВЫБРАТЬ К.Лимит.Наименование КАК Лимит, К.Фокус.Наименование КАК Фокус, "
        "К.Зона КАК Зона, К.Отказ КАК Отказ, К.Базис КАК Базис "
        "ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Лимит.Наименование ПОДОБНО \"FO_PACK%\" "
        "УПОРЯДОЧИТЬ ПО Лимит, Фокус"
    )
    cache = cache_query.Выполнить().Выбрать()
    cache_count = 0
    while cache.Следующий():
        cache_count += 1
        lines.append("%s | %s | %s | %s | %s" % (
            conn.String(cache.Лимит), conn.String(cache.Фокус),
            conn.String(cache.Зона), cache.Отказ, cache.Базис))
    lines.append("cache rows " + str(cache_count))
    lines.append("measures")
    selection = measure_query.Выполнить().Выбрать()
    while selection.Следующий():
        lines.append("%s | %s | %s" % (conn.String(selection.Имя), selection.Секунды, selection.Вес))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    safe_print("\n".join(lines[:12]))
    safe_print(REPORT)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        safe_print(traceback.format_exc()[-1500:])
        raise
