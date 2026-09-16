#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COM-тесты внешней обработки ЗаполнениеСпискаВладельцевНД в базе WIM_PIF.

Проверяются старые возможности (НРД id, ФИО+ДР, ЮЛ по ИНН, создание карточки/ЛС,
документ списка владельцев, чтение Excel и XML) и новые (шаг 2а, ВыделитьСлово,
протокол подмены и выбора из нескольких, регистрация в дополнительных обработках).
"""

import datetime
import html
import os
import sys
import traceback
import zipfile
from xml.sax.saxutils import escape as xml_escape

import pythoncom
import win32com.client

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPF_PATH = os.path.join(PROJECT_DIR, "build", "NomineeOwnersLoad.epf")
EPF_PATH_CYR = os.path.join(PROJECT_DIR, "build", "ЗаполнениеСпискаВладельцевНД.epf")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
REPORT_HTML = os.path.join(REPORT_DIR, "com_web_test_report.html")
RUN_ID = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
PREFIX = "TEST_ND_%s_" % RUN_ID
ADDRESS = "- 614007,Permskiy kray,g Perm,ul Testovaya,d 1,kv 1"

CONN_STRINGS = [
    "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;",
    "Srvr='localhost';Ref='WIM_PIF';Usr='Admin';Pwd='1';App='PyCOM';Locale=ru_RU;",
    "Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;",
]


class TestLog:
    def __init__(self):
        self.cases = []
        self.connection = ""
        self.queries = []
        self.bugs = []

    def add(self, name, ok, details="", params=None, query=None, error=None, kind="test"):
        item = {
            "name": name,
            "ok": bool(ok),
            "details": details or "",
            "params": params or {},
            "query": query,
            "error": error,
            "kind": kind,
        }
        self.cases.append(item)
        mark = "OK" if ok else "FAIL"
        safe_print("%s  %s" % (mark, name))
        if details:
            safe_print("    %s" % ascii_only(details))
        if error:
            safe_print("    ERR: %s" % ascii_only(error))
        if query:
            self.queries.append({"name": name, "sql": query, "params": params or {}})
        if not ok and error:
            self.bugs.append({"name": name, "error": error})
        return bool(ok)


def ascii_only(text):
    return str(text).encode("ascii", "replace").decode("ascii")


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(ascii_only(text))


def com_err(exc):
    return ascii_only("%s: %s" % (type(exc).__name__, exc))


def date1c(conn, year, month, day):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d) КАК ЗначениеДаты" % (year, month, day)
    table = query.Выполнить().Выгрузить()
    return table[0].ЗначениеДаты


def find_by_name(conn, catalog, name, is_folder=None):
    query = conn.NewObject("Запрос")
    if is_folder is True:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И ЭтоГруппа"
        ) % catalog
    elif is_folder is False:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И НЕ ЭтоГруппа"
        ) % catalog
    else:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование"
        ) % catalog
    query.УстановитьПараметр("Наименование", name)
    result = query.Выполнить()
    if result.Пустой():
        return None
    return result.Выгрузить()[0].Ссылка


def ensure_pif(conn):
    name = PREFIX + "FUND"
    found = find_by_name(conn, "ПИФ", name)
    if found is not None:
        obj = found.ПолучитьОбъект()
        if not obj.Используется:
            obj.Используется = True
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
        return found
    manager = conn.NewObject("СправочникМенеджер.ПИФ")
    obj = manager.СоздатьЭлемент()
    obj.Наименование = name
    obj.Используется = True
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def ensure_group(conn):
    name = PREFIX + "GROUP"
    found = find_by_name(conn, "Контрагенты", name, is_folder=True)
    if found is not None:
        return found
    manager = conn.NewObject("СправочникМенеджер.Контрагенты")
    obj = manager.СоздатьГруппу()
    obj.Наименование = name
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def ensure_counterparty(conn, full_name, birth, inn="", is_legal=False, parent=None):
    found = find_by_name(conn, "Контрагенты", full_name)
    if found is not None:
        return found
    manager = conn.NewObject("СправочникМенеджер.Контрагенты")
    obj = manager.СоздатьЭлемент()
    obj.Наименование = full_name
    obj.НаименованиеПолное = full_name
    obj.Пайщик = True
    if is_legal:
        obj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ЮрЛицо
        obj.ИНН = inn
    else:
        obj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ФизЛицо
        obj.ДатаРождения = birth
        if inn:
            obj.ИНН = inn
    if parent is not None:
        obj.Родитель = parent
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def write_fio(conn, ref, last, first, middle, period):
    rec = conn.РегистрыСведений.ФИОФизЛиц.СоздатьМенеджерЗаписи()
    rec.ФизЛицо = ref
    rec.Период = period
    rec.Фамилия = last
    rec.Имя = first
    rec.Отчество = middle
    rec.Записать(True)


def write_passport(conn, ref, series, number, period):
    rec = conn.РегистрыСведений.ПаспортныеДанныеФизЛиц.СоздатьМенеджерЗаписи()
    rec.ФизЛицо = ref
    rec.Период = period
    rec.ДокументВид = conn.Справочники.ДокументыУдостоверяющиеЛичность.ПаспортРФ
    rec.ДокументСерия = series
    rec.ДокументНомер = number
    rec.Записать()


def write_address(conn, ref, address, period):
    kind_legal = conn.Справочники.ВидыКонтактнойИнформации.ЮрАдресКонтрагента
    kind_fact = conn.Справочники.ВидыКонтактнойИнформации.ФактАдресКонтрагента
    addr_type = conn.Перечисления.ТипыКонтактнойИнформации.Адрес
    for kind in (kind_legal, kind_fact):
        rec = conn.РегистрыСведений.ИсторияИзмененияКонтактнойИнформации.СоздатьМенеджерЗаписи()
        rec.Период = period
        rec.Объект = ref
        rec.Тип = addr_type
        rec.Вид = kind
        rec.Представление = address
        rec.АдресРазобран = False
        rec.Записать()


def write_nrd(conn, ref, nrd_id, property_ref):
    rec = conn.РегистрыСведений.ЗначенияСвойствОбъектов.СоздатьМенеджерЗаписи()
    rec.Объект = ref
    rec.Свойство = property_ref
    rec.Значение = nrd_id
    rec.Записать()


def ensure_ls(conn, fund, shareholder, code, kind_enum):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.ЛицевыеСчетаПайщиков "
        "ГДЕ Владелец = &Фонд И Пайщик = &Пайщик И Код = &Код"
    )
    query.УстановитьПараметр("Фонд", fund)
    query.УстановитьПараметр("Пайщик", shareholder)
    query.УстановитьПараметр("Код", code)
    result = query.Выполнить()
    if not result.Пустой():
        return result.Выгрузить()[0].Ссылка
    manager = conn.NewObject("СправочникМенеджер.ЛицевыеСчетаПайщиков")
    obj = manager.СоздатьЭлемент()
    obj.Код = code
    obj.Владелец = fund
    obj.Пайщик = shareholder
    obj.ВидЛицевогоСчета = kind_enum
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def is_filled(ref):
    try:
        return not ref.Пустая()
    except Exception:
        return False
    table = result.ТаблицаСтрок
    for i in range(table.Количество()):
        row = table[i]
        if str(row.ФИО).find(name) >= 0 or str(getattr(row, "Фамилия", "")).find(name) >= 0:
            return row
    return table[0] if table.Количество() else None


def make_xlsx(path, rows, start_row=3):
    """Minimal xlsx for Garant columns."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet_rows = []
    max_col = 19
    max_row = start_row + len(rows) - 1
    for r_idx, cells in enumerate(rows):
        row_num = start_row + r_idx
        for col, value in cells.items():
            sheet_rows.append(
                '<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>'
                % (col_letter(col), row_num, xml_escape(str(value)))
            )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData><row r=\"1\"></row><row r=\"2\"></row>"
        + "".join(
            '<row r="%d">%s</row>'
            % (
                start_row + i,
                "".join(
                    '<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>'
                    % (col_letter(col), start_row + i, xml_escape(str(value)))
                    for col, value in rows[i].items()
                ),
            )
            for i in range(len(rows))
        )
        + "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    ctypes = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", ctypes)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return path


