#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация минимальных данных FO_GEN и прогон постконтроля лимитов.
"""

import datetime
import os
import sys
import time
import traceback

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
NAME_SOURCE = "FO_GEN источник"
NAME_DATASET = "FO_GEN набор"
NAME_LIMIT = "FO_GEN лимит"
NAME_SOURCE_POS = "FO_GEN источник позиции"
NAME_DATASET_POS = "FO_GEN набор позиции"
NAME_LIMIT_POS = "FO_GEN лимит состав"
NAME_UKR = "FO_GEN УКР"


def safe_print(text):
    """Печать в консоль без падения на кодировке."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def connect():
    pythoncom.CoInitialize()
    com = win32com.client.Dispatch("V83.COMConnector")
    return com.Connect(CONN)


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
    manager = getattr(conn.Справочники, catalog)
    ref = manager.НайтиПоНаименованию(name, True)
    if ref.Пустая():
        return None
    return ref


def ensure_source(conn):
    manager = getattr(conn.Справочники, "ИсточникиДанныхДляПроверкиЛимитов")
    predefined = None
    try:
        predefined = manager.Основной
    except Exception:
        predefined = None
    if predefined is not None and not predefined.Пустая():
        kind = conn.String(predefined.ВидИсточника)
        safe_print("source predefined kind=" + kind)
        if "Поручение" in kind:
            return predefined
    existing = find_by_name(conn, "ИсточникиДанныхДляПроверкиЛимитов", NAME_SOURCE)
    if existing is not None:
        safe_print("source exists")
        return existing
    item = manager.СоздатьЭлемент()
    item.Наименование = NAME_SOURCE
    item.ВидИсточника = conn.Перечисления.ВидыОсновныхИсточниковДанных.Поручение
    item.Записать()
    safe_print("source created")
    return item.Ссылка


def ensure_dataset(conn, source, limit_class):
    existing = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", NAME_DATASET)
    if existing is not None:
        safe_print("dataset exists")
        return existing
    manager = getattr(conn.Справочники, "НаборыДанныхДляПроверкиЛимитов")
    item = manager.СоздатьЭлемент()
    item.Наименование = NAME_DATASET
    item.ИсточникДанных = source
    item.КлассЛимита = limit_class
    item.Записать()
    safe_print("dataset created")
    return item.Ссылка


def ensure_limit(conn, dataset, limit_class):
    existing = find_by_name(conn, "Лимиты", NAME_LIMIT)
    if existing is not None:
        safe_print("limit exists")
        return existing
    manager = getattr(conn.Справочники, "Лимиты")
    item = manager.СоздатьЭлемент()
    item.Наименование = NAME_LIMIT
    item.СпособНастройкиЛимита = conn.Перечисления.СпособыНастройкиЛимита.Внутренний
    item.ВидЛимита = conn.Перечисления.ВидыЛимитов.Поручение
    item.НаборДанныхДляПроверкиЛимитов = dataset
    item.КлассЛимита = limit_class
    item.Тестовый = False
    item.Подтвержден = True
    item.Записать()
    safe_print("limit created")
    return item.Ссылка


def save_settings(conn, limit_ref):
    getattr(conn.Справочники, "Лимиты").СохранитьНастройкиЛимита(limit_ref)
    safe_print("settings cache saved")


def ensure_installation(conn, portfolio, limit_ref, limit_class):
    rows = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов.Лимиты КАК Т "
        "ГДЕ Т.Лимит = &Лимит И Т.Ссылка.Проведен",
        {"Лимит": limit_ref},
    )
    if rows:
        safe_print("installation already posted")
        return rows[0].Ссылка
    manager = getattr(conn.Документы, "УстановкаЛимитов")
    doc = manager.СоздатьДокумент()
    doc.Дата = datetime.datetime.now().replace(microsecond=0)
    doc.ВидОперации = conn.Перечисления.ВидыОперацийУстановкиЛимитов.ПоПортфелю
    doc.ОбъектНазначения = portfolio
    doc.КлассЛимита = limit_class
    doc.Подтвержден = True
    line = doc.Лимиты.Добавить()
    line.Лимит = limit_ref
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    safe_print("installation posted")
    return doc.Ссылка


