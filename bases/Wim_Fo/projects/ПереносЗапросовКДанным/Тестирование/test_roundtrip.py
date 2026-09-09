#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Функциональный тест внешней обработки "Перенос запросов к данным".

Проверяется полный цикл через COM-соединение с тестовой файловой базой:
1. Обработка подключается, модуль объекта компилируется.
2. Регистрационные сведения для БСП корректны.
3. Список элементов справочника читается.
4. Выгрузка существующего элемента в JSON.
5. Повторное чтение файла: формат распознан, сравнение показывает "без изменений".
6. Создание нового элемента из изменённого файла, в том числе с параметром ссылочного типа.
7. Обновление существующего элемента.
8. Контроль "битой" ссылки в значении параметра.
9. Побайтовое сравнение значений параметров после цикла выгрузка-загрузка.
10. Удаление созданных тестовых элементов.

Результат: reports/roundtrip_result.json и reports/export_sample.json (UTF-8).
Консольный вывод - только ASCII.
"""

import json
import os
import sys
import traceback

import pythoncom
import win32com.client

BASE_PATH = r"C:\1c\Cursor_1c\WORK\WIM_Fo"
USER = "admin"
PASSWORD = "1"

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPF_PATH = os.path.join(PROJECT_DIR, "Обработка", "build", "внПереносЗапросовКДанным.epf")

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
REPORT_FILE = os.path.join(REPORT_DIR, "roundtrip_result.json")
EXPORT_SAMPLE = os.path.join(REPORT_DIR, "export_sample.json")

# Внутреннее представление ссылки на существующий элемент справочника Активы (RUB),
# снятое с этой же базы. Используется для проверки переноса ссылочных значений.
REF_RUB = '{"#",f66cadf1-c157-4f10-8f05-3140a16e3e04,57:88485478dd6ede0f11f1ac43c8319dc9}'
# Тот же тип, но идентификатор объекта, которого в базе нет.
REF_MISSING = '{"#",f66cadf1-c157-4f10-8f05-3140a16e3e04,57:0000000000000000dead0000dead0001}'

TEST_CODE_NEW = "TEST_ПереносJSON"
TEST_UID_NEW = "b1b2b3b4-0001-4000-8000-000000000001"

checks = []


def safe_print(text):
    """Безопасный вывод в консоль - только ASCII."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(str(text).encode("ascii", "replace").decode("ascii"))


def check(name, condition, details=""):
    """Регистрирует результат проверки и печатает его в консоль."""
    checks.append({"name": name, "passed": bool(condition), "details": str(details)})
    safe_print("%-6s %s" % ("OK" if condition else "FAIL", name))
    if not condition and details:
        safe_print("       %s" % str(details).encode("ascii", "replace").decode("ascii"))
    return bool(condition)


def connect():
    """Устанавливает COM-соединение с файловой базой."""
    connector = win32com.client.Dispatch("V83.COMConnector")
    return connector.Connect(
        "File='{0}';Usr='{1}';Pwd='{2}';App='PyCOM';Locale=ru_RU;".format(BASE_PATH, USER, PASSWORD)
    )


def array_to_list(conn, com_array):
    """Преобразует 1С-Массив в список Python."""
    return [com_array.Получить(i) for i in range(com_array.Количество())]


def value_table_to_list(table, columns):
    """Преобразует 1С-ТаблицуЗначений в список словарей по указанным колонкам."""
    rows = []
    for i in range(table.Количество()):
        row = table.Получить(i)
        rows.append({name: getattr(row, name) for name in columns})
    return rows


def refs_array(conn, uuid_list):
    """Строит 1С-Массив ссылок справочника ЗапросыКДанным по списку идентификаторов."""
    result = conn.NewObject("Массив")
    manager = conn.Справочники.ЗапросыКДанным
    for uid in uuid_list:
        result.Добавить(manager.ПолучитьСсылку(conn.NewObject("УникальныйИдентификатор", uid)))
    return result