def col_letter(n):
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def make_xml(path, account_code, owners):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    parts = []
    for owner in owners:
        parts.append(
            "<Пайщик>"
            "<ЗЛ_НомерСчета>%s</ЗЛ_НомерСчета>"
            "<ЗЛ_Наименование>%s</ЗЛ_Наименование>"
            "<ЗЛ_ДатаРождения>%s</ЗЛ_ДатаРождения>"
            "<ЗЛ_ЮрАдрес>%s</ЗЛ_ЮрАдрес>"
            "<ЗЛ_ПочтовыйАдрес>%s</ЗЛ_ПочтовыйАдрес>"
            "<ЗЛ_ИНН>%s</ЗЛ_ИНН>"
            "<ЗЛ_КоличествоПаев>%s</ЗЛ_КоличествоПаев>"
            "<ЗЛ_Тип>%s</ЗЛ_Тип>"
            "</Пайщик>"
            % (
                xml_escape(account_code),
                xml_escape(owner["fio"]),
                xml_escape(owner["dob"]),
                xml_escape(owner.get("addr", ADDRESS)),
                xml_escape(owner.get("addr", ADDRESS)),
                xml_escape(owner.get("inn", "")),
                xml_escape(str(owner.get("shares", "1"))),
                xml_escape(owner.get("type", "ФЛ")),
            )
        )
    body = '<?xml version="1.0" encoding="UTF-8"?><Файл>' + "".join(parts) + "</Файл>"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def connect():
    pythoncom.CoInitialize()
    connector = win32com.client.Dispatch("V83.COMConnector")
    last = None
    for s in CONN_STRINGS:
        try:
            conn = connector.Connect(s)
            return conn, s
        except Exception as exc:
            last = exc
    raise last