def ensure_position_chain(conn, limit_class):
    source = find_by_name(conn, "ИсточникиДанныхДляПроверкиЛимитов", NAME_SOURCE_POS)
    if source is None:
        item = getattr(conn.Справочники, "ИсточникиДанныхДляПроверкиЛимитов").СоздатьЭлемент()
        item.Наименование = NAME_SOURCE_POS
        item.ВидИсточника = conn.Перечисления.ВидыОсновныхИсточниковДанных.ТекущаяПозиция
        item.КлассЛимита = limit_class
        item.Записать()
        source = item.Ссылка
        safe_print("position source created")
    else:
        safe_print("position source exists")
    dataset = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", NAME_DATASET_POS)
    if dataset is None:
        item = getattr(conn.Справочники, "НаборыДанныхДляПроверкиЛимитов").СоздатьЭлемент()
        item.Наименование = NAME_DATASET_POS
        item.ИсточникДанных = source
        item.КлассЛимита = limit_class
        item.Записать()
        dataset = item.Ссылка
        safe_print("position dataset created")
    else:
        safe_print("position dataset exists")
    limit_ref = find_by_name(conn, "Лимиты", NAME_LIMIT_POS)
    if limit_ref is None:
        item = getattr(conn.Справочники, "Лимиты").СоздатьЭлемент()
        item.Наименование = NAME_LIMIT_POS
        item.СпособНастройкиЛимита = conn.Перечисления.СпособыНастройкиЛимита.Внутренний
        item.ВидЛимита = conn.Перечисления.ВидыЛимитов.Состав
        item.НаборДанныхДляПроверкиЛимитов = dataset
        item.КлассЛимита = limit_class
        item.Тестовый = False
        item.Подтвержден = True
        item.Записать()
        limit_ref = item.Ссылка
        safe_print("composition limit created")
    else:
        safe_print("composition limit exists")
    save_settings(conn, limit_ref)
    return limit_ref


def ensure_extra_settings(conn):
    setting = find_by_name(conn, "НастройкиУстановкиКредитныхРейтингов", NAME_UKR)
    if setting is None:
        item = getattr(conn.Справочники, "НастройкиУстановкиКредитныхРейтингов").СоздатьЭлемент()
        item.Наименование = NAME_UKR
        item.Префикс = "FOGEN"
        item.Записать()
        setting = item.Ссылка
        safe_print("ukr setting created")
    else:
        safe_print("ukr setting exists")
    rows = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаДополнительныхНастроекЛимитов КАК Т "
        "ГДЕ Т.Проведен И Т.НастройкаУстановкиКредитныхРейтингов = &Настройка",
        {"Настройка": setting},
    )
    if rows:
        safe_print("extra settings document exists")
        return
    doc = getattr(conn.Документы, "УстановкаДополнительныхНастроекЛимитов").СоздатьДокумент()
    doc.Дата = datetime.datetime.now().replace(microsecond=0)
    doc.НастройкаУстановкиКредитныхРейтингов = setting
    doc.ПроверятьНаличиеПорогов = False
    doc.ВыполнятьРассылкуРезультатовPreTradeВместеСПроверкой = False
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    safe_print("extra settings document posted")


def add_limit_to_installation(conn, limit_ref):
    rows = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов.Лимиты КАК Т "
        "ГДЕ Т.Лимит.Наименование = &Имя И Т.Ссылка.Проведен",
        {"Имя": NAME_LIMIT},
    )
    if not rows:
        safe_print("ERROR installation for order limit not found")
        return
    already = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов.Лимиты КАК Т "
        "ГДЕ Т.Лимит = &Лимит И Т.Ссылка.Проведен",
        {"Лимит": limit_ref},
    )
    if already:
        safe_print("composition limit already in installation")
        return
    doc = rows[0].Ссылка.ПолучитьОбъект()
    line = doc.Лимиты.Добавить()
    line.Лимит = limit_ref
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    safe_print("installation updated")


def new_array(conn, values):
    array = conn.NewObject("Массив")
    for value in values:
        array.Add(value)
    return array


