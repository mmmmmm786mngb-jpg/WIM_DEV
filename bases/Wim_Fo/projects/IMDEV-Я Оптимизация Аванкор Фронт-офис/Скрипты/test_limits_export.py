#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовые данные FO_EXPORT и проверка внешней обработки выгрузки лимитов.
"""

import json
import os
import sys
import traceback
from datetime import datetime

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EPF = os.path.join(ROOT, "Обработки", "FO_LimitsExport.epf")
OUT = os.path.join(ROOT, "Тестирование", "reports", "limits-export-test")
NAME_GROUP = "FO_EXPORT группа"
NAME_LIMIT = "FO_EXPORT лимит"
NAME_DATASET = "FO_GEN набор позиции"
NAME_SOURCE = "FO_GEN источник позиции"


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
    ref = getattr(conn.Справочники, catalog).НайтиПоНаименованию(name, True)
    if ref.Пустая():
        return None
    return ref


def type_of(conn, name):
    return conn.NewObject("ОписаниеТипов", name).Типы().Get(0)


def add_item(conn, collection, type_name):
    return collection.Добавить(type_of(conn, type_name))


def composition_settings(conn, portfolio):
    settings = conn.NewObject("НастройкиКомпоновкиДанных")
    elements = settings.Отбор.Элементы
    direct = add_item(conn, elements, "ЭлементОтбораКомпоновкиДанных")
    direct.Использование = True
    direct.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", "Актив.Эмитент")
    direct.ВидСравнения = conn.ВидСравненияКомпоновкиДанных.Равно
    direct.ПравоеЗначение = "FO_EXPORT_EMITENT"

    group = add_item(conn, elements, "ГруппаЭлементовОтбораКомпоновкиДанных")
    group.Использование = True
    group.ТипГруппы = conn.ТипГруппыЭлементовОтбораКомпоновкиДанных.ГруппаИли

    amount = add_item(conn, group.Элементы, "ЭлементОтбораКомпоновкиДанных")
    amount.Использование = True
    amount.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", "Количество")
    amount.ВидСравнения = conn.ВидСравненияКомпоновкиДанных.Больше
    amount.ПравоеЗначение = 5

    values = conn.NewObject("СписокЗначений")
    values.Добавить(portfolio)
    listed = add_item(conn, group.Элементы, "ЭлементОтбораКомпоновкиДанных")
    listed.Использование = True
    listed.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", "Портфель")
    listed.ВидСравнения = conn.ВидСравненияКомпоновкиДанных.ВСписке
    listed.ПравоеЗначение = values
    return settings


def internal_string(conn, settings):
    storage = conn.NewObject("ХранилищеЗначения", settings)
    return conn.ЗначениеВСтрокуВнутр(storage)


def ensure_dataset(conn, limit_class):
    dataset = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", NAME_DATASET)
    if dataset is not None:
        safe_print("dataset exists")
        return dataset
    source = find_by_name(conn, "ИсточникиДанныхДляПроверкиЛимитов", NAME_SOURCE)
    if source is None:
        source_item = getattr(conn.Справочники, "ИсточникиДанныхДляПроверкиЛимитов").СоздатьЭлемент()
        source_item.Наименование = NAME_SOURCE
        source_item.ВидИсточника = conn.Перечисления.ВидыОсновныхИсточниковДанных.ТекущаяПозиция
        source_item.КлассЛимита = limit_class
        source_item.Записать()
        source = source_item.Ссылка
        safe_print("source created")
    item = getattr(conn.Справочники, "НаборыДанныхДляПроверкиЛимитов").СоздатьЭлемент()
    item.Наименование = NAME_DATASET
    item.ИсточникДанных = source
    item.КлассЛимита = limit_class
    item.Записать()
    safe_print("dataset created")
    return item.Ссылка


def ensure_limit(conn, limit_class, dataset, portfolio):
    manager = getattr(conn.Справочники, "Лимиты")
    group = find_by_name(conn, "Лимиты", NAME_GROUP)
    if group is None:
        group_item = manager.СоздатьГруппу()
        group_item.Наименование = NAME_GROUP
        group_item.Записать()
        group = group_item.Ссылка
        safe_print("group created")
    else:
        safe_print("group exists")

    settings = composition_settings(conn, portfolio)
    packed = internal_string(conn, settings)
    algorithm = conn.NewObject("Структура")
    algorithm.Вставить("ПорогАлгоритма", 15)
    algorithm.Вставить("Комментарий", "FO_EXPORT")
    algorithm_storage = conn.NewObject("ХранилищеЗначения", algorithm)

    template_storage = None
    try:
        template = conn.NewObject("МакетКомпоновкиДанных")
        template_storage = conn.NewObject("ХранилищеЗначения", template)
    except Exception as error:
        safe_print("template skipped: " + str(error)[:180])

    existing = find_by_name(conn, "Лимиты", NAME_LIMIT)
    if existing is None:
        item = manager.СоздатьЭлемент()
        safe_print("limit creating")
    else:
        item = existing.ПолучитьОбъект()
        item.Квалификаторы.Очистить()
        item.ПараметрыЗапросов.Очистить()
        safe_print("limit updating")

    item.Родитель = group
    item.Наименование = NAME_LIMIT
    item.СпособНастройкиЛимита = conn.Перечисления.СпособыНастройкиЛимита.Внутренний
    item.ВидЛимита = conn.Перечисления.ВидыЛимитов.Состав
    item.НаборДанныхДляПроверкиЛимитов = dataset
    item.КлассЛимита = limit_class
    item.Тестовый = True
    item.Подтвержден = True
    item.ДополнительныйОтбор = "И Актив.Тестовый = ЛОЖЬ"
    item.УсловияОтбораОсновные = "ВЫБРАТЬ 1 КАК Поле ГДЕ Эмитент = &Эмитент"
    item.НастройкиПодготовкиСпискаАктивов = packed
    item.НастройкиАлгоритма = algorithm_storage
    if template_storage is not None:
        item.МакетКомпоновкиНастроек = template_storage

    qualifier = item.Квалификаторы.Добавить()
    qualifier.Описание = "FO_EXPORT квалификатор"
    qualifier.Квалификатор = packed
    qualifier.УсловияОтбора = "ВЫБРАТЬ 1 КАК Поле ГДЕ Портфель В (&Портфели)"
    qualifier.НастройкиКвалификатораНеактуальны = False

    parameter = item.ПараметрыЗапросов.Добавить()
    parameter.ИмяПараметра = "Эмитент"
    parameter.ЗначениеПараметра = "FO_EXPORT_EMITENT"
    item.Записать()
    safe_print("limit written")
    return item.Ссылка


def ensure_installation(conn, portfolio, limit_ref, limit_class):
    rows = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов.Лимиты КАК Т "
        "ГДЕ Т.Ссылка.ОбъектНазначения = &Портфель И Т.Ссылка.Проведен И НЕ Т.Ссылка.ПометкаУдаления "
        "УПОРЯДОЧИТЬ ПО Т.Ссылка.Дата УБЫВ",
        {"Портфель": portfolio},
    )
    if rows:
        doc = rows[0].Ссылка.ПолучитьОбъект()
        safe_print("installation updating")
    else:
        doc = getattr(conn.Документы, "УстановкаЛимитов").СоздатьДокумент()
        doc.Дата = datetime.now().replace(microsecond=0)
        doc.ВидОперации = conn.Перечисления.ВидыОперацийУстановкиЛимитов.ПоПортфелю
        doc.ОбъектНазначения = portfolio
        doc.КлассЛимита = limit_class
        doc.Подтвержден = True
        safe_print("installation creating")

    blank_line = doc.Лимиты.Добавить()
    blank_storage = blank_line.НастройкиЛимита
    doc.Лимиты.Удалить(doc.Лимиты.Количество() - 1)

    settings = conn.NewObject("Структура")
    settings.Вставить("Порог", 10)
    settings.Вставить("Комментарий", "FO_EXPORT")
    found = None
    for index in range(doc.Лимиты.Количество()):
        line = doc.Лимиты.Получить(index)
        line_name = str(conn.String(line.Лимит))
        if line_name == NAME_LIMIT:
            found = line
            continue
        stored = line.НастройкиЛимита.Получить()
        comment = ""
        try:
            comment = str(stored.Комментарий)
        except Exception:
            comment = ""
        if comment == "FO_EXPORT":
            line.НастройкиЛимита = blank_storage
    if found is None:
        found = doc.Лимиты.Добавить()
        found.Лимит = limit_ref
    found.НастройкиЛимита = conn.NewObject("ХранилищеЗначения", settings)
    found.НастройкиУстановлены = True
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    safe_print("installation posted")
    return doc.Ссылка


def run_export(conn):
    processor = conn.ВнешниеОбработки.Создать(EPF, False)
    text = processor.ВыгрузитьЛимитыАрхивом(OUT)
    safe_print(text)
    return text


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def check_export():
    index = load_json(os.path.join(OUT, "index.json"))
    names = [row.get("Наименование") for row in index["Лимиты"]]
    if NAME_GROUP not in names or NAME_LIMIT not in names:
        raise RuntimeError("index missing FO_EXPORT rows")
    limit_row = [row for row in index["Лимиты"] if row.get("Наименование") == NAME_LIMIT][0]
    if not limit_row.get("Файл"):
        raise RuntimeError("limit file name is empty")
    limit = load_json(os.path.join(OUT, limit_row["Файл"].replace("/", os.sep)))
    settings = limit["Реквизиты"]["НастройкиПодготовкиСпискаАктивов"]
    if settings.get("Вид") != "СтрокаВнутр":
        raise RuntimeError("asset settings were not decoded")
    filters = settings["Значение"]["Отбор"]
    left_values = []

    def walk(items):
        for item in items:
            if item.get("Вид") == "Группа":
                if "Или" not in str(item.get("ТипГруппы")) and "Or" not in str(item.get("ТипГруппы")):
                    raise RuntimeError("OR group was not exported: " + str(item.get("ТипГруппы")))
                walk(item.get("Элементы", []))
            else:
                left_values.append(str(item.get("ЛевоеЗначение")))
                right = item.get("ПравоеЗначение")
                if isinstance(right, list) and right:
                    left_values.append("LIST")

    walk(filters)
    joined = " ".join(left_values)
    if "Актив.Эмитент" not in joined or "Количество" not in joined or "LIST" not in joined:
        raise RuntimeError("filter tree is incomplete: " + joined)
    qualifiers = limit["ТабличныеЧасти"]["Квалификаторы"]
    condition = qualifiers[0]["УсловияОтбора"]
    if "Портфель" not in condition or "ИЛИ" not in condition and "OR" not in condition:
        raise RuntimeError("qualifier query text is missing: " + condition)
    if qualifiers[0]["Квалификатор"].get("Вид") != "СтрокаВнутр":
        raise RuntimeError("qualifier settings were not decoded")
    if limit["Реквизиты"]["УсловияОтбораОсновные"].find("Эмитент") < 0:
        raise RuntimeError("main query text is missing")
    algorithm = limit["Реквизиты"]["НастройкиАлгоритма"]
    if algorithm.get("Вид") != "ХранилищеЗначения" or algorithm["Значение"].get("ПорогАлгоритма") != 15:
        raise RuntimeError("algorithm settings were not unpacked")
    template = limit["Реквизиты"]["МакетКомпоновкиНастроек"]
    if template.get("Значение", {}).get("Вид") != "МакетКомпоновкиДанных":
        raise RuntimeError("template marker is missing")
    if "НаборДанныхДляПроверкиЛимитов" not in limit["Связанные"]:
        raise RuntimeError("dataset card is missing")

    installations = load_json(os.path.join(OUT, "installations.json"))
    found_threshold = False
    for document in installations["Документы"]:
        for line in document["Лимиты"]:
            limit_ref = line.get("Лимит") or {}
            if limit_ref.get("Представление") != NAME_LIMIT:
                continue
            value = (line.get("Настройки") or {}).get("Значение") or {}
            if value.get("Порог") == 10 and value.get("Комментарий") == "FO_EXPORT":
                found_threshold = True
    if not found_threshold:
        raise RuntimeError("installation threshold was not unpacked")
    if index["Ошибки"]:
        raise RuntimeError("export errors: " + str(index["Ошибки"]))
    safe_print(
        "check ok elements="
        + str(index["КоличествоЭлементов"])
        + " groups="
        + str(index["КоличествоГрупп"])
        + " documents="
        + str(index["КоличествоДокументовУстановок"])
    )


def main():
    if not os.path.isfile(EPF):
        safe_print("ERROR epf missing")
        return 1
    os.makedirs(OUT, exist_ok=True)
    conn = connect()
    classes = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Классы.Ссылка КАК Ссылка "
        "ИЗ Справочник.КлассыЛимитов КАК Классы ГДЕ НЕ Классы.ПометкаУдаления",
    )
    portfolios = query_rows(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Портфели.Ссылка КАК Ссылка "
        "ИЗ Справочник.Портфели КАК Портфели ГДЕ НЕ Портфели.ПометкаУдаления",
    )
    if not classes or not portfolios:
        safe_print("ERROR no class or portfolio")
        return 1
    dataset = ensure_dataset(conn, classes[0].Ссылка)
    limit_ref = ensure_limit(conn, classes[0].Ссылка, dataset, portfolios[0].Ссылка)
    ensure_installation(conn, portfolios[0].Ссылка, limit_ref, classes[0].Ссылка)
    run_export(conn)
    check_export()
    pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        safe_print(traceback.format_exc()[-1500:])
        raise