def existing_items(conn):
    """Возвращает список элементов справочника: идентификатор, наименование, код запроса."""
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Т.Ссылка КАК Ссылка, Т.Наименование КАК Наименование, Т.КодЗапроса КАК КодЗапроса "
        "ИЗ Справочник.ЗапросыКДанным КАК Т УПОРЯДОЧИТЬ ПО Т.Наименование"
    )
    table = query.Выполнить().Выгрузить()
    items = []
    for i in range(table.Количество()):
        row = table.Получить(i)
        items.append(
            {
                "uid": conn.String(row.Ссылка.УникальныйИдентификатор()),
                "Наименование": row.Наименование,
                "КодЗапроса": row.КодЗапроса,
            }
        )
    return items


def read_element(conn, uid):
    """Читает элемент справочника вместе с табличной частью параметров."""
    ref = conn.Справочники.ЗапросыКДанным.ПолучитьСсылку(
        conn.NewObject("УникальныйИдентификатор", uid)
    )
    obj = ref.ПолучитьОбъект()
    if obj is None:
        return None
    params = []
    for i in range(obj.Параметры.Количество()):
        row = obj.Параметры.Получить(i)
        params.append(
            {
                "Имя": row.Имя,
                "Тип": row.Тип,
                "Значение": row.Значение,
                "Внешний": bool(row.Внешний),
                "Идентификатор": conn.String(row.Идентификатор),
            }
        )
    return {
        "Код": obj.Код,
        "Наименование": obj.Наименование,
        "КодЗапроса": obj.КодЗапроса,
        "ТекстЗапроса": obj.ТекстЗапроса,
        "ПометкаУдаления": bool(obj.ПометкаУдаления),
        "Параметры": params,
    }


def delete_element(conn, uid):
    """Полностью удаляет элемент справочника, если он существует."""
    ref = conn.Справочники.ЗапросыКДанным.ПолучитьСсылку(
        conn.NewObject("УникальныйИдентификатор", uid)
    )
    obj = ref.ПолучитьОбъект()
    if obj is not None:
        obj.Удалить()
        return True
    return False


def load_from_json(conn, processor, payload):
    """Прогоняет словарь Python через обработку: чтение, сравнение, загрузка."""
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    read_result = processor.ПрочитатьДанныеВыгрузки(text)
    if not read_result.Успешно:
        return {"read_ok": False, "error": read_result.ОписаниеОшибки, "compare": [], "load": None}

    compare = value_table_to_list(
        processor.ТаблицаСравнения(read_result.Данные),
        ["Элемент", "Действие", "Поле", "ЗначениеВБазе", "ЗначениеВФайле"],
    )

    load_result = processor.ЗагрузитьЭлементы(read_result.Данные)
    load = {
        "Создано": int(load_result.Создано),
        "Обновлено": int(load_result.Обновлено),
        "Ошибок": int(load_result.Ошибок),
        "Протокол": array_to_list(conn, load_result.Протокол),
    }
    return {"read_ok": True, "error": "", "compare": compare, "load": load}


