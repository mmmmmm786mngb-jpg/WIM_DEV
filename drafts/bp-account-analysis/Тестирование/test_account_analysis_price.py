#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка строки цены в отчете Анализ счета.
Результат пишется в файл, в консоль только ASCII.
"""

import pythoncom
import win32com.client
import traceback

OUT = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Тестирование\test_result.txt"
MXL = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Тестирование\account_analysis_41_01.mxl"


def log(lines, text):
    lines.append(text)


def query_date(conn, year, month, day):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d) КАК Д" % (year, month, day)
    data = query.Выполнить().Выгрузить()
    return data.Get(0).Д


def set_prop(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        obj.Вставить(name, value)
        return True


def form_report(conn, account_code, lines, tag):
    reports = getattr(conn, "Отчеты")
    manager = getattr(reports, "АнализСчета")
    params = manager.ПустыеПараметрыКомпоновкиОтчета()

    accounts = getattr(getattr(conn, "ПланыСчетов"), "Хозрасчетный")
    orgs = getattr(getattr(conn, "Справочники"), "Организации")
    account = accounts.НайтиПоКоду(account_code)
    org = orgs.НайтиПоНаименованию("Конфетпром ООО", True)
    log(lines, tag + " account empty=" + str(account.Пустая()) + " org empty=" + str(org.Пустая()))

    set_prop(params, "Организация", org)
    set_prop(params, "НачалоПериода", query_date(conn, 2020, 1, 1))
    set_prop(params, "КонецПериода", query_date(conn, 2026, 10, 4))
    set_prop(params, "Счет", account)
    for name in ("НУ", "СверкаНУ", "ПР", "ВР", "Контроль", "ВалютнаяСумма"):
        set_prop(params, "Показатель" + name, False)
    set_prop(params, "ПоказательБУ", True)
    set_prop(params, "ПоказательКоличество", True)
    set_prop(params, "ВыводитьЗаголовок", True)
    set_prop(params, "ВыводитьПодвал", False)

    grouping = params.Группировка
    row = grouping.Добавить()
    row.Использование = True
    row.Поле = "Субконто1"
    row.Представление = "Номенклатура"
    row.ТипГруппировки = 0

    schema_name = "СхемаКомпоновкиДанных"
    try:
        buh = getattr(conn, "БухгалтерскиеОтчеты")
        report_object = manager.Создать()
        schema_name = str(buh.ИмяСхемыКомпоновкиДанныхОтчета(report_object, "АнализСчета"))
    except Exception as error:
        log(lines, tag + " schema name fallback: " + str(error)[:300])
    log(lines, tag + " schema=" + schema_name)

    schema = manager.ПолучитьМакет(schema_name)
    try:
        manager.НастроитьСхемуКомпоновкиДанных(schema, account)
    except Exception as error:
        log(lines, tag + " tune schema: " + str(error)[:400])

    variant = schema.ВариантыНастроек.Найти("АнализСчета")
    if variant is None:
        settings = schema.НастройкиПоУмолчанию
    else:
        settings = variant.Настройки
    set_prop(params, "СхемаКомпоновкиДанных", schema)
    set_prop(params, "НастройкиКомпоновкиДанных", settings)
    set_prop(params, "ДанныеРасшифровки", "")

    server = getattr(conn, "БухгалтерскиеОтчетыВызовСервера")
    formed = server.ПодготовитьОтчет(params)
    done = bool(formed.Выполнено)
    log(lines, tag + " done=" + str(done))
    if not done:
        log(lines, tag + " short=" + str(formed.КраткоеПредставлениеОшибки))
        log(lines, tag + " detail=" + str(formed.ПодробноеПредставлениеОшибки)[:4000])
        return None
    log(lines, tag + " control=" + str(formed.КонтрольноеСоотношениеИтоговВыполняется))
    return formed.Результат


def dump_sheet(lines, doc, tag, limit_rows=80):
    height = int(doc.ВысотаТаблицы)
    width = int(doc.ШиринаТаблицы)
    log(lines, tag + " size=" + str(height) + "x" + str(width))
    price_rows = 0
    colored = 0
    samples = 0
    max_row = height if height < 250 else 250
    for row_index in range(1, max_row + 1):
        texts = []
        row_has_price = False
        row_colored = False
        for col_index in range(1, width + 1):
            area = doc.Область(row_index, col_index, row_index, col_index)
            text = str(area.Текст).strip()
            if text:
                texts.append(text)
            if text == "Цена":
                row_has_price = True
            try:
                red = int(area.ЦветФона.Красный)
                green = int(area.ЦветФона.Зеленый)
                blue = int(area.ЦветФона.Синий)
                if red == 255 and green == 224 and blue == 130:
                    row_colored = True
            except Exception:
                pass
        if row_has_price:
            price_rows += 1
        if row_colored:
            colored += 1
        joined = " | ".join(texts)
        if row_has_price or "Кол." in joined or joined.startswith("БУ"):
            if samples < limit_rows:
                mark = ""
                if row_colored:
                    mark = " [COLOR]"
                log(lines, tag + " r%d%s: %s" % (row_index, mark, joined))
                samples += 1
    log(lines, tag + " price_rows=" + str(price_rows) + " colored_rows=" + str(colored))
    return price_rows, colored


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("File='C:\\1c\\БП_ДЕМО';Usr='Admin';App='PyCOM';Locale=ru_RU;")
        extensions = conn.ConfigurationExtensions.Get()
        for ext in extensions:
            log(lines, "ext " + str(ext.Name) + " active=" + str(ext.Active))

        query = conn.NewObject("Запрос")
        query.Текст = """
