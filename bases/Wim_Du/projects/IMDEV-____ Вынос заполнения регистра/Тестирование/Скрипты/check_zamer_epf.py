"""Проверка обработки ЗамерЗаполненияИсторииКвал на временной файловой базе ДУ 1.5.30.4.

Создает тестовые бумаги с версиями в РегистрСведений.ВерсииОбъектов (сериализация как в БСП),
запускает обработку через COM и сверяет записи обоих алгоритмов с ожидаемыми.

Запуск: python check_zamer_epf.py <каталог файловой базы | srvr:<сервер>\<база>> <путь к epf> [<файл json>]
Для серверной базы (вход по ОС) тестовые данные не создаются: только прогон обработки, без записи.
"""
import datetime as dt
import json
import sys

import win32com.client

TAG = "T_ZAMER"

# Версии по бумагам: (дата версии, значение признака или None - версия без данных).
# Ожидаемые записи - по алгоритму обработчика: обход версий по убыванию номера, запись True
# на каждый день, где до него (по срезу) еще нет True.
CASES = {
    "Облигация А": ("Облигации", True, [("2026-01-10 10:00", False), ("2026-02-01 09:00", True),
                                        ("2026-02-01 18:00", True), ("2026-03-05 12:00", True)],
                    ["20260201", "20260305"]),
    "Облигация Б": ("Облигации", True, [("2026-01-10 10:00", False), ("2026-02-02 10:00", False)], []),
    "Облигация В": ("Облигации", True, [("2026-01-15 10:00", True), ("2026-02-15 10:00", False),
                                        ("2026-03-15 10:00", True)], ["20260115", "20260315"]),
    "Облигация Г": ("Облигации", True, [("2026-01-20 10:00", None), ("2026-01-25 10:00", True)],
                    ["20260125"]),
    "Облигация Д без квал": ("Облигации", False, [("2026-01-20 10:00", True)], None),
    "Акция А": ("Акции", True, [("2026-04-01 10:00", True), ("2026-04-02 10:00", True)],
                ["20260401", "20260402"]),
}


def date_1c(c, text):
    value = dt.datetime.strptime(text, "%Y-%m-%d %H:%M")
    date_type = c.NewObject("ОписаниеТипов", "Дата").Типы().Получить(0)
    return c.XMLЗначение(date_type, value.strftime("%Y-%m-%dT%H:%M:%S"))


def write_load(obj):
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def prepare(c):
    for name, (catalog, current_flag, versions, _expected) in CASES.items():
        manager = getattr(c.Справочники, catalog)
        full_name = f"{TAG} {name}"
        ref = manager.НайтиПоНаименованию(full_name, True)
        obj = manager.СоздатьЭлемент() if ref.Пустая() else ref.ПолучитьОбъект()
        obj.Наименование = full_name
        obj.ЦБДляКвалИнвестора = current_flag
        bond_ref = write_load(obj)

        assets = c.Справочники.Активы
        asset_ref = assets.НайтиПоНаименованию(full_name, True)
        asset = assets.СоздатьЭлемент() if asset_ref.Пустая() else asset_ref.ПолучитьОбъект()
        asset.Наименование = full_name
        asset.Объект = bond_ref
        write_load(asset)

        record_set = c.РегистрыСведений.ВерсииОбъектов.СоздатьНаборЗаписей()
        record_set.Отбор.Объект.Установить(bond_ref)
        for number, (version_date, flag) in enumerate(versions, start=1):
            record = record_set.Добавить()
            record.Объект = bond_ref
            record.НомерВерсии = number
            record.ДатаВерсии = date_1c(c, version_date)
            if flag is not None:
                obj.ЦБДляКвалИнвестора = flag
                data = c.ВерсионированиеОбъектов.СериализоватьОбъект(obj)
                record.ВерсияОбъекта = c.NewObject("ХранилищеЗначения", data, c.NewObject("СжатиеДанных", 9))
                record.РазмерДанных = data.Размер()
        record_set.Записать(True)


def run(c, epf_path):
    protection = c.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    processing = c.ВнешниеОбработки.Создать(epf_path, False, protection)
    params = c.NewObject("Структура")
    params.Вставить("ЛимитБумаг", 1000)
    params.Вставить("ЛимитСекунд", 120)
    params.Вставить("Зерно", 1)
    params.Вставить("ЗамерятьВендор", True)
    params.Вставить("ЗамерятьБыстрый", True)
    state = processing.НовоеСостояние(params)
    portions = 1
    while not processing.ВыполнитьПорцию(state, 5000):
        portions += 1
    report = processing.ДанныеОтчета(state)
    return processing.ТекстДанныхОтчета(report.Данные), report.Текст, portions


def main():
    base_dir, epf_path = sys.argv[1], sys.argv[2]
    json_path = sys.argv[3] if len(sys.argv) > 3 else None
    server_base = base_dir.startswith("srvr:")
    if server_base:
        server, ref = base_dir[5:].split("\\", 1)
        conn_str = f'Srvr="{server}";Ref="{ref}";'
    else:
        conn_str = f'File="{base_dir}";'
    c = win32com.client.Dispatch("V83.COMConnector").Connect(conn_str)
    if not server_base:
        prepare(c)
    text_json, text_report, portions = run(c, epf_path)
    if server_base:
        print(text_report)
        print("порций:", portions)
        if json_path:
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(text_json)
        return 0
    data = json.loads(text_json)
    if json_path:
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(text_json)

    print(text_report)
    print("порций:", portions)
    expected_papers = {n for n, case in CASES.items() if case[3] is not None}
    expected_writes = sum(len(case[3]) for case in CASES.values() if case[3] is not None)
    details = data["Детали"]
    writes_vendor = sum(d["ЗаписейВендор"] for d in details)
    writes_fast = sum(d["ЗаписейБыстрый"] for d in details)
    print("бумаг в замере:", len(details), "ожидалось:", len(expected_papers))
    print("записей: обновление", writes_vendor, "быстрый", writes_fast, "ожидалось", expected_writes)
    print("совпало:", sum(1 for d in details if d["Совпало"]), "расхождения:", data["Расхождения"])
    print("ошибки:", data["Ошибки"])
    ok = (len(details) == len(expected_papers) and writes_vendor == expected_writes
          and writes_fast == expected_writes and not data["Расхождения"] and not data["Ошибки"])
    print("ИТОГ:", "OK" if ok else "РАСХОЖДЕНИЕ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