def main():
    pythoncom.CoInitialize()
    report = {}

    try:
        conn = connect()
        safe_print("Connected to test base")

        check("EPF file exists", os.path.isfile(EPF_PATH), EPF_PATH)

        # 1. Подключение обработки - компилирует модуль объекта.
        processor_manager = conn.ВнешниеОбработки
        processor = processor_manager.Создать(EPF_PATH, False)
        check("Object module compiles and processor instantiates", processor is not None)

        # 2. Регистрационные сведения для БСП.
        registration = processor.СведенияОВнешнейОбработке()
        report["СведенияОВнешнейОбработке"] = {
            "Вид": registration.Вид,
            "Наименование": registration.Наименование,
            "Версия": registration.Версия,
            "БезопасныйРежим": bool(registration.БезопасныйРежим),
            "Информация": registration.Информация,
            "КомандКоличество": int(registration.Команды.Количество()),
        }
        check(
            "BSP registration kind is a global data processor",
            registration.Вид == "ДополнительнаяОбработка",
            registration.Вид,
        )
        check("BSP registration declares one command", registration.Команды.Количество() == 1)
        check("Safe mode requested", bool(registration.БезопасныйРежим))

        # 3. Список элементов справочника.
        items_before = existing_items(conn)
        report["ЭлементыДоТеста"] = items_before
        catalog_table = processor.ТаблицаЗапросовКДанным()
        report["ТаблицаЗапросовКДанным"] = value_table_to_list(
            catalog_table, ["Пометка", "Наименование", "КодЗапроса", "Параметров"]
        )
        check(
            "Catalog list matches base content",
            catalog_table.Количество() == len(items_before),
            "processor=%d, query=%d" % (catalog_table.Количество(), len(items_before)),
        )

        if not items_before:
            check("Base has at least one element to export", False, "catalog is empty")
            raise RuntimeError("no source data")

        source = items_before[0]
        source_before = read_element(conn, source["uid"])
        report["ИсходныйЭлемент"] = source_before

        # 4. Выгрузка исходного элемента.
        export_result = processor.ВыгрузитьЭлементы(refs_array(conn, [source["uid"]]))
        export_text = export_result.ТекстJSON
        report["ПротоколВыгрузки"] = array_to_list(conn, export_result.Протокол)
        check("Export reports one element", int(export_result.Выгружено) == 1)

        os.makedirs(REPORT_DIR, exist_ok=True)
        with open(EXPORT_SAMPLE, "w", encoding="utf-8") as f:
            f.write(export_text)

        payload = json.loads(export_text)
        check("Export is valid JSON with format marker", payload.get("ФорматВыгрузки") == "ЗапросыКДанным")
        check("Export contains one element", len(payload.get("Элементы", [])) == 1)

        exported = payload["Элементы"][0]
        check(
            "Exported UUID matches source",
            exported.get("УникальныйИдентификатор") == source["uid"],
            "%s vs %s" % (exported.get("УникальныйИдентификатор"), source["uid"]),
        )
        check(
            "Exported query text matches source",
            exported.get("ТекстЗапроса") == source_before["ТекстЗапроса"],
        )
        check(
            "Exported parameter internal values match source",
            [p["ЗначениеВнутреннее"] for p in exported.get("Параметры", [])]
            == [p["Значение"] for p in source_before["Параметры"]],
        )
        check(
            "Reference-type parameters carry a decoded description",
            all("ЗначениеОписание" in p for p in exported.get("Параметры", [])),
        )
        check(
            "Every parameter description has a non-empty presentation",
            all(
                p["ЗначениеОписание"].get("Представление", "") != ""
                for p in exported.get("Параметры", [])
            ),
            [p["ЗначениеОписание"] for p in exported.get("Параметры", [])],
        )
        check(
            "Export date is written in ISO form",
            len(payload.get("ДатаВыгрузки", "")) == 19 and payload["ДатаВыгрузки"][4] == "-",
            payload.get("ДатаВыгрузки"),
        )

        # 5. Повторное чтение той же выгрузки: изменений быть не должно.
        idempotent = load_from_json(conn, processor, payload)
        report["ПовторноеЧтение"] = idempotent
        check("Re-read of own export succeeds", idempotent["read_ok"], idempotent["error"])
        check(
            "Re-import of unchanged export reports no differences",
            all(row["Действие"] == "Без изменений" for row in idempotent["compare"]),
            idempotent["compare"],
        )
        check(
            "Re-import updates the same element, creates nothing",
            idempotent["load"]["Создано"] == 0 and idempotent["load"]["Ошибок"] == 0,
            idempotent["load"],
        )

        source_after_reimport = read_element(conn, source["uid"])
        check(
            "Source element is unchanged after re-import",
            source_after_reimport == source_before,
            {"before": source_before, "after": source_after_reimport},
        )

        # 6. Создание нового элемента, включая параметр ссылочного типа и битую ссылку.
        delete_element(conn, TEST_UID_NEW)

        new_payload = json.loads(export_text)
        new_element = new_payload["Элементы"][0]
        new_element["УникальныйИдентификатор"] = TEST_UID_NEW
        new_element["Код"] = "TST000001"
        new_element["Наименование"] = "Тест переноса JSON"
        new_element["КодЗапроса"] = TEST_CODE_NEW
        new_element["ТекстЗапроса"] = "ВЫБРАТЬ 1 КАК Один ГДЕ &Актив = &Актив"
        new_element["Параметры"] = [
            {
                "НомерСтроки": 1,
                "Имя": "Актив",
                "Тип": "CatalogRef.Активы",
                "Внешний": False,
                "Идентификатор": "aaaaaaaa-0000-4000-8000-000000000001",
                "ЗначениеВнутреннее": REF_RUB,
                "ЗначениеОписание": {"ВидЗначения": "Ссылка", "Представление": "RUB"},
            },
            {
                "НомерСтроки": 2,
                "Имя": "АктивОтсутствующий",
                "Тип": "CatalogRef.Активы",
                "Внешний": False,
                "Идентификатор": "aaaaaaaa-0000-4000-8000-000000000002",
                "ЗначениеВнутреннее": REF_MISSING,
                "ЗначениеОписание": {"ВидЗначения": "Ссылка", "Представление": "Отсутствующий актив"},
            },
        ]

        creation = load_from_json(conn, processor, new_payload)
        report["СозданиеЭлемента"] = creation
        check("Read of modified export succeeds", creation["read_ok"], creation["error"])
        check(
            "Comparison marks the element as new",
            any(row["Действие"] == "Создание" for row in creation["compare"]),
            creation["compare"],
        )
        check(
            "Import creates exactly one element without errors",
            creation["load"]["Создано"] == 1 and creation["load"]["Ошибок"] == 0,
            creation["load"],
        )
        check(
            "Import warns about the unresolvable reference",
            any("не найден" in msg for msg in creation["load"]["Протокол"]),
            creation["load"]["Протокол"],
        )

        created = read_element(conn, TEST_UID_NEW)
        report["СозданныйЭлемент"] = created
        check("Created element exists at the UUID from the file", created is not None)
        check("Created element keeps the code from the file", created["Код"] == "TST000001", created["Код"])
        check(
            "Created element keeps the query code from the file",
            created["КодЗапроса"] == TEST_CODE_NEW,
            created["КодЗапроса"],
        )
        check(
            "Created element has both parameters",
            len(created["Параметры"]) == 2,
            created["Параметры"],
        )
        check(
            "Reference parameter value stored byte-identically",
            created["Параметры"][0]["Значение"] == REF_RUB,
            created["Параметры"][0]["Значение"],
        )
        check(
            "Parameter row identifiers transferred",
            created["Параметры"][0]["Идентификатор"] == "aaaaaaaa-0000-4000-8000-000000000001",
            created["Параметры"][0]["Идентификатор"],
        )

        # 7. Выгрузка созданного элемента и сверка с тем, что записывали.
        reexport = processor.ВыгрузитьЭлементы(refs_array(conn, [TEST_UID_NEW]))
        reexported = json.loads(reexport.ТекстJSON)["Элементы"][0]
        report["ПовторнаяВыгрузкаСозданного"] = reexported
        check(
            "Re-export of created element reproduces reference value",
            reexported["Параметры"][0]["ЗначениеВнутреннее"] == REF_RUB,
        )
        check(
            "Re-export resolves the reference to its presentation",
            reexported["Параметры"][0]["ЗначениеОписание"].get("Представление") == "RUB",
            reexported["Параметры"][0]["ЗначениеОписание"],
        )
        check(
            "Re-export marks the missing reference as not found",
            "Объект не найден" in str(reexported["Параметры"][1]["ЗначениеОписание"].get("Представление", "")),
            reexported["Параметры"][1]["ЗначениеОписание"],
        )

        # 8. Обновление существующего элемента.
        update_payload = json.loads(reexport.ТекстJSON)
        update_element = update_payload["Элементы"][0]
        update_element["ТекстЗапроса"] = "ВЫБРАТЬ 2 КАК Два"
        update_element["Наименование"] = "Тест переноса JSON 2"
        update_element["Параметры"] = update_element["Параметры"][:1]

        update = load_from_json(conn, processor, update_payload)
        report["ОбновлениеЭлемента"] = update
        check("Read of update file succeeds", update["read_ok"], update["error"])
        check(
            "Comparison lists the changed query text",
            any(row["Поле"] == "ТекстЗапроса" for row in update["compare"]),
            update["compare"],
        )
        check(
            "Comparison reports the parameter row that will be removed",
            any("Удалится параметр" in row["ЗначениеВБазе"] for row in update["compare"]),
            update["compare"],
        )
        check(
            "Import updates exactly one element without errors",
            update["load"]["Обновлено"] == 1 and update["load"]["Создано"] == 0 and update["load"]["Ошибок"] == 0,
            update["load"],
        )

        updated = read_element(conn, TEST_UID_NEW)
        report["ОбновленныйЭлемент"] = updated
        check("Query text updated in base", updated["ТекстЗапроса"] == "ВЫБРАТЬ 2 КАК Два", updated["ТекстЗапроса"])
        check("Parameter row removed in base", len(updated["Параметры"]) == 1, updated["Параметры"])

        # 9. Поиск по коду запроса, когда идентификатор в файле отсутствует.
        by_code_payload = json.loads(reexport.ТекстJSON)
        by_code_payload["Элементы"][0]["УникальныйИдентификатор"] = ""
        by_code_payload["Элементы"][0]["Наименование"] = "Тест поиска по коду"
        by_code = load_from_json(conn, processor, by_code_payload)
        report["ПоискПоКодуЗапроса"] = by_code
        check(
            "Element without UUID is matched by query code and updated",
            by_code["load"]["Обновлено"] == 1 and by_code["load"]["Создано"] == 0,
            by_code["load"],
        )

        # 10. Отклонение файла неверного формата.
        bad = processor.ПрочитатьДанныеВыгрузки('{"ФорматВыгрузки":"ЧтоТоДругое","Элементы":[]}')
        check("File of a foreign format is rejected", not bad.Успешно, bad.ОписаниеОшибки)
        broken = processor.ПрочитатьДанныеВыгрузки("{не json")
        check("Malformed JSON is rejected with a message", not broken.Успешно, broken.ОписаниеОшибки)

        # 11. Работа в безопасном режиме - так обработка запускается из БСП.
        safe_processor = processor_manager.Создать(EPF_PATH, True)
        safe_export = safe_processor.ВыгрузитьЭлементы(refs_array(conn, [source["uid"]]))
        check(
            "Export works in safe mode",
            int(safe_export.Выгружено) == 1 and len(safe_export.ТекстJSON) > 0,
        )

        # 12. Уборка тестовых данных.
        deleted = delete_element(conn, TEST_UID_NEW)
        check("Test element removed from base", deleted)

        items_after = existing_items(conn)
        report["ЭлементыПослеТеста"] = items_after
        check(
            "Catalog returned to its initial content",
            [i["uid"] for i in items_after] == [i["uid"] for i in items_before],
            {"before": items_before, "after": items_after},
        )

    except Exception:
        report["error"] = traceback.format_exc()
        safe_print("EXCEPTION - see report file")
        safe_print(report["error"].encode("ascii", "replace").decode("ascii"))
    finally:
        pythoncom.CoUninitialize()

    passed = sum(1 for c in checks if c["passed"])
    report["checks"] = checks
    report["summary"] = {"total": len(checks), "passed": passed, "failed": len(checks) - passed}

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    safe_print("")
    safe_print("Checks: %d passed, %d failed" % (passed, len(checks) - passed))
    safe_print("Report saved: %s" % REPORT_FILE)

    return 0 if passed == len(checks) and "error" not in report else 1


if __name__ == "__main__":
    sys.exit(main())
