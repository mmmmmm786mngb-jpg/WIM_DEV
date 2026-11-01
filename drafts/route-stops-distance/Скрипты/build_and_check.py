#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Собирает схему СКД треугольника расстояний, заполняет демо-данные
и выводит результат компоновки в текстовый файл.
"""

import os
import traceback

import pythoncom
import win32com.client

OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(OUT_DIR, "compose_result.txt")
SCHEMA_PATH = os.path.join(
    OUT_DIR,
    "src",
    "РасстоянияМеждуОстановками",
    "Templates",
    "ОсновнаяСхемаКомпоновкиДанных",
    "Ext",
    "Template.xml",
)

QUERY_TEXT = (
    "ВЫБРАТЬ\n"
    "    ОстановкиПоМаршруту.Маршрут КАК Маршрут,\n"
    "    ОстановкиПоМаршруту.Остановка КАК Остановка,\n"
    "    ОстановкиПоМаршруту.Расстояние КАК Расстояние\n"
    "ИЗ\n"
    "    РегистрСведений.ОстановкиПоМаршруту КАК ОстановкиПоМаршруту"
)

CELL_EXPRESSION = (
    "ВЫБОР\n"
    "    КОГДА Расстояние = ВычислитьВыражение(\"Максимум(Расстояние)\", \"ОбщийИтог\")\n"
    "        ТОГДА Остановка\n"
    "    ИНАЧЕ ВычислитьВыражение(\"Максимум(Расстояние)\", \"ОбщийИтог\") - Расстояние\n"
    "КОНЕЦ"
)

DEMO_ROWS = [
    ("Север", "Борок", 0),
    ("Север", "Заречье", 2.5),
    ("Север", "Мологино", 6.3),
    ("Север", "Пристань", 11),
    ("Север", "Лужки", 15.4),
    ("Север", "Озерки", 19),
    ("Север", "Мост", 24.8),
    ("Север", "Брод", 29.1),
    ("Север", "Поляна", 33.6),
    ("Север", "Роща", 38),
    ("Север", "Холм", 42.7),
    ("Север", "Речка", 47.2),
    ("Север", "Паром", 51.9),
    ("Север", "Дачи", 56.4),
    ("Север", "Сады", 61),
    ("Север", "Выселки", 65.8),
    ("Север", "Пруд", 70.3),
    ("Север", "Гать", 75),
    ("Север", "Разъезд", 79.6),
    ("Север", "Слобода", 84.2),
    ("Север", "Курган", 89),
    ("Север", "Затон", 93.5),
    ("Север", "Перевоз", 98.1),
    ("Север", "Причал", 102.8),
    ("Север", "Финиш", 108),
    ("Южный", "Вокзал", 0),
    ("Южный", "Рынок", 1.5),
    ("Южный", "Парк", 4.2),
    ("Южный", "Школа", 7.1),
    ("Южный", "Кольцо", 12.4),
]


def connect():
    password = os.environ.get("OU_PWD", "")
    com = win32com.client.Dispatch("V83.COMConnector")
    conn_str = "File='C:\\1c\\Cursor_1c\\WORK\\OU_Training';Usr='admin';Pwd='" + password + "';"
    return com.Connect(conn_str)


def enum_value(conn, enum_name, item_name):
    enum_obj = getattr(conn, enum_name)
    return getattr(enum_obj, item_name)


def type_of(conn, name):
    description = conn.NewObject("ОписаниеТипов", name)
    return description.Типы().Получить(0)


def add_typed(conn, collection, type_name):
    return collection.Добавить(type_of(conn, type_name))


def field(conn, name):
    return conn.NewObject("ПолеКомпоновкиДанных", name)


def add_dataset_field(conn, dataset, name, ascending, order_by=None, presentation=None):
    item = add_typed(conn, dataset.Поля, "ПолеНабораДанныхСхемыКомпоновкиДанных")
    item.Поле = name
    item.ПутьКДанным = name
    item.Заголовок = name
    if presentation:
        item.ВыражениеПредставления = presentation
    if order_by:
        expression = item.ВыраженияУпорядочивания.Добавить()
        expression.Выражение = order_by
        expression.ТипУпорядочивания = ascending
    return item


def add_query_dataset(conn, schema, ascending):
    source = schema.ИсточникиДанных.Добавить()
    source.Имя = "ИсточникДанных1"
    source.ТипИсточникаДанных = "Local"
    dataset = add_typed(conn, schema.НаборыДанных, "НаборДанныхЗапросСхемыКомпоновкиДанных")
    dataset.Имя = "НаборДанных1"
    dataset.ИсточникДанных = "ИсточникДанных1"
    dataset.Запрос = QUERY_TEXT
    dataset.АвтоЗаполнениеДоступныхПолей = True
    return dataset


def fill_demo(conn, log):
    manager = getattr(conn.РегистрыСведений, "ОстановкиПоМаршруту")
    record_set = manager.СоздатьНаборЗаписей()
    record_set.Записать()
    for route, stop, distance in DEMO_ROWS:
        record = manager.СоздатьМенеджерЗаписи()
        record.Маршрут = route
        record.Остановка = stop
        record.Расстояние = distance
        record.Записать()
    log.append("demo rows: " + str(len(DEMO_ROWS)))


def add_group_field(conn, group, name, group_type):
    item = add_typed(conn, group.ПоляГруппировки.Элементы, "ПолеГруппировкиКомпоновкиДанных")
    item.Поле = field(conn, name)
    item.ТипГруппировки = group_type
    item.Использование = True


def add_order(conn, owner, name, direction):
    item = add_typed(conn, owner.Порядок.Элементы, "ЭлементПорядкаКомпоновкиДанных")
    item.Поле = field(conn, name)
    item.ТипУпорядочивания = direction
    item.Использование = True


def add_selected(conn, owner, name):
    item = add_typed(conn, owner.Выбор.Элементы, "ВыбранноеПолеКомпоновкиДанных")
    item.Поле = field(conn, name)
    item.Использование = True


def add_link_filter(conn, owner, left_name, comparison, right_name):
    item = add_typed(conn, owner.Отбор.Элементы, "ЭлементОтбораКомпоновкиДанных")
    item.ЛевоеЗначение = field(conn, left_name)
    item.ВидСравнения = comparison
    item.ПравоеЗначение = field(conn, right_name)
    item.Использование = True


def set_output_parameter(conn, settings, name, value):
    parameter = conn.NewObject("ПараметрКомпоновкиДанных", name)
    item = settings.ПараметрыВывода.НайтиЗначениеПараметра(parameter)
    item.Использование = True
    item.Значение = value


def build_schema(conn):
    equal = enum_value(conn, "ВидСравненияКомпоновкиДанных", "Равно")
    less_or_equal = enum_value(conn, "ВидСравненияКомпоновкиДанных", "МеньшеИлиРавно")
    ascending = enum_value(conn, "НаправлениеСортировкиКомпоновкиДанных", "Возр")
    group_items = enum_value(conn, "ТипГруппировкиКомпоновкиДанных", "Элементы")
    no_totals = enum_value(conn, "РасположениеИтоговКомпоновкиДанных", "Нет")
    output_text = enum_value(conn, "ТипВыводаТекстаКомпоновкиДанных", "Выводить")
    hide_text = enum_value(conn, "ТипВыводаТекстаКомпоновкиДанных", "НеВыводить")

    schema = conn.NewObject("СхемаКомпоновкиДанных")
    add_query_dataset(conn, schema, ascending)

    nested = schema.ВложенныеСхемыКомпоновкиДанных.Добавить()
    nested.Имя = "ПредыдущиеОстановкиПоМаршруту"
    nested.Заголовок = "Предыдущие остановки по маршруту"
    nested_schema = nested.Схема
    if nested_schema is None:
        created = conn.NewObject("СхемаКомпоновкиДанных")
        try:
            nested.Схема = created
            nested_schema = nested.Схема
        except Exception as error:
            raise RuntimeError("nested schema is empty: " + str(error))
    add_query_dataset(conn, nested_schema, ascending)
    add_dataset_field(
        conn,
        nested_schema.НаборыДанных.Получить(0),
        "Остановка",
        ascending,
        "Расстояние",
        CELL_EXPRESSION,
    )

    row_field = nested_schema.ВычисляемыеПоля.Добавить()
    row_field.ПутьКДанным = "СтрокаОтчета"
    row_field.Заголовок = "Строка"
    row_field.Выражение = "1"

    cell = nested_schema.ВычисляемыеПоля.Добавить()
    cell.ПутьКДанным = "Ячейка"
    cell.Заголовок = " "
    cell.Выражение = CELL_EXPRESSION
    cell.ТипЗначения = conn.NewObject("ОписаниеТипов", "Строка")

    total = nested_schema.ПоляИтога.Добавить()
    total.ПутьКДанным = "Ячейка"
    total.Выражение = "Максимум(Ячейка)"

    settings = schema.НастройкиПоУмолчанию
    group = add_typed(conn, settings.Структура, "ГруппировкаКомпоновкиДанных")
    add_group_field(conn, group, "Маршрут", group_items)
    add_group_field(conn, group, "Остановка", group_items)
    add_group_field(conn, group, "Расстояние", group_items)
    add_order(conn, group, "Маршрут", ascending)
    add_order(conn, group, "Расстояние", ascending)
    fields_only_in_totals = enum_value(
        conn, "РасположениеПолейГруппировкиКомпоновкиДанных", "ОтдельноИТолькоВИтогах"
    )
    set_output_parameter(conn, group, "РасположениеПолейГруппировки", fields_only_in_totals)
    set_output_parameter(conn, group, "РасположениеИтогов", no_totals)
    set_output_parameter(conn, group, "ВыводитьЗаголовок", hide_text)
    set_output_parameter(conn, group, "ВыводитьОтбор", hide_text)

    route_filter = add_typed(conn, settings.Отбор.Элементы, "ЭлементОтбораКомпоновкиДанных")
    route_filter.ЛевоеЗначение = field(conn, "Маршрут")
    route_filter.ВидСравнения = equal
    route_filter.Использование = False
    route_filter.ИдентификаторПользовательскойНастройки = "ОтборМаршрут"
    route_filter.ПредставлениеПользовательскойНастройки = "Маршрут"

    nested_item = add_typed(conn, group.Структура, "НастройкиВложенногоОбъектаКомпоновкиДанных")
    nested_item.УстановитьИдентификатор("ПредыдущиеОстановкиПоМаршруту")
    object_id = str(nested_item.ИдентификаторОбъекта)
    own_id = str(nested_item.Идентификатор)
    if object_id != "ПредыдущиеОстановкиПоМаршруту":
        raise RuntimeError("object id=[" + object_id + "] own id=[" + own_id + "]")
    nested_settings = nested_item.Настройки
    add_link_filter(conn, nested_settings, "Маршрут", equal, "ОбъектНастройкиВладелец.Маршрут")
    add_link_filter(conn, nested_settings, "Расстояние", less_or_equal, "ОбъектНастройкиВладелец.Расстояние")
    add_selected(conn, nested_settings, "Остановка")

    table = add_typed(conn, nested_settings.Структура, "ТаблицаКомпоновкиДанных")
    column = table.Колонки.Добавить()
    add_group_field(conn, column, "Остановка", group_items)
    add_order(conn, column, "Остановка", ascending)
    add_selected(conn, column, "Остановка")
    set_output_parameter(conn, table, "ГоризонтальноеРасположениеОбщихИтогов", no_totals)
    set_output_parameter(conn, table, "ВертикальноеРасположениеОбщихИтогов", no_totals)

    set_output_parameter(conn, settings, "Заголовок", "Таблица расстояний")
    set_output_parameter(conn, settings, "ВыводитьЗаголовок", output_text)
    set_output_parameter(conn, settings, "ВыводитьОтбор", hide_text)
    set_output_parameter(conn, settings, "ГоризонтальноеРасположениеОбщихИтогов", no_totals)
    set_output_parameter(conn, settings, "ВертикальноеРасположениеОбщихИтогов", no_totals)
    set_output_parameter(conn, nested_settings, "ВыводитьЗаголовок", hide_text)
    set_output_parameter(conn, nested_settings, "ВыводитьОтбор", hide_text)
    set_output_parameter(conn, nested_settings, "ГоризонтальноеРасположениеОбщихИтогов", no_totals)
    set_output_parameter(conn, nested_settings, "ВертикальноеРасположениеОбщихИтогов", no_totals)
    return schema


def dump_fields(fields, lines, prefix, depth):
    if fields is None or depth > 5:
        return
    count = int(fields.Количество())
    for index in range(count):
        item = fields.Получить(index)
        lines.append(prefix + str(item.Поле) + " | " + str(item.Заголовок))
        dump_fields(item.Элементы, lines, prefix + "  ", depth + 1)


def find_field(fields, title, depth=0):
    if fields is None or depth > 6:
        return None
    for index in range(int(fields.Количество())):
        item = fields.Получить(index)
        if str(item.Заголовок) == title:
            return item
        found = find_field(item.Элементы, title, depth + 1)
        if found is not None:
            return found
    return None


def compose(conn, schema, log):
    composer = conn.NewObject("КомпоновщикНастроекКомпоновкиДанных")
    available = conn.NewObject("ИсточникДоступныхНастроекКомпоновкиДанных", schema)
    composer.Инициализировать(available)
    composer.ЗагрузитьНастройки(schema.НастройкиПоУмолчанию)
    group = composer.Настройки.Структура.Получить(0)
    nested_item = group.Структура.Получить(0)
    nested_settings = nested_item.Настройки
    route_field = find_field(nested_settings.ДоступныеПоляОтбора.Элементы, "Объект владелец.Маршрут")
    distance_field = find_field(nested_settings.ДоступныеПоляОтбора.Элементы, "Объект владелец.Расстояние")
    filters = nested_settings.Отбор.Элементы
    filters.Получить(0).ПравоеЗначение = route_field.Поле
    filters.Получить(1).ПравоеЗначение = distance_field.Поле
    writer = conn.NewObject("ЗаписьXML")
    writer.УстановитьСтроку()
    getattr(conn, "СериализаторXDTO").ЗаписатьXML(writer, route_field.Поле)
    log.append("owner route field xml: " + str(writer.Закрыть()))
    layout_composer = conn.NewObject("КомпоновщикМакетаКомпоновкиДанных")
    layout = layout_composer.Выполнить(schema, composer.ПолучитьНастройки())
    processor = conn.NewObject("ПроцессорКомпоновкиДанных")
    processor.Инициализировать(layout)
    document = conn.NewObject("ТабличныйДокумент")
    output = conn.NewObject("ПроцессорВыводаРезультатаКомпоновкиДанныхВТабличныйДокумент")
    output.УстановитьДокумент(document)
    output.Вывести(processor)
    squeeze_empty_rows(conn, document)
    return document


def squeeze_empty_rows(conn, document):
    height = int(document.ВысотаТаблицы)
    width = int(document.ШиринаТаблицы)
    if width == 0:
        return
    empty_rows = []
    for row_index in range(1, height + 1):
        empty = True
        for column_index in range(1, width + 1):
            area = document.Область(row_index, column_index, row_index, column_index)
            if str(area.Текст).strip() != "":
                empty = False
                break
        if empty:
            empty_rows.append(row_index)
    shift = enum_value(conn, "ТипСмещенияТабличногоДокумента", "ПоВертикали")
    for row_index in reversed(empty_rows):
        document.УдалитьОбласть(document.Область("R" + str(row_index)), shift)


def document_text(document):
    height = int(document.ВысотаТаблицы)
    width = int(document.ШиринаТаблицы)
    lines = ["size " + str(height) + "x" + str(width)]
    for row_index in range(1, height + 1):
        cells = []
        row_area = document.Область("R" + str(row_index))
        for column_index in range(1, width + 1):
            area = document.Область(row_index, column_index, row_index, column_index)
            cells.append(repr(str(area.Текст).replace("\n", " ")))
        lines.append(
            str(row_index)
            + " h="
            + str(row_area.ВысотаСтроки)
            + " auto="
            + str(bool(row_area.АвтоВысотаСтроки))
            + " | "
            + " | ".join(cells)
        )
    return "\n".join(lines)


def save_schema(conn, schema):
    writer = conn.NewObject("ЗаписьXML")
    writer.УстановитьСтроку()
    serializer = getattr(conn, "СериализаторXDTO")
    serializer.ЗаписатьXML(writer, schema)
    text = writer.Закрыть()
    if not text.startswith("<?xml"):
        text = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + text
    with open(SCHEMA_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    return len(text)


def main():
    pythoncom.CoInitialize()
    log = []
    try:
        conn = connect()
        log.append("connected")
        fill_demo(conn, log)
        schema = build_schema(conn)
        log.append("schema built")
        stored = schema.ВложенныеСхемыКомпоновкиДанных.Получить(0).Схема
        if stored is None:
            log.append("stored nested schema is none")
        else:
            log.append("stored nested datasets " + str(stored.НаборыДанных.Количество()))
            if int(stored.НаборыДанных.Количество()) > 0:
                nested_ds = stored.НаборыДанных.Получить(0)
                log.append("stored nested fields " + str(nested_ds.Поля.Количество()))
        dataset = schema.НаборыДанных.Получить(0)
        log.append("parent fields " + str(dataset.Поля.Количество()))
        log.append("query " + str(dataset.Запрос)[:80])
        for index in range(int(dataset.Поля.Количество())):
            item = dataset.Поля.Получить(index)
            log.append("field [" + str(item.ПутьКДанным) + "] src [" + str(item.Поле) + "]")
        document = compose(conn, schema, log)
        log.append("composed")
        log.append(document_text(document))
        size = save_schema(conn, schema)
        log.append("schema bytes " + str(size))
    except Exception:
        log.append(traceback.format_exc())
    finally:
        pythoncom.CoUninitialize()
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(log))
    print("LOG " + str(len(log)))


if __name__ == "__main__":
    main()