def run_direct(conn, portfolio, limit_ref):
    empty = new_array(conn, [])
    portfolios = new_array(conn, [portfolio])
    limits = new_array(conn, [limit_ref])
    today = datetime.datetime.now().replace(microsecond=0)
    empty_date = query_rows(conn, "ВЫБРАТЬ ДАТАВРЕМЯ(1, 1, 1) КАК D")[0].D
    plan = getattr(conn, "РаботаСЛимитами").ПланПроверки(today, empty, portfolios, limits)
    safe_print("plan rows=" + str(plan.Количество()))
    params = conn.NewObject("Структура")
    params.Вставить("Вид", conn.Перечисления.ВидыРаспорядителей.ПроверкаИОтправка)
    params.Вставить("Метод", "Распорядители.ПроверкаИОтправка")
    params.Вставить("МетодНаКлиенте", "РаспорядителиКлиент.ПроверкаИОтправка_Вход")
    params.Вставить("Наименование", "FO_GEN postcontrol")
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
    params.Вставить("ОписаниеОперации", "FO_GEN")
    params.Вставить("ФормуИнициаторЗакрыть", False)
    params.Вставить("Поручения", empty)
    params.Вставить("Портфели", portfolios)
    params.Вставить("Лимиты", limits)
    safe_print("param portfolios=" + str(params.Портфели.Количество()))
    safe_print("param limits=" + str(params.Лимиты.Количество()))
    params.Вставить("ОтправитьПослеПроверки", False)
    params.Вставить("ДатаПроверки", today)
    params.Вставить("ДатаФактПозиции", empty_date)
    params.Вставить("ДатаОграниченияПлановойПозиции", empty_date)
    params.Вставить("СоставПозиции", new_array(conn, []))
    params.Вставить("ЭтоПретрейд", False)
    params.Вставить("ПроверкаПоручений", False)
    params.Вставить("ИспользоватьДатуАктуальности", True)
    params.Вставить("СоставПозицииИзДополнительныхНастроек", new_array(conn, []))
    params.Вставить("ВыводитьПредупрежденияПриПретрейде", False)
    params.Вставить("ВозможенЗапускПроверки", True)
    params.Вставить("ВозможенЗапускПроверкиОписание", "")
    params.Вставить("Вместилище", conn.NewObject("УникальныйИдентификатор"))
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
    safe_print("check seconds=" + format(elapsed, ".3f"))
    safe_print("refusal=" + str(result.Отказ))
    log_path = os.path.join(os.path.dirname(__file__), "..", "Тестирование", "reports", "fo_gen_check.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    text = str(result.Описание)
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    safe_print("description bytes=" + str(len(text)))
    return elapsed


def run_postcontrol(conn, portfolio, limit_ref):
    processing = getattr(conn.Обработки, "ТестированиеЛимитов").Создать()
    processing.ДатаПроверки = datetime.datetime.now().replace(microsecond=0)
    processing.Посттрейд = True
    processing.Претрейд = False
    processing.ИспользоватьДатуАктуальности = False
    limit_row = processing.СписокЛимитов.Добавить()
    limit_row.Лимит = limit_ref
    portfolio_row = processing.СписокПортфелейГруппПортфелей.Добавить()
    portfolio_row.ПортфельГруппаПортфелей = portfolio
    started = time.perf_counter()
    processing.ВыполнитьПроверкуЛимитов()
    elapsed = time.perf_counter() - started
    safe_print("check seconds=" + format(elapsed, ".3f"))
    return elapsed


def print_measures(conn):
    rows = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 30 "
        "Замеры.КлючеваяОперация.Наименование КАК Имя, "
        "Замеры.ВремяВыполнения КАК Секунды, "
        "Замеры.ВесЗамера КАК Вес, "
        "Замеры.НомерСеанса КАК Сеанс "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера УБЫВ",
    )
    safe_print("measures " + str(len(rows)))
    for row in rows:
        safe_print(
            " | ".join(
                [
                    str(row.Сеанс),
                    str(row.Имя),
                    format(float(row.Секунды), ".3f"),
                    str(row.Вес),
                ]
            )
        )


def main():
    conn = connect()
    portfolios = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Портфели.Ссылка КАК Ссылка, Портфели.Наименование КАК Имя "
        "ИЗ Справочник.Портфели КАК Портфели ГДЕ НЕ Портфели.ПометкаУдаления",
    )
    classes = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Классы.Ссылка КАК Ссылка, Классы.Наименование КАК Имя "
        "ИЗ Справочник.КлассыЛимитов КАК Классы ГДЕ НЕ Классы.ПометкаУдаления "
        "УПОРЯДОЧИТЬ ПО Классы.РасширенноеПодтверждение",
    )
    if not portfolios or not classes:
        safe_print("ERROR no portfolio or limit class")
        return 1
    safe_print("portfolio ok")
    safe_print("class ok")
    source = ensure_source(conn)
    dataset = ensure_dataset(conn, source, classes[0].Ссылка)
    limit_ref = ensure_limit(conn, dataset, classes[0].Ссылка)
    save_settings(conn, limit_ref)
    ensure_installation(conn, portfolios[0].Ссылка, limit_ref, classes[0].Ссылка)
    composition = ensure_position_chain(conn, classes[0].Ссылка)
    add_limit_to_installation(conn, composition)
    ensure_extra_settings(conn)
    dataset_pos = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", NAME_DATASET_POS)
    dataset_pos.ПолучитьОбъект().Записать()
    safe_print("position dataset rewritten")
    save_settings(conn, composition)
    run_direct(conn, portfolios[0].Ссылка, composition)
    print_measures(conn)
    pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        safe_print(traceback.format_exc().splitlines()[-1][:500])
        raise