ВЫБРАТЬ ПЕРВЫЕ 8
    ПРЕДСТАВЛЕНИЕ(ХозрасчетныйОстаткиИОбороты.Субконто1) КАК Номенклатура,
    ХозрасчетныйОстаткиИОбороты.КоличествоКонечныйОстаток КАК Количество,
    ХозрасчетныйОстаткиИОбороты.СуммаКонечныйОстаток КАК Сумма,
    ВЫБОР
        КОГДА ХозрасчетныйОстаткиИОбороты.КоличествоКонечныйОстаток = 0
            ТОГДА 0
        ИНАЧЕ ХозрасчетныйОстаткиИОбороты.СуммаКонечныйОстаток / ХозрасчетныйОстаткиИОбороты.КоличествоКонечныйОстаток
    КОНЕЦ КАК Цена
ИЗ
    РегистрБухгалтерии.Хозрасчетный.ОстаткиИОбороты(
        ДАТАВРЕМЯ(2020, 1, 1),
        ДАТАВРЕМЯ(2026, 10, 4),
        ,
        ,
        Счет = &Счет,
        ,
        Организация = &Организация) КАК ХозрасчетныйОстаткиИОбороты
ГДЕ
    ХозрасчетныйОстаткиИОбороты.КоличествоКонечныйОстаток <> 0
    ИЛИ ХозрасчетныйОстаткиИОбороты.СуммаКонечныйОстаток <> 0
"""
        accounts = getattr(getattr(conn, "ПланыСчетов"), "Хозрасчетный")
        orgs = getattr(getattr(conn, "Справочники"), "Организации")
        query.УстановитьПараметр("Счет", accounts.НайтиПоКоду("41.01"))
        query.УстановитьПараметр("Организация", orgs.НайтиПоНаименованию("Конфетпром ООО", True))
        data = query.Выполнить().Выгрузить()
        log(lines, "expected rows=" + str(data.Count()))
        index = 0
        while index < data.Count() and index < 8:
            row = data.Get(index)
            log(lines, "expected " + str(row.Номенклатура)
                + " qty=" + str(row.Количество)
                + " sum=" + str(row.Сумма)
                + " price=" + str(row.Цена))
            index += 1

        doc = form_report(conn, "41.01", lines, "GOODS")
        if doc is not None:
            dump_sheet(lines, doc, "GOODS")
            try:
                doc.Записать(MXL)
                log(lines, "mxl saved")
            except Exception as error:
                log(lines, "mxl err " + str(error)[:300])

        doc_other = form_report(conn, "51", lines, "CASH")
        if doc_other is not None:
            dump_sheet(lines, doc_other, "CASH", 20)
    except Exception:
        log(lines, traceback.format_exc())
    finally:
        pythoncom.CoUninitialize()
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


if __name__ == "__main__":
    main()