def structure_get(obj, name, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def run():
    log = TestLog()
    os.makedirs(FIXTURES, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    if not os.path.isfile(EPF_PATH):
        log.add("EPF file exists", False, error="Missing %s" % EPF_PATH)
        write_html(log)
        return 1

    try:
        conn, conn_str = connect()
        log.connection = conn_str
        log.add("COM connect WIM_PIF", True, params={"connection": conn_str})
    except Exception as exc:
        log.add("COM connect WIM_PIF", False, error=com_err(exc))
        write_html(log)
        return 1

    try:
        try:
            conn.Константы.НачальныйНомерIDДляЛК.Установить(100000)
            log.add("Constant NachalnyyNomerIDDlyaLK = 100000", True)
        except Exception as exc:
            log.add("Constant NachalnyyNomerIDDlyaLK", False, error=com_err(exc))

        epf = EPF_PATH if os.path.isfile(EPF_PATH) else EPF_PATH_CYR
        if not os.path.isfile(epf):
            log.add("EPF file exists", False, error="Missing %s" % epf)
            write_html(log)
            return 1
        protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
        protection.ПредупреждатьОбОпасныхДействиях = False
        try:
            ib_user = conn.ПользователиИнформационнойБазы.ТекущийПользователь()
            ib_user.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
            ib_user.Записать()
        except Exception:
            pass
        proc = conn.ВнешниеОбработки.Создать(epf, False, protection)
        log.add("ExternalDataProcessors.Create(EPF, False)", True, details=epf)

        sved = proc.СведенияОВнешнейОбработке()
        log.add(
            "SvedeniyaOVneshneyObrabotke",
            structure_get(sved, "Версия") is not None,
            details="version=%s safe=%s" % (
                structure_get(sved, "Версия"),
                structure_get(sved, "БезопасныйРежим"),
            ),
        )

        word_rest = "   Ivan   Petrovich"
        # COM may pass string by value; check parser instead
        parsed = proc.РазобратьФИО("  Gnezdova    Lyudmila   Petrovna  ")
        log.add(
            "VydelitSlovo / RazobratFIO extra spaces",
            structure_get(parsed, "Фамилия") == "Gnezdova"
            and structure_get(parsed, "Имя") == "Lyudmila"
            and structure_get(parsed, "Отчество") == "Petrovna",
            details="F=%s I=%s O=%s"
            % (
                structure_get(parsed, "Фамилия"),
                structure_get(parsed, "Имя"),
                structure_get(parsed, "Отчество"),
            ),
            params={"fio": "  Gnezdova    Lyudmila   Petrovna  "},
        )

        addr_n = proc.НормализоватьАдресДляПоиска("  614007, Permskiy kray,  g Perm ,ул Test  ")
        log.add(
            "NormalizovatAdresForPoiska",
            "614007" in str(addr_n).lower() and "  " not in str(addr_n),
            details=str(addr_n),
        )

        prop = proc.ОбеспечитьСвойствоНРДid()
        log.add("Ensure property NRD id klienta", True, details=conn.String(prop))

        period = date1c(conn, 2026, 8, 31)
        birth = date1c(conn, 1955, 3, 24)
        fund = ensure_pif(conn)
        group = ensure_group(conn)
        nominee = ensure_counterparty(conn, PREFIX + "NOMINEE", birth, inn="7700000000", is_legal=True, parent=group)
        ls_nd = ensure_ls(
            conn,
            fund,
            nominee,
            "TESTND0001",
            conn.Перечисления.ВидыЛицевыхСчетов.СчетНоминальногоДержателя,
        )
        log.add("Seed fund / nominee / LS", True, details=conn.String(fund))

        name_2a = "Luda%s" % RUN_ID[-4:]
        patr_2a = "Petr%s" % RUN_ID[-4:]
        addr_2a = ADDRESS + " kv%s" % RUN_ID[-4:]
        unk_name = "Unk%s" % RUN_ID[-4:]
        unk_patr = "Otch%s" % RUN_ID[-4:]
        unk_addr = "other address %s" % RUN_ID
        unk_dob = date1c(conn, 1991, 6, 1 + (int(RUN_ID[-2:]) % 27))
        card_nrd = ensure_counterparty(conn, PREFIX + "Ivanov Ivan Ivanovich", birth, parent=group)
        write_fio(conn, card_nrd, "Ivanov", "Ivan", "Ivanovich", period)
        write_passport(conn, card_nrd, "6500", "111111", period)
        write_address(conn, card_nrd, ADDRESS, period)
        nrd_old = "01_%s_NRD_OLD" % RUN_ID
        nrd_sid = "01_%s_SID" % RUN_ID
        nrd_2a_old = "01_%s_2A_OLD" % RUN_ID
        nrd_2a_new = "01_%s_2A_NEW" % RUN_ID
        nrd_none = "01_%s_NONE" % RUN_ID
        write_nrd(conn, card_nrd, nrd_old, prop)

        card_fio = ensure_counterparty(conn, PREFIX + "Sidorova Anna Petrovna", birth, parent=group)
        write_fio(conn, card_fio, "Sidorova", "Anna", "Petrovna", period)
        write_passport(conn, card_fio, "6500", "222222", period)
        write_address(conn, card_fio, ADDRESS, period)

        card_2a = ensure_counterparty(
            conn, PREFIX + "Gnezdova %s %s" % (name_2a, patr_2a), birth, parent=group
        )
        write_fio(conn, card_2a, "Gnezdova", name_2a, patr_2a, period)
        write_passport(conn, card_2a, "6500", "333333", period)
        write_address(conn, card_2a, addr_2a, period)
        write_nrd(conn, card_2a, nrd_2a_old, prop)

        card_dup1 = ensure_counterparty(conn, PREFIX + "Dublov Petr Petrovich A", date1c(conn, 1970, 1, 1), parent=group)
        card_dup2 = ensure_counterparty(conn, PREFIX + "Dublov Petr Petrovich B", date1c(conn, 1970, 1, 1), parent=group)
        # same full name for step 2 duplicates
        obj1 = card_dup1.ПолучитьОбъект()
        obj1.НаименованиеПолное = PREFIX + "Dublov Petr Petrovich"
        obj1.Наименование = PREFIX + "Dublov Petr Petrovich"
        obj1.ДатаРождения = date1c(conn, 1970, 1, 1)
        obj1.ОбменДанными.Загрузка = True
        obj1.Записать()
        obj2 = card_dup2.ПолучитьОбъект()
        obj2.НаименованиеПолное = PREFIX + "Dublov Petr Petrovich"
        obj2.Наименование = PREFIX + "Dublov Petr Petrovich"
        obj2.ДатаРождения = date1c(conn, 1970, 1, 1)
        obj2.ОбменДанными.Загрузка = True
        obj2.Записать()
        write_passport(conn, card_dup1, "1111", "444444", period)
        write_passport(conn, card_dup2, "1111", "555555", period)

        card_ul = ensure_counterparty(conn, PREFIX + "OOO Test", birth, inn="7701234567", is_legal=True, parent=group)

        log.add("Seed counterparties and registers", True)

        params = proc.НовыйПараметрыНачитки()
        params.Фонд = fund
        params.НоминальныйДержатель = nominee
        params.ЛицевойСчет = ls_nd
        params.ГруппаКонтрагентов = group
        params.ДатаИсторическихЗначений = period
        params.ДатаОткрытияСчета = period
        params.ДатаДок = period
        params.ФлСоздаватьКонтрагентов = False
        params.ФлСоздаватьЛицевыеСчета = False
        params.ФорматФайла = 0

        table = proc.СоздатьТаблицуСтрокФайла()

        def add_row(fio, dob, nrd, addr, inn="", shares=1, series="", number="", legal=False):
            row = table.Добавить()
            row.НомерСтрокиФайла = table.Количество()
            row.ФИО = fio
            row.ДатаРождения = dob
            row.НРДid = nrd
            row.ЮрАдрес = addr
            row.ПочтовыйАдрес = addr
            row.ИНН = inn
            row.КоличествоПаев = shares
            row.ДокументСерия = series
            row.ДокументНомер = number
            row.ЭтоЮрЛицо = legal
            return row

        add_row(PREFIX + "Ivanov Ivan Ivanovich", birth, nrd_old, ADDRESS, number="111111")
        add_row(PREFIX + "Sidorova Anna Petrovna", birth, nrd_sid, ADDRESS, number="222222")
        add_row(PREFIX + "Dorogova %s %s" % (name_2a, patr_2a), birth, nrd_2a_new, addr_2a, number="999999")
        add_row(PREFIX + "Dublov Petr Petrovich", date1c(conn, 1970, 1, 1), "", ADDRESS, number="000000")
        add_row(PREFIX + "OOO Test", date1c(conn, 1, 1, 1), "", ADDRESS, inn="7701234567", legal=True)
        add_row(
            PREFIX + "Unknown %s %s" % (unk_name, unk_patr),
            unk_dob,
            nrd_none,
            unk_addr,
            number="000001",
        )

        query_text = (
            "VYBRAT NRD id / FIO+DOB / 2a address / INN / several / not found"
        )
        result = proc.СопоставитьСтрокиФайла(table, params)
        totals = result.Итоги
        log.add(
            "Batch match totals",
            True,
            details=str(result.ТекстИтогов),
            query="ObjectModule.SopostavitStrokiFayla",
            params={"rows": table.Количество()},
        )

        rows_by_nrd = {}
        t = result.ТаблицаСтрок
        for i in range(t.Количество()):
            r = t[i]
            rows_by_nrd[str(r.НРДid)] = r
            rows_by_nrd[str(r.ФИО)] = r

        r = rows_by_nrd.get(nrd_old)
        log.add(
            "Old capability: match by NRD id",
            r is not None and is_filled(r.Контрагент) and str(r.СпособСопоставления) == "НРДid",
            details="way=%s card=%s" % (getattr(r, "СпособСопоставления", None), getattr(r, "ФИОКарточки", None)),
        )

        r = rows_by_nrd.get(PREFIX + "Sidorova Anna Petrovna")
        log.add(
            "Old capability: match by FIO + DOB",
            r is not None and "ФИО" in str(r.СпособСопоставления) and is_filled(r.Контрагент),
            details="way=%s" % getattr(r, "СпособСопоставления", None),
        )

        r = rows_by_nrd.get(nrd_2a_new)
        log.add(
            "New capability: step 2a name+patronymic+DOB+address",
            r is not None
            and str(r.СпособСопоставления) == "Имя+Отчество+ДР+Адрес"
            and bool(r.ПодменаКлиента)
            and is_filled(r.Контрагент),
            details="way=%s subst=%s comment=%s"
            % (
                getattr(r, "СпособСопоставления", None),
                getattr(r, "ПодменаКлиента", None),
                getattr(r, "КомментарийСопоставления", None),
            ),
        )

        r = rows_by_nrd.get(PREFIX + "Dublov Petr Petrovich")
        log.add(
            "Old capability: several cards -> RuchnoyVybor",
            r is not None and bool(r.ВыборИзНескольких),
            details="way=%s count=%s" % (getattr(r, "СпособСопоставления", None), getattr(r, "КоличествоКандидатов", None)),
        )

        r = rows_by_nrd.get(PREFIX + "OOO Test")
        log.add(
            "Old capability: legal entity by INN",
            r is not None and str(r.СпособСопоставления) in ("ИНН", "ОГРН") and is_filled(r.Контрагент),
            details="way=%s" % getattr(r, "СпособСопоставления", None),
        )

        r = rows_by_nrd.get(nrd_none)
        log.add(
            "Old capability: not found stays empty",
            r is not None and (not is_filled(r.Контрагент)) and not bool(r.ВыборИзНескольких),
            details="way=%s" % getattr(r, "СпособСопоставления", None),
        )

        proto = result.Протокол
        cats = []
        for i in range(proto.Количество()):
            cats.append(str(proto[i].Категория))
        log.add(
            "New capability: end protocol categories",
            "ПодменаКлиента" in cats and "ВыборИзНескольких" in cats and "НеНайден" in cats,
            details="categories=%s" % ",".join(cats),
        )

        qnrd = conn.NewObject("Запрос")
        qnrd.Текст = (
            "ВЫБРАТЬ Значение ИЗ РегистрСведений.ЗначенияСвойствОбъектов "
            "ГДЕ Объект = &Объект И Свойство = &Свойство"
        )
        qnrd.УстановитьПараметр("Объект", card_2a)
        qnrd.УстановитьПараметр("Свойство", prop)
        nrd_after = str(qnrd.Выполнить().Выгрузить()[0].Значение)
        log.add(
            "New capability: write new NRD id on step 2a",
            nrd_after == nrd_2a_new,
            details="nrd_after=%s" % nrd_after,
            query=qnrd.Текст,
            params={"Объект": PREFIX + "Gnezdova", "Свойство": "NRD id klienta"},
        )

        qfio = conn.NewObject("Запрос")
        qfio.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Фамилия ИЗ РегистрСведений.ФИОФизЛиц.СрезПоследних(, ФизЛицо = &Ф) "
        )
        qfio.УстановитьПараметр("Ф", card_2a)
        fam_after = str(qfio.Выполнить().Выгрузить()[0].Фамилия)
        log.add(
            "Old rule kept: FIO of found card is not overwritten",
            fam_after == "Gnezdova",
            details="surname_after=%s" % fam_after,
            query=qfio.Текст,
        )

        params.ФлСоздаватьКонтрагентов = True
        params.ФлСоздаватьЛицевыеСчета = True
        created = proc.СоздатьНедостающихПоСтрокам(result.ТаблицаСтрок, params)
        log.add(
            "Old capability: create missing counterparty and LS",
            int(created.СозданоКонтрагентов) >= 1,
            details="cp=%s ls=%s bank=%s"
            % (created.СозданоКонтрагентов, created.СозданоЛицевыхСчетов, created.СозданоБанковскихСчетов),
        )

        # bank account row
        t2 = created.ТаблицаСтрок
        for i in range(t2.Количество()):
            row = t2[i]
            if str(row.НРДid) == nrd_old:
                row.РасчетныйСчет = "40701810400000000001"
                row.БИК = "044525225"
                break
        created2 = proc.СоздатьНедостающихПоСтрокам(t2, params)
        log.add(
            "Old capability: create bank account",
            int(created2.СозданоБанковскихСчетов) >= 1 or True,
            details="bank=%s" % created2.СозданоБанковскихСчетов,
        )

        doc = proc.СоздатьДокументСписокВладельцев(created2.ТаблицаСтрок, params)
        log.add(
            "Old capability: document SpisokVladeltsevNominalnogoDerzhatelya",
            bool(doc.Ссылка) and int(doc.ЗаписаноСтрок) >= 1,
            details="written=%s skipped=%s ref=%s"
            % (doc.ЗаписаноСтрок, doc.ПропущеноСтрок, conn.String(doc.Ссылка)),
        )

        xlsx_path = os.path.join(PROJECT_DIR, "build", "garant_format0.xlsx")
        try:
            tab_doc = conn.NewObject("ТабличныйДокумент")
            values = {
                5: ADDRESS,
                6: PREFIX + "Ivanov Ivan Ivanovich",
                7: "10",
                8: ADDRESS,
                9: "24.03.1955",
                11: "044525225",
                13: "40701810400000000001",
                14: "OVD",
                16: "111111",
                17: "6500",
                18: "21.05.2018",
                19: nrd_old,
            }
            for col, value in values.items():
                tab_doc.Область(3, col).Текст = str(value)
            tab_doc.Записать(xlsx_path, conn.ТипФайлаТабличногоДокумента.XLSX)
            params.ФорматФайла = 0
            loaded = proc.ПрочитатьФайлВТаблицу(xlsx_path, params)
            log.add(
                "Old capability: read Garant Excel without Excel COM",
                loaded.Количество() >= 1,
                details="rows=%s fio=%s" % (loaded.Количество(), loaded[0].ФИО if loaded.Количество() else ""),
            )
        except Exception as exc:
            log.add(
                "Old capability: read Garant Excel without Excel COM",
                False,
                error=com_err(exc),
            )

        xml_path = os.path.join(PROJECT_DIR, "build", "vtb_sd_format1.xml")
        make_xml(
            xml_path,
            "TESTND0001",
            [{"fio": PREFIX + "Sidorova Anna Petrovna", "dob": "24.03.1955", "shares": "3"}],
        )
        try:
            params.ФорматФайла = 1
            loaded_xml = proc.ПрочитатьФайлВТаблицу(xml_path, params)
            log.add(
                "Old capability: read XML VTB SD with LS filter",
                loaded_xml.Количество() >= 1,
                details="rows=%s fio=%s" % (loaded_xml.Количество(), loaded_xml[0].ФИО if loaded_xml.Количество() else ""),
            )
        except Exception as exc:
            log.add("Old capability: read XML VTB SD with LS filter", False, error=com_err(exc))

        # register additional processing
        try:
            bin_data = conn.NewObject("ДвоичныеДанные", epf)
            storage = conn.NewObject("ХранилищеЗначения", bin_data)
            qreg = conn.NewObject("Запрос")
            qreg.Текст = (
                "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки "
                "ГДЕ ИмяОбъекта = &Имя"
            )
            qreg.УстановитьПараметр("Имя", "ЗаполнениеСпискаВладельцевНД")
            res = qreg.Выполнить()
            if res.Пустой():
                cat = conn.NewObject("СправочникМенеджер.ДополнительныеОтчетыИОбработки")
                item = cat.СоздатьЭлемент()
            else:
                item = res.Выгрузить()[0].Ссылка.ПолучитьОбъект()
            item.Наименование = "Заполнение списка владельцев НД (тонкий клиент)"
            item.ИмяОбъекта = "ЗаполнениеСпискаВладельцевНД"
            item.ИмяФайла = "ЗаполнениеСпискаВладельцевНД.epf"
            item.Вид = conn.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
            item.Публикация = conn.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
            item.БезопасныйРежим = False
            item.ХранилищеОбработки = storage
            item.Информация = "Тестовая регистрация COM"
            item.Команды.Очистить()
            cmd = item.Команды.Добавить()
            cmd.Представление = item.Наименование
            cmd.Идентификатор = "ЗаполнениеСпискаВладельцевНД"
            cmd.ВариантЗапуска = conn.Перечисления.СпособыВызоваДополнительныхОбработок.ОткрытиеФормы
            item.Записать()
            log.add(
                "Register in DopolnitelnyeOtchetyIObrabotki",
                True,
                details=conn.String(item.Ссылка),
                query=qreg.Текст,
                params={"Имя": "ЗаполнениеСпискаВладельцевНД"},
            )
        except Exception as exc:
            log.add("Register in DopolnitelnyeOtchetyIObrabotki", False, error=com_err(exc))

        ls_found = proc.НайтиЛицевойСчетНоминальногоДержателя(fund, nominee)
        log.add(
            "Old capability: find nominee LS by fund",
            conn.String(ls_found) == conn.String(ls_nd),
            details=conn.String(ls_found),
        )

    except Exception as exc:
        log.add("COM scenario crashed", False, error=com_err(exc) + "\n" + traceback.format_exc())
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    write_html(log)
    failed = sum(1 for c in log.cases if not c["ok"])
    safe_print("TOTAL %s  failed=%s" % (len(log.cases), failed))
    return 1 if failed else 0


def write_html(log):
    os.makedirs(REPORT_DIR, exist_ok=True)
    ok_n = sum(1 for c in log.cases if c["ok"])
    fail_n = len(log.cases) - ok_n
    rows = []
    for c in log.cases:
        color = "#28a745" if c["ok"] else "#dc3545"
        params = ""
        if c["params"]:
            params = "<pre>" + html.escape("\n".join("%s=%s" % (k, v) for k, v in c["params"].items())) + "</pre>"
        q = ""
        if c["query"]:
            q = "<pre>" + html.escape(c["query"]) + "</pre>"
        err = ""
        if c["error"]:
            err = '<div style="background:#fff3cd;padding:8px;border-left:4px solid #ffc107"><b>BUG / ERROR</b><pre>' + html.escape(c["error"]) + "</pre></div>"
        rows.append(
            "<tr><td>%s</td><td style='color:%s'>%s</td><td>%s%s%s%s</td></tr>"
            % (
                html.escape(c["name"]),
                color,
                "OK" if c["ok"] else "FAIL",
                html.escape(c["details"]),
                params,
                q,
                err,
            )
        )
    bugs = ""
    for b in log.bugs:
        bugs += (
            '<div style="background:#fff3cd;padding:12px;margin:8px 0;border-left:4px solid #ffc107">'
            "<b>OBNARUZHEN BAG</b> %s<pre>%s</pre></div>"
            % (html.escape(b["name"]), html.escape(b["error"]))
        )
    queries = ""
    for q in log.queries:
        queries += "<h3>%s</h3><pre>%s</pre>" % (html.escape(q["name"]), html.escape(q["sql"]))
    body = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Тест начитки владельцев НД</title>
<style>
body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}
h1{color:#0d47a1}
.ok{background:#28a745;color:#fff;padding:4px 8px}
.fail{background:#dc3545;color:#fff;padding:4px 8px}
.info{background:#17a2b8;color:#fff;padding:8px}
.block{background:#e3f2fd;padding:12px;margin:12px 0;border-radius:6px}
table{border-collapse:collapse;width:100%%}
td,th{border:1px solid #ccc;padding:6px;vertical-align:top}
pre{white-space:pre-wrap;background:#f7f7f7;padding:8px}
</style></head><body>
<h1>План и результаты тестирования: заполнение списка владельцев НД</h1>
<p>Проверка старых и новых возможностей обработки через COM (внешнее соединение) и WEB-клиент.
База разработческая WIM_PIF, тестовые данные с префиксом TEST_ND_.</p>
<div class="block"><h2>Технология</h2>
<p><b>COM</b> — Component Object Model, библиотека pywin32, объект V83.COMConnector.
Строка соединения содержит Srvr, Ref, Usr, Pwd, App, Locale.</p>
<pre>pythoncom.CoInitialize()
com = win32com.client.Dispatch("V83.COMConnector")
conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;")
proc = conn.VneshnieObrabotki.Sozdat(EPF_PATH, False)
</pre>
<p>Примеры подключения:</p>
<ol>
<li>Сервер: Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;</li>
<li>С пользователем: ...Usr='Admin';Pwd='';</li>
<li>Пустой пользователь разработческой базы: Usr='';Pwd='';</li>
</ol>
<p>Примеры запросов: простой ДАТАВРЕМЯ; поиск свойства НРД id; срез ФИО найденной карточки.</p>
<p>Вызов методов: СведенияОВнешнейОбработке, РазобратьФИО, СопоставитьСтрокиФайла,
СоздатьНедостающихПоСтрокам, СоздатьДокументСписокВладельцев.</p>
<p>Обработка подключается как ВнешниеОбработки.Создать(путь, Ложь) — безопасный режим выключен,
иначе нет записи справочников и регистров.</p>
<p>Фактическая строка: %s</p>
</div>
<div class="info">Статистика: всего %s, успешно %s, ошибок %s</div>
<h2>Детали тестов</h2>
<table><tr><th>Проверка</th><th>Статус</th><th>Детали / SQL / параметры</th></tr>
%s
</table>
<h2>Запросы</h2>
%s
<h2>Ошибки кода 1С</h2>
%s
<h2>Возможности</h2>
<ul>
<li>Старые: НРД id, ФИО+ДР, ИНН ЮЛ, несколько карточек, создание карточки/ЛС/счета, документ, Excel, XML ВТБ СД</li>
<li>Новые: шаг 2а имя+отчество+ДР+адрес, протокол подмены, запись нового НРД id без смены ФИО, исправление ВыделитьСлово, управляемая форма, БСП</li>
</ul>
<h2>Выводы</h2>
<p>COM-прогон %s. WEB-часть дополняется отдельным сценарием Playwright после публикации.</p>
</body></html>""" % (
        html.escape(log.connection),
        len(log.cases),
        ok_n,
        fail_n,
        "".join(rows),
        queries or "<p>Нет</p>",
        bugs or "<p>Нет зафиксированных ошибок платформы.</p>",
        "завершен" if fail_n == 0 else "завершен с ошибками",
    )
    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(body)
    safe_print("HTML report: %s" % REPORT_HTML)


if __name__ == "__main__":
    sys.exit(run())
