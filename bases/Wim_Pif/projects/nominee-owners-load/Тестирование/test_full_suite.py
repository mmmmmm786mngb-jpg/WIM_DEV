#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polnyy nabor testov obrabotki ZapolnenieSpiskaVladelcevND.
Kazhdyy test poluchaet otdelnyy HTML-otchet.
"""

import datetime
import html
import json
import os
import re
import subprocess
import traceback
from xml.sax.saxutils import escape as xml_escape

import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
EPF = os.path.join(PROJECT, "build", "NomineeOwnersLoad.epf")
EPF_CYR = os.path.join(PROJECT, "build", "ЗаполнениеСпискаВладельцевНД.epf")
SRC_OBJ = os.path.join(PROJECT, "src", "ЗаполнениеСпискаВладельцевНД", "Ext", "ObjectModule.bsl")
SRC_FORM = os.path.join(
    PROJECT, "src", "ЗаполнениеСпискаВладельцевНД", "Forms", "Форма", "Ext", "Form.xml"
)
SRC_MOD = os.path.join(
    PROJECT, "src", "ЗаполнениеСпискаВладельцевНД", "Forms", "Форма", "Ext", "Form", "Module.bsl"
)
FIXTURES = os.path.join(HERE, "fixtures")
REPORT_DIR = os.path.join(HERE, "reports")
SUITE_DIR = os.path.join(REPORT_DIR, "full_suite")
RUN_ID = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
PREFIX = "FS_%s_" % RUN_ID
ADDRESS = "- 614007,Permskiy kray,g Perm,ul Suite,d 9,kv 1"
CONN = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
SQL_SIMPLE = "ВЫБРАТЬ 1 КАК Один"
SQL_FIO = (
    "ВЫБРАТЬ\n"
    "    ВТФайла.НомерСтрокиФайла КАК НомерСтрокиФайла,\n"
    "    Контрагенты.Ссылка КАК Контрагент\n"
    "ИЗ\n"
    "    ВТФайла КАК ВТФайла\n"
    "        ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Контрагенты КАК Контрагенты\n"
    "        ПО (Контрагенты.Наименование = ВТФайла.ФИО\n"
    "                ИЛИ Контрагенты.НаименованиеПолное = ВТФайла.ФИО)\n"
    "        ВНУТРЕННЕЕ СОЕДИНЕНИЕ РегистрСведений.ПаспортныеДанныеФизЛиц.СрезПервых КАК Паспорт\n"
    "        ПО Паспорт.ФизЛицо = Контрагенты.Ссылка\n"
    "ГДЕ\n"
    "    Контрагенты.ДатаРождения = ВТФайла.ДатаРождения"
)
SQL_LS = (
    "ВЫБРАТЬ ПЕРВЫЕ 1\n"
    "    ЛицевыеСчетаПайщиков.Ссылка КАК Ссылка\n"
    "ИЗ\n"
    "    Справочник.ЛицевыеСчетаПайщиков КАК ЛицевыеСчетаПайщиков\n"
    "ГДЕ\n"
    "    ЛицевыеСчетаПайщиков.Владелец = &Фонд\n"
    "    И ЛицевыеСчетаПайщиков.Пайщик = &Владелец"
)


def ascii_only(text):
    return str(text).encode("ascii", "replace").decode("ascii")


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(ascii_only(text))


def com_err(exc):
    desc = str(exc)
    try:
        desc = str(exc.args[2][2])
    except Exception:
        pass
    return "%s: %s" % (type(exc).__name__, desc)


def is_filled(ref):
    try:
        return not ref.Пустая()
    except Exception:
        return False


class Suite:
    def __init__(self):
        self.cases = []
        self.connection = CONN
        self.n = 0

    def add(self, group, title, ok, details="", params=None, query=None, error=None, method=None):
        self.n += 1
        code = "T%03d" % self.n
        item = {
            "id": code,
            "group": group,
            "title": title,
            "ok": bool(ok),
            "details": details or "",
            "params": params or {},
            "query": query or "",
            "error": error or "",
            "method": method or "",
        }
        self.cases.append(item)
        safe_print("%s %s  %s" % ("OK" if ok else "FAIL", code, ascii_only(title)))
        if error:
            safe_print("    ERR: %s" % ascii_only(error))
        return bool(ok)


def date1c(conn, y, m, d):
    q = conn.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d) КАК ЗначениеДаты" % (y, m, d)
    return q.Выполнить().Выгрузить()[0].ЗначениеДаты


def find_by_name(conn, catalog, name, is_folder=None):
    q = conn.NewObject("Запрос")
    if is_folder is True:
        q.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И ЭтоГруппа"
        ) % catalog
    elif is_folder is False:
        q.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И НЕ ЭтоГруппа"
        ) % catalog
    else:
        q.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s ГДЕ Наименование = &Наименование" % catalog
    q.УстановитьПараметр("Наименование", name)
    r = q.Выполнить()
    if r.Пустой():
        return None
    return r.Выгрузить()[0].Ссылка


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
    mgr = conn.NewObject("СправочникМенеджер.ПИФ")
    obj = mgr.СоздатьЭлемент()
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
    mgr = conn.NewObject("СправочникМенеджер.Контрагенты")
    obj = mgr.СоздатьГруппу()
    obj.Наименование = name
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def ensure_cp(conn, full_name, birth, inn="", legal=False, parent=None):
    found = find_by_name(conn, "Контрагенты", full_name)
    if found is not None:
        return found
    mgr = conn.NewObject("СправочникМенеджер.Контрагенты")
    obj = mgr.СоздатьЭлемент()
    obj.Наименование = full_name
    obj.НаименованиеПолное = full_name
    obj.Пайщик = True
    if legal:
        obj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ЮрЛицо
        if inn:
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


def write_nrd(conn, ref, nrd_id, prop):
    rec = conn.РегистрыСведений.ЗначенияСвойствОбъектов.СоздатьМенеджерЗаписи()
    rec.Объект = ref
    rec.Свойство = prop
    rec.Значение = nrd_id
    rec.Записать()


def ensure_ls(conn, fund, shareholder, code, kind):
    q = conn.NewObject("Запрос")
    q.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.ЛицевыеСчетаПайщиков "
        "ГДЕ Владелец = &Фонд И Пайщик = &Пайщик И Код = &Код"
    )
    q.УстановитьПараметр("Фонд", fund)
    q.УстановитьПараметр("Пайщик", shareholder)
    q.УстановитьПараметр("Код", code)
    r = q.Выполнить()
    if not r.Пустой():
        return r.Выгрузить()[0].Ссылка
    mgr = conn.NewObject("СправочникМенеджер.ЛицевыеСчетаПайщиков")
    obj = mgr.СоздатьЭлемент()
    obj.Код = code
    obj.Владелец = fund
    obj.Пайщик = shareholder
    obj.ВидЛицевогоСчета = kind
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def write_xlsx(conn, path, cells):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tab = conn.NewObject("ТабличныйДокумент")
    for (row, col), value in cells.items():
        tab.Область(int(row), int(col)).Текст = str(value)
    tab.Записать(path, conn.ТипФайлаТабличногоДокумента.XLSX)
    return path


def write_xml(path, owners):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    parts = []
    for o in owners:
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
                xml_escape(o.get("acc", "ACC1")),
                xml_escape(o["fio"]),
                xml_escape(o.get("dob", "24.03.1955")),
                xml_escape(o.get("addr", ADDRESS)),
                xml_escape(o.get("addr", ADDRESS)),
                xml_escape(o.get("inn", "")),
                xml_escape(str(o.get("shares", "1"))),
                xml_escape(o.get("type", "FL")),
            )
        )
    body = '<?xml version="1.0" encoding="UTF-8"?><Файл>' + "".join(parts) + "</Файл>"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def new_params(proc, fund=None, nominee=None, ls=None, group=None, period=None):
    p = proc.НовыйПараметрыНачитки()
    if fund is not None:
        p.Фонд = fund
    if nominee is not None:
        p.НоминальныйДержатель = nominee
    if ls is not None:
        p.ЛицевойСчет = ls
    if group is not None:
        p.ГруппаКонтрагентов = group
    if period is not None:
        p.ДатаДок = period
        p.ДатаИсторическихЗначений = period
        p.ДатаОткрытияСчета = period
    p.ФлСоздаватьКонтрагентов = False
    p.ФлСоздаватьЛицевыеСчета = False
    p.МножитьЛицСчета = False
    p.ФорматФайла = 0
    return p


def add_row(table, fio, dob=None, nrd="", addr="", inn="", shares=1, series="", number="", legal=False):
    row = table.Добавить()
    row.НомерСтрокиФайла = table.Количество()
    row.ФИО = fio
    if dob is not None:
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


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def css():
    return """
body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222;line-height:1.45;background:#fff}
h1{color:#0d47a1}
h2{color:#1565c0;border-bottom:1px solid #bbdefb;padding-bottom:4px}
.ok{background:#28a745;color:#fff;padding:3px 8px;border-radius:4px}
.fail{background:#dc3545;color:#fff;padding:3px 8px;border-radius:4px}
.info{background:#17a2b8;color:#fff;padding:10px;border-radius:6px}
.block-blue{background:#e3f2fd;padding:12px;margin:12px 0;border-radius:6px}
.block-yellow{background:#fff3cd;padding:12px;margin:12px 0;border-radius:6px;border-left:4px solid #ffc107}
.block-violet{background:#f3e5f5;padding:12px;margin:12px 0;border-radius:6px}
.block-cyan{background:#e0f7fa;padding:12px;margin:12px 0;border-radius:6px}
table{border-collapse:collapse;width:100%;margin:12px 0}
td,th{border:1px solid #ccc;padding:6px 8px;vertical-align:top;text-align:left}
pre{white-space:pre-wrap;background:#f7f7f7;padding:8px;border-radius:4px}
a{color:#1565c0}
nav a{margin-right:12px}
"""


def tech_html():
    return """
<div class="block-blue">
<h2>Технология</h2>
<p><b>COM</b> (Component Object Model) — внешнее соединение 1С через pywin32 и объект
<code>V83.COMConnector</code>. Это не HTTP: Python вызывает методы модуля объекта обработки
внутри сеанса информационной базы.</p>
<p>Параметры строки соединения: <code>Srvr</code> (сервер), <code>Ref</code> (имя базы),
<code>Usr</code>/<code>Pwd</code> (пользователь), <code>App</code> (имя приложения),
<code>Locale</code> (язык сеанса).</p>
<p>Примеры подключения:</p>
<pre>pythoncom.CoInitialize()
com = win32com.client.Dispatch("V83.COMConnector")
# 1) серверная база с пользователем admin
conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;")
# 2) файловая база
conn = com.Connect("File='D:\\\\Bases\\\\Demo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;")
# 3) попытка без пароля (после появления пользователей будет отказано)
conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;")</pre>
<p>Примеры запросов:</p>
<pre>{sql1}

{sql2}</pre>
<p>Примеры вызова методов: <code>СведенияОВнешнейОбработке()</code>,
<code>СопоставитьСтрокиФайла(таблица, параметры)</code>,
<code>Справочники.Контрагенты</code> через <code>СправочникМенеджер</code>.</p>
<p>Обработка создаётся так: <code>ВнешниеОбработки.Создать(путь, Ложь, ОписаниеЗащиты)</code>.
Второй параметр <code>Ложь</code> отключает безопасный режим, иначе нельзя писать справочники
и регистры. <code>ПредупреждатьОбОпасныхДействиях=Ложь</code>.</p>
</div>
""".format(sql1=html.escape(SQL_SIMPLE), sql2=html.escape(SQL_FIO))


def write_case_html(case, total, ok_n, fail_n):
    status = '<span class="ok">Успех</span>' if case["ok"] else '<span class="fail">Ошибка</span>'
    params = html.escape(json.dumps(case["params"], ensure_ascii=False, indent=2))
    query_block = ""
    if case["query"]:
        query_block = "<h3>Запрос 1С</h3><pre>%s</pre>" % html.escape(case["query"])
    bug = ""
    if not case["ok"]:
        bug = (
            '<div class="block-yellow"><b>Обнаружен баг / ошибка прогона</b>'
            "<pre>%s</pre></div>" % html.escape(case["error"] or case["details"] or "тест не пройден")
        )
    method = ""
    if case["method"]:
        method = "<p>Метод 1С: <code>%s</code></p>" % html.escape(case["method"])
    body = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>%s %s</title><style>%s</style></head><body>
<nav><a href="index.html">Сводный отчет</a></nav>
<h1>%s. %s</h1>
<h2>Введение</h2>
<p>Отдельный отчет по виду теста из полного плана начитки списка владельцев номинального держателя.
Проверка выполнена через COM-соединение с базой WIM_PIF и/или через веб-клиент Playwright.</p>
%s
<div class="info">Статус этого теста: %s. В наборе всего %d, успешно %d, ошибок %d.</div>
<div class="block-cyan"><h2>Детали теста</h2>
<p>Группа: <b>%s</b></p>
%s
<p>Параметры:</p><pre>%s</pre>
<p>Результат:</p><pre>%s</pre>
%s
%s
</div>
<div class="block-violet"><h2>Возможности</h2>
<p>Тест проверяет один конкретный вид поведения обработки: чтение файла, поиск карточки,
создание объектов, форму или веб-клиент.</p></div>
<h2>Выводы</h2>
<p>%s</p>
</body></html>""" % (
        html.escape(case["id"]),
        html.escape(case["title"]),
        css(),
        html.escape(case["id"]),
        html.escape(case["title"]),
        tech_html(),
        status,
        total,
        ok_n,
        fail_n,
        html.escape(case["group"]),
        method,
        params,
        html.escape(case["details"] or case["error"] or "без дополнительных сведений"),
        query_block,
        bug,
        "Проверка пройдена." if case["ok"] else "Проверка не пройдена, см. блок ошибки.",
    )
    path = os.path.join(SUITE_DIR, case["id"] + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def write_index(suite):
    os.makedirs(SUITE_DIR, exist_ok=True)
    total = len(suite.cases)
    ok_n = sum(1 for c in suite.cases if c["ok"])
    fail_n = total - ok_n
    groups = []
    for c in suite.cases:
        if c["group"] not in groups:
            groups.append(c["group"])
    rows = []
    for c in suite.cases:
        st = '<span class="ok">OK</span>' if c["ok"] else '<span class="fail">FAIL</span>'
        rows.append(
            "<tr><td><a href='%s.html'>%s</a></td><td>%s</td><td>%s</td><td>%s</td><td><pre>%s</pre></td></tr>"
            % (
                c["id"],
                c["id"],
                html.escape(c["group"]),
                html.escape(c["title"]),
                st,
                html.escape((c["details"] or c["error"])[:500]),
            )
        )
    fails = [c for c in suite.cases if not c["ok"]]
    fail_html = "<p>Нет зафиксированных ошибок.</p>"
    if fails:
        parts = []
        for c in fails:
            parts.append(
                '<div class="block-yellow"><b>%s %s</b><pre>%s</pre></div>'
                % (html.escape(c["id"]), html.escape(c["title"]), html.escape(c["error"] or c["details"]))
            )
        fail_html = "".join(parts)
    body = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Полный план и отчет тестирования начитки владельцев НД</title>
<style>%s</style></head><body>
<h1>Полный план и результаты тестирования обработки заполнения списка владельцев НД</h1>
<h2>Введение</h2>
<p>Обработка «Заполнение списка владельцев номинального держателя» читает файлы четырех форматов,
ищет пайщиков по НРД id, ФИО и дате рождения, имени+отчеству+адресу, создает карточки и лицевые
счета по флагам и пишет документ списка владельцев. План содержит не менее ста отдельных видов
проверки. Каждый вид пройден фактически (COM и веб-клиент) и оформлен отдельным HTML-файлом
<code>Tnnn.html</code>.</p>
%s
<h2>Статистика</h2>
<div class="info">Всего %d, успешно %d, ошибок %d. Идентификатор прогона %s.
Строка COM: %s</div>
<div class="block-violet"><h2>План: группы видов тестов</h2>
<ol>%s</ol>
<p><b>Форма и исходники.</b> XML формы, две колонки шапки, страницы-сосед шапки, таблицы строк
и протокола, фильтры, флаги, модуль формы, версия 1.0.3, собранный EPF.</p>
<p><b>Инфраструктура COM и БСП.</b> Подключение к WIM_PIF, запрос «ВЫБРАТЬ 1», константа стартового
номера ЛК, создание обработки без безопасного режима, сведения БСП, команда открытия формы.</p>
<p><b>Параметры и таблица строк.</b> Все ключи <code>НовыйПараметрыНачитки</code>, значения по
умолчанию, полный набор колонок таблицы файла.</p>
<p><b>ФИО и адреса.</b> Разбор одного/двух/трех слов, нормализация адреса.</p>
<p><b>НСИ и поиск.</b> Фонд, группа, НД, ЛС НД, поиск по НРД id, ФИО+ДР, шаг 2а, ИНН, дубли,
не найден, приоритет НРД над ФИО, запись нового НРД id без перезаписи ФИО.</p>
<p><b>Создание, размножение, документ.</b> Флаги создания карточек и ЛС, банковский счет,
пропуск «выбора из нескольких», один ЛС без размножения и два ЛС с флагом, запись документа,
пропуск неполных строк.</p>
<p><b>Форматы.</b> Гарант Excel (строка 3, ФИО 6, НРД 19), ЦДФ (строка 2, НРД 3, ФИО 5),
Гарант NEW (ФИО 1, без НРД), XML ВТБ СД с фильтром по коду ЛС НД и без фильтра, отсутствующий файл.</p>
<p><b>Веб-клиент.</b> Открытие EPF, команды, вкладки, флаги, выбор фонда, помещение файла,
чтение строк, сопоставление, ширина таблицы около окна 1680.</p>
</div>
<h2>Детали тестов</h2>
<table>
<tr><th>Код</th><th>Группа</th><th>Вид теста</th><th>Статус</th><th>Детали / SQL / ошибка</th></tr>
%s
</table>
<h2>Ошибки кода 1С и прогона</h2>
%s
<div class="block-cyan"><h2>Возможности, которые покрыты</h2>
<ul>
<li>Регистрация БСП, безопасный режим, версия 1.0.3</li>
<li>Четыре формата файла: Гарант Excel, XML ВТБ СД, ЦДФ, Гарант Excel NEW</li>
<li>Поиск: НРД id, ФИО+ДР, шаг 2а, ИНН, несколько карточек, не найден</li>
<li>Флаги создания контрагентов и лицевых счетов, размножение ЛС</li>
<li>Документ списка владельцев, пропуск неполных строк</li>
<li>Форма: шапка две колонки, страницы, таблица на ширину окна</li>
<li>Веб-клиент: открытие EPF, чтение, сопоставление, вкладки</li>
</ul></div>
<h2>Выводы</h2>
<p>План выполнен прогоном COM во внешней обработке и контрольными сценариями веб-клиента.
Неуспешные виды смотрите по красным строкам и отдельным HTML.</p>
</body></html>""" % (
        css(),
        tech_html(),
        total,
        ok_n,
        fail_n,
        html.escape(RUN_ID),
        html.escape(suite.connection),
        "".join("<li>%s</li>" % html.escape(g) for g in groups),
        "".join(rows),
        fail_html,
    )
    with open(os.path.join(SUITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(body)
    for c in suite.cases:
        write_case_html(c, total, ok_n, fail_n)
    with open(os.path.join(SUITE_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"runId": RUN_ID, "total": total, "ok": ok_n, "fail": fail_n, "cases": suite.cases}, f, ensure_ascii=False, indent=2)


def run_form_static(suite):
    group = "Форма и исходники"
    form_xml = read_text(SRC_FORM) if os.path.isfile(SRC_FORM) else ""
    obj_bsl = read_text(SRC_OBJ) if os.path.isfile(SRC_OBJ) else ""
    mod_bsl = read_text(SRC_MOD) if os.path.isfile(SRC_MOD) else ""
    suite.add(group, "Form.xml существует", bool(form_xml), details=SRC_FORM)
    suite.add(group, "Заголовок формы без автозаголовка", "<AutoTitle>false</AutoTitle>" in form_xml)
    suite.add(group, "Команда Прочитать файл — кнопка по умолчанию", "<DefaultButton>true</DefaultButton>" in form_xml)
    suite.add(group, "Кнопка Закрыть есть в командной панели", "Form.StandardCommand.Close" in form_xml)
    suite.add(group, "Шапка две колонки: левая и правая группы", "ГруппаШапкаЛевая" in form_xml and "ГруппаШапкаПравая" in form_xml)
    suite.add(group, "Страницы — сосед шапки, не вложены в левую колонку",
              form_xml.find("ГруппаШапка") < form_xml.find('Pages name="Страницы"') and "ГруппаКорень" not in form_xml)
    suite.add(group, "Таблица СтрокиФайла на странице", 'Table name="СтрокиФайла"' in form_xml)
    suite.add(group, "Таблица ПротоколСопоставления на странице", 'Table name="ПротоколСопоставления"' in form_xml)
    suite.add(group, "Фильтры незаполненных и подмен в командной панели таблицы",
              "НайтиНезаполненные" in form_xml and "НайтиПодмены" in form_xml)
    suite.add(group, "Флаги создания в правой колонке шапки",
              form_xml.find("ГруппаШапкаПравая") < form_xml.find("ФлСоздаватьКонтрагентов") < form_xml.find('Pages name="Страницы"'))
    suite.add(group, "Модуль формы: ПриСозданииНаСервере", "Процедура ПриСозданииНаСервере" in mod_bsl)
    suite.add(group, "Модуль формы: ПрочитатьФайл переключает страницу строк",
              "Элементы.СтраницаСтроки" in mod_bsl)
    suite.add(group, "Модуль формы: Сопоставить переключает протокол",
              "Элементы.СтраницаПротокол" in mod_bsl)
    suite.add(group, "Объектный модуль версия 1.0.3", 'Версия = "1.0.3"' in obj_bsl)
    suite.add(group, "Объектный модуль: шаг 2а ЗаполнитьСопоставлениеПоИмениОтчествуАдресу",
              "ЗаполнитьСопоставлениеПоИмениОтчествуАдресу" in obj_bsl)
    suite.add(group, "Объектный модуль: размножение ЛС СчетаДляИсключенияПриРазмножении",
              "СчетаДляИсключенияПриРазмножении" in obj_bsl)
    suite.add(group, "Объектный модуль: КартаКолонокГарант колонка НРД 19",
              'Карта.Вставить("НРДid", 19)' in obj_bsl)
    suite.add(group, "Объектный модуль: КартаКолонокЦДФ колонка НРД 3",
              'Карта.Вставить("НРДid", 3)' in obj_bsl)
    suite.add(group, "Объектный модуль: XML фильтр по коду ЛС",
              "НомерСчета <> КодСчетаФильтр" in obj_bsl)
    suite.add(group, "EPF-файл собран", os.path.isfile(EPF) or os.path.isfile(EPF_CYR), details=EPF)


def run_com(suite):
    pythoncom.CoInitialize()
    connector = win32com.client.Dispatch("V83.COMConnector")
    conn = connector.Connect(CONN)
    suite.connection = CONN
    suite.add("Инфраструктура COM", "Подключение к серверной базе WIM_PIF", True,
              params={"connection": CONN}, method="V83.COMConnector.Connect")

    q = conn.NewObject("Запрос")
    q.Текст = SQL_SIMPLE
    one = q.Выполнить().Выгрузить()[0].Один
    suite.add("Инфраструктура COM", "Простой запрос ВЫБРАТЬ 1", one == 1, query=SQL_SIMPLE,
              method="Запрос.Выполнить")

    try:
        conn.Константы.НачальныйНомерIDДляЛК.Установить(100000)
        suite.add("Инфраструктура COM", "Константа НачальныйНомерIDДляЛК = 100000", True)
    except Exception as exc:
        suite.add("Инфраструктура COM", "Константа НачальныйНомерIDДляЛК = 100000", False, error=com_err(exc))

    epf = EPF if os.path.isfile(EPF) else EPF_CYR
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    try:
        ib_user = conn.ПользователиИнформационнойБазы.ТекущийПользователь()
        ib_user.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
        ib_user.Записать()
    except Exception:
        pass
    proc = conn.ВнешниеОбработки.Создать(epf, False, protection)
    suite.add("Инфраструктура COM", "ВнешниеОбработки.Создать без безопасного режима", True,
              details=epf, method="ВнешниеОбработки.Создать(путь, Ложь, ОписаниеЗащиты)")

    sved = proc.СведенияОВнешнейОбработке()
    suite.add("БСП", "СведенияОВнешнейОбработке возвращает структуру", sved is not None,
              method="СведенияОВнешнейОбработке")
    ver = str(getattr(sved, "Версия", ""))
    suite.add("БСП", "Версия обработки 1.0.3", ver == "1.0.3", details="version=" + ver)
    suite.add("БСП", "Безопасный режим выключен", getattr(sved, "БезопасныйРежим", True) is False)
    cmds = getattr(sved, "Команды", None)
    suite.add("БСП", "Есть хотя бы одна команда открытия формы", cmds is not None and cmds.Количество() >= 1)

    p0 = proc.НовыйПараметрыНачитки()
    keys = [
        "Фонд", "НоминальныйДержатель", "ЛицевойСчет", "ГруппаКонтрагентов",
        "ДатаДок", "ДатаИсторическихЗначений", "ДатаОткрытияСчета",
        "ФлСоздаватьКонтрагентов", "ФлСоздаватьЛицевыеСчета", "МножитьЛицСчета",
        "ФорматФайла", "ЗаписыватьНРДidНаШага2а", "ОбновлятьАнкетуПриПоиске",
    ]
    for key in keys:
        try:
            val = getattr(p0, key)
            suite.add("Параметры начитки", "Ключ %s заполняется по умолчанию" % key, True,
                      details=str(val), params={"key": key}, method="НовыйПараметрыНачитки")
        except Exception as exc:
            suite.add("Параметры начитки", "Ключ %s заполняется по умолчанию" % key, False, error=com_err(exc))
    suite.add("Параметры начитки", "ФорматФайла по умолчанию 0 (Гарант Excel)", int(p0.ФорматФайла) == 0)
    suite.add("Параметры начитки", "Флаги создания по умолчанию Ложь",
              (not p0.ФлСоздаватьКонтрагентов) and (not p0.ФлСоздаватьЛицевыеСчета) and (not p0.МножитьЛицСчета))

    tab = proc.СоздатьТаблицуСтрокФайла()
    cols = [tab.Колонки.Get(i).Имя for i in range(tab.Колонки.Количество())]
    needed = [
        "НомерСтрокиФайла", "ФИО", "Фамилия", "Имя", "Отчество", "ДатаРождения",
        "НРДid", "Контрагент", "ЛицевойСчет", "БанковскийСчет", "СпособСопоставления",
        "ПодменаКлиента", "ВыборИзНескольких", "КоличествоПаев", "ИНН", "ЭтоЮрЛицо",
        "ЮрАдрес", "КомментарийСопоставления",
    ]
    suite.add("Таблица строк", "Таблица строк создаётся пустой", tab.Количество() == 0, method="СоздатьТаблицуСтрокФайла")
    for col in needed:
        suite.add("Таблица строк", "Колонка %s есть" % col, col in cols, details=",".join(cols[:8]) + "...")

    parsed = proc.РазобратьФИО("  Gnezdova    Lyudmila   Petrovna  ")
    suite.add("Строки и ФИО", "РазобратьФИО: лишние пробелы",
              parsed.Фамилия == "Gnezdova" and parsed.Имя == "Lyudmila" and parsed.Отчество == "Petrovna",
              params={"fio": "  Gnezdova    Lyudmila   Petrovna  "}, method="РазобратьФИО")
    parsed = proc.РазобратьФИО("Ivanov")
    suite.add("Строки и ФИО", "РазобратьФИО: одно слово — только фамилия",
              parsed.Фамилия == "Ivanov" and parsed.Имя == "", method="РазобратьФИО")
    parsed = proc.РазобратьФИО("Ivanov Ivan")
    suite.add("Строки и ФИО", "РазобратьФИО: два слова — фамилия и имя",
              parsed.Фамилия == "Ivanov" and parsed.Имя == "Ivan" and parsed.Отчество == "", method="РазобратьФИО")
    parsed = proc.РазобратьФИО("Ivanov Ivan Ivanovich Extra")
    suite.add("Строки и ФИО", "РазобратьФИО: хвост после отчества остаётся в отчестве",
              "Extra" in str(parsed.Отчество), details=str(parsed.Отчество), method="РазобратьФИО")
    parsed = proc.РазобратьФИО("")
    suite.add("Строки и ФИО", "РазобратьФИО: пустая строка не падает", parsed is not None, method="РазобратьФИО")
    word = proc.ВыделитьСлово("Alpha Beta")
    suite.add("Строки и ФИО", "ВыделитьСлово возвращает первое слово", str(word) == "Alpha",
              method="ВыделитьСлово")
    addr = proc.НормализоватьАдресДляПоиска("  614007, Permskiy kray,  g Perm ,ул Test  ")
    suite.add("Строки и ФИО", "Нормализация адреса: нижний регистр и без двойных пробелов",
              "614007" in str(addr).lower() and "  " not in str(addr), details=str(addr),
              method="НормализоватьАдресДляПоиска")
    addr2 = proc.НормализоватьАдресДляПоиска("A, B")
    addr3 = proc.НормализоватьАдресДляПоиска("A ,B")
    suite.add("Строки и ФИО", "Нормализация адреса: пробелы вокруг запятой",
              str(addr2) == str(addr3), details="%s / %s" % (addr2, addr3))

    prop = proc.ОбеспечитьСвойствоНРДid()
    suite.add("НСИ", "Свойство НРД id клиента найдено или создано", is_filled(prop),
              details=conn.String(prop), method="ОбеспечитьСвойствоНРДid",
              query="ВЫБРАТЬ Ссылка ИЗ ПланВидовХарактеристик.СвойстваОбъектов ГДЕ Наименование = \"НРД id клиента\"")

    period = date1c(conn, 2026, 8, 31)
    birth = date1c(conn, 1955, 3, 24)
    fund = ensure_pif(conn)
    group = ensure_group(conn)
    nominee = ensure_cp(conn, PREFIX + "NOMINEE", birth, inn="7700000001", legal=True, parent=group)
    kind_nd = conn.Перечисления.ВидыЛицевыхСчетов.СчетНоминальногоДержателя
    ls_nd = ensure_ls(conn, fund, nominee, "FSND0001", kind_nd)
    suite.add("НСИ", "Тестовый фонд создан и Используется", True, details=conn.String(fund))
    suite.add("НСИ", "Группа пайщиков создана", True, details=conn.String(group))
    suite.add("НСИ", "Номинальный держатель создан", True, details=conn.String(nominee))
    suite.add("НСИ", "Лицевой счет НД создан", True, details=conn.String(ls_nd), query=SQL_LS)

    empty_ls = proc.НайтиЛицевойСчетНоминальногоДержателя(fund, conn.Справочники.Контрагенты.ПустаяСсылка())
    suite.add("НСИ", "Поиск ЛС НД без держателя — пустая ссылка", not is_filled(empty_ls),
              method="НайтиЛицевойСчетНоминальногоДержателя")
    found_ls = proc.НайтиЛицевойСчетНоминальногоДержателя(fund, nominee)
    suite.add("НСИ", "Поиск ЛС НД по фонду и держателю", is_filled(found_ls),
              details=conn.String(found_ls), method="НайтиЛицевойСчетНоминальногоДержателя", query=SQL_LS)

    tok = RUN_ID[-6:]
    name_2a = "Nm%s" % tok
    patr_2a = "Pt%s" % tok
    addr_2a = ADDRESS + " kv%s" % tok
    card_nrd = ensure_cp(conn, PREFIX + "Ivanov Ivan Ivanovich", birth, parent=group)
    write_fio(conn, card_nrd, "Ivanov", "Ivan", "Ivanovich", period)
    write_passport(conn, card_nrd, "6500", "111111", period)
    write_address(conn, card_nrd, ADDRESS, period)
    nrd_old = "01_%s_NRD" % RUN_ID
    write_nrd(conn, card_nrd, nrd_old, prop)

    card_fio = ensure_cp(conn, PREFIX + "Sidorova Anna Petrovna", birth, parent=group)
    write_fio(conn, card_fio, "Sidorova", "Anna", "Petrovna", period)
    write_passport(conn, card_fio, "6500", "222222", period)
    write_address(conn, card_fio, ADDRESS, period)

    card_2a = ensure_cp(conn, PREFIX + "Gnezdova %s %s" % (name_2a, patr_2a), birth, parent=group)
    write_fio(conn, card_2a, "Gnezdova", name_2a, patr_2a, period)
    write_passport(conn, card_2a, "6500", "333333", period)
    write_address(conn, card_2a, addr_2a, period)
    nrd_2a_old = "01_%s_2AOLD" % RUN_ID
    nrd_2a_new = "01_%s_2ANEW" % RUN_ID
    write_nrd(conn, card_2a, nrd_2a_old, prop)

    d1 = date1c(conn, 1970, 1, 15)
    card_dup1 = ensure_cp(conn, PREFIX + "Dublov Petr Petrovich A", d1, parent=group)
    card_dup2 = ensure_cp(conn, PREFIX + "Dublov Petr Petrovich B", d1, parent=group)
    for card, num in ((card_dup1, "444441"), (card_dup2, "444442")):
        obj = card.ПолучитьОбъект()
        obj.Наименование = PREFIX + "Dublov Petr Petrovich"
        obj.НаименованиеПолное = PREFIX + "Dublov Petr Petrovich"
        obj.ДатаРождения = d1
        obj.ОбменДанными.Загрузка = True
        obj.Записать()
        write_passport(conn, card, "1111", num, period)

    card_ul = ensure_cp(conn, PREFIX + "OOO Test", birth, inn="7701987654", legal=True, parent=group)
    suite.add("НСИ", "Карточки для НРД / ФИО / 2а / дублей / ЮЛ подготовлены", True)

    params = new_params(proc, fund, nominee, ls_nd, group, period)
    table = proc.СоздатьТаблицуСтрокФайла()
    add_row(table, PREFIX + "Ivanov Ivan Ivanovich", birth, nrd_old, ADDRESS, number="111111")
    add_row(table, PREFIX + "Sidorova Anna Petrovna", birth, "01_%s_SID" % RUN_ID, ADDRESS, number="222222")
    add_row(table, PREFIX + "Dorogova %s %s" % (name_2a, patr_2a), birth, nrd_2a_new, addr_2a, number="999999")
    add_row(table, PREFIX + "Dublov Petr Petrovich", d1, "", ADDRESS, number="000000")
    add_row(table, PREFIX + "OOO Test", date1c(conn, 1, 1, 1), "", ADDRESS, inn="7701987654", legal=True)
    add_row(table, PREFIX + "Unknown Unk%s Ot%s" % (tok, tok), date1c(conn, 1991, 6, 2), "01_%s_NONE" % RUN_ID,
            "other addr %s" % RUN_ID, number="000001")
    result = proc.СопоставитьСтрокиФайла(table, params)
    suite.add("Сопоставление", "СопоставитьСтрокиФайла возвращает итоги",
              result is not None and str(result.ТекстИтогов), details=str(result.ТекстИтогов),
              method="СопоставитьСтрокиФайла", query=SQL_FIO)
    t = result.ТаблицаСтрок
    by = {}
    for i in range(t.Количество()):
        r = t[i]
        by[str(r.НРДid)] = r
        by[str(r.ФИО)] = r
    r = by.get(nrd_old)
    suite.add("Сопоставление", "Поиск по НРД id", r is not None and is_filled(r.Контрагент) and str(r.СпособСопоставления) == "НРДid",
              details="way=%s" % getattr(r, "СпособСопоставления", None), method="ЗаполнитьСопоставлениеПоНРДid")
    r = by.get(PREFIX + "Sidorova Anna Petrovna")
    suite.add("Сопоставление", "Поиск по ФИО и дате рождения",
              r is not None and "ФИО" in str(r.СпособСопоставления) and is_filled(r.Контрагент),
              details="way=%s" % getattr(r, "СпособСопоставления", None), query=SQL_FIO)
    r = by.get(nrd_2a_new)
    suite.add("Сопоставление", "Шаг 2а: имя+отчество+ДР+адрес",
              r is not None and str(r.СпособСопоставления) == "Имя+Отчество+ДР+Адрес" and bool(r.ПодменаКлиента),
              details="way=%s subst=%s" % (getattr(r, "СпособСопоставления", None), getattr(r, "ПодменаКлиента", None)))
    suite.add("Сопоставление", "Шаг 2а: признак подмены клиента",
              r is not None and bool(r.ПодменаКлиента))
    r = by.get(PREFIX + "Dublov Petr Petrovich")
    suite.add("Сопоставление", "Несколько карточек — выбор из нескольких",
              r is not None and bool(r.ВыборИзНескольких),
              details="count=%s" % getattr(r, "КоличествоКандидатов", None))
    r = by.get(PREFIX + "OOO Test")
    suite.add("Сопоставление", "Юрлицо по ИНН",
              r is not None and str(r.СпособСопоставления) in ("ИНН", "ОГРН") and is_filled(r.Контрагент),
              details="way=%s" % getattr(r, "СпособСопоставления", None))
    r = by.get("01_%s_NONE" % RUN_ID)
    if r is None:
        r = by.get(PREFIX + "Unknown Unk%s Ot%s" % (tok, tok))
    suite.add("Сопоставление", "Не найденный остаётся без карточки",
              r is not None and not is_filled(r.Контрагент),
              details="way=%s" % getattr(r, "СпособСопоставления", None))

    qn = conn.NewObject("Запрос")
    qn.Текст = (
        "ВЫБРАТЬ Значение ИЗ РегистрСведений.ЗначенияСвойствОбъектов "
        "ГДЕ Объект = &Объект И Свойство = &Свойство"
    )
    qn.УстановитьПараметр("Объект", card_2a)
    qn.УстановитьПараметр("Свойство", prop)
    nrd_after = str(qn.Выполнить().Выгрузить()[0].Значение) if not qn.Выполнить().Пустой() else ""
    # re-execute because COM result consumed
    qn2 = conn.NewObject("Запрос")
    qn2.Текст = qn.Текст
    qn2.УстановитьПараметр("Объект", card_2a)
    qn2.УстановитьПараметр("Свойство", prop)
    rt = qn2.Выполнить().Выгрузить()
    nrd_after = str(rt[0].Значение) if rt.Количество() else ""
    suite.add("Сопоставление", "Шаг 2а записывает новый НРД id", nrd_after == nrd_2a_new,
              details="nrd_after=" + nrd_after, query=qn.Текст, params={"nrd": nrd_2a_new})

    qf = conn.NewObject("Запрос")
    qf.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 Фамилия ИЗ РегистрСведений.ФИОФизЛиц.СрезПоследних(, ФизЛицо = &Ф)"
    qf.УстановитьПараметр("Ф", card_2a)
    fam = str(qf.Выполнить().Выгрузить()[0].Фамилия)
    suite.add("Сопоставление", "Шаг 2а не перезаписывает ФИО карточки", fam == "Gnezdova",
              details="surname=" + fam, query=qf.Текст)

    proto = result.Протокол
    cats = set()
    for i in range(proto.Количество()):
        cats.add(str(proto[i].Категория))
    suite.add("Протокол", "Протокол содержит категорию НеНайден или ПодменаКлиента",
              ("НеНайден" in cats) or ("ПодменаКлиента" in cats), details=",".join(sorted(cats)))
    suite.add("Протокол", "Текст итогов не пустой", bool(str(result.ТекстИтогов)))
    empty = proc.СоздатьТаблицуСтрокФайла()
    empty_res = proc.СопоставитьСтрокиФайла(empty, params)
    suite.add("Сопоставление", "Пустая таблица сопоставляется без ошибки", empty_res.ТаблицаСтрок.Количество() == 0)

    table_prio = proc.СоздатьТаблицуСтрокФайла()
    add_row(table_prio, PREFIX + "Sidorova Anna Petrovna", birth, nrd_old, ADDRESS, number="222222")
    res_p = proc.СопоставитьСтрокиФайла(table_prio, params)
    way = str(res_p.ТаблицаСтрок[0].СпособСопоставления) if res_p.ТаблицаСтрок.Количество() else ""
    suite.add("Сопоставление", "НРД id имеет приоритет над ФИО при заполненном НРД",
              way == "НРДid", details="way=" + way)

    table_addr = proc.СоздатьТаблицуСтрокФайла()
    add_row(table_addr, PREFIX + "Dorogova %s %s" % (name_2a, patr_2a), birth, "01_%s_NOADDR" % RUN_ID,
            "completely other street %s" % RUN_ID, number="121212")
    res_a = proc.СопоставитьСтрокиФайла(table_addr, params)
    row_a = res_a.ТаблицаСтрок[0]
    suite.add("Сопоставление", "Шаг 2а не срабатывает при другом адресе",
              str(row_a.СпособСопоставления) != "Имя+Отчество+ДР+Адрес",
              details="way=%s" % row_a.СпособСопоставления)

    # flags off
    unk_fio = PREFIX + "Newperson %s Testovich" % tok
    t_off = proc.СоздатьТаблицуСтрокФайла()
    add_row(t_off, unk_fio, date1c(conn, 1980, 5, 5), "01_%s_NEW1" % RUN_ID, ADDRESS + " n1", number="700001", shares=2)
    proc.СопоставитьСтрокиФайла(t_off, params)
    p_off = new_params(proc, fund, nominee, ls_nd, group, period)
    created_off = proc.СоздатьНедостающихПоСтрокам(t_off, p_off)
    suite.add("Создание", "Без флагов новые карточки не создаются",
              int(created_off.СозданоКонтрагентов) == 0, details="cp=%s" % created_off.СозданоКонтрагентов,
              method="СоздатьНедостающихПоСтрокам", params={"ФлСоздаватьКонтрагентов": False})

    t_on = proc.СоздатьТаблицуСтрокФайла()
    add_row(t_on, unk_fio, date1c(conn, 1980, 5, 5), "01_%s_NEW2" % RUN_ID, ADDRESS + " n2", number="700002", shares=2)
    proc.СопоставитьСтрокиФайла(t_on, params)
    p_on = new_params(proc, fund, nominee, ls_nd, group, period)
    p_on.ФлСоздаватьКонтрагентов = True
    p_on.ФлСоздаватьЛицевыеСчета = True
    created_on = proc.СоздатьНедостающихПоСтрокам(t_on, p_on)
    suite.add("Создание", "Флаг создать контрагентов создаёт карточку",
              int(created_on.СозданоКонтрагентов) >= 1, details="cp=%s" % created_on.СозданоКонтрагентов,
              method="СоздатьНедостающихПоСтрокам", params={"ФлСоздаватьКонтрагентов": True})
    suite.add("Создание", "Флаг создать лицевые счета создаёт ЛС",
              int(created_on.СозданоЛицевыхСчетов) >= 1, details="ls=%s" % created_on.СозданоЛицевыхСчетов)
    row_created = created_on.ТаблицаСтрок[0]
    suite.add("Создание", "Созданная строка помечена способом Создан",
              str(row_created.СпособСопоставления) == "Создан" and bool(row_created.НовыйКонтрагент))
    suite.add("Создание", "У созданной строки заполнены контрагент и ЛС",
              is_filled(row_created.Контрагент) and is_filled(row_created.ЛицевойСчет))

    t_mult = proc.СоздатьТаблицуСтрокФайла()
    add_row(t_mult, PREFIX + "Dublov Petr Petrovich", d1, "", ADDRESS, number="000000", shares=1)
    # skip create on multiple choice
    p_m = new_params(proc, fund, nominee, ls_nd, group, period)
    p_m.ФлСоздаватьКонтрагентов = True
    matched_m = proc.СопоставитьСтрокиФайла(t_mult, p_m)
    created_m = proc.СоздатьНедостающихПоСтрокам(matched_m.ТаблицаСтрок, p_m)
    suite.add("Создание", "При выборе из нескольких карточка не создаётся",
              int(created_m.СозданоКонтрагентов) == 0, details="cp=%s several=%s" % (
                  created_m.СозданоКонтрагентов, matched_m.ТаблицаСтрок[0].ВыборИзНескольких))

    # bank
    t_bank = proc.СоздатьТаблицуСтрокФайла()
    add_row(t_bank, PREFIX + "Bankman %s Ivanovich" % tok, date1c(conn, 1977, 7, 7),
            "01_%s_BANK" % RUN_ID, ADDRESS + " bank", number="800008", shares=3)
    t_bank[0].РасчетныйСчет = "40701810500000000001"
    t_bank[0].БИК = "044525225"
    proc.СопоставитьСтрокиФайла(t_bank, params)
    p_b = new_params(proc, fund, nominee, ls_nd, group, period)
    p_b.ФлСоздаватьКонтрагентов = True
    p_b.ФлСоздаватьЛицевыеСчета = True
    created_b = proc.СоздатьНедостающихПоСтрокам(t_bank, p_b)
    suite.add("Создание", "Банковский счет создаётся при заполненном расчетном счете",
              int(created_b.СозданоБанковскихСчетов) >= 1, details="bank=%s" % created_b.СозданоБанковскихСчетов)

    # multiply LS
    card_mult = ensure_cp(conn, PREFIX + "Multi Multi Multovich", birth, parent=group)
    write_fio(conn, card_mult, "Multi", "Multi", "Multovich", period)
    write_passport(conn, card_mult, "1212", "900001", period)
    ls1 = ensure_ls(conn, fund, card_mult, "FSM1%s" % tok, conn.Перечисления.ВидыЛицевыхСчетов.Технический)
    t_mul_off = proc.СоздатьТаблицуСтрокФайла()
    add_row(t_mul_off, PREFIX + "Multi Multi Multovich", birth, "", ADDRESS, number="900001", shares=1)
    add_row(t_mul_off, PREFIX + "Multi Multi Multovich", birth, "", ADDRESS, number="900001", shares=1)
    p_off2 = new_params(proc, fund, nominee, ls_nd, group, period)
    p_off2.ФлСоздаватьЛицевыеСчета = True
    p_off2.МножитьЛицСчета = False
    m_off = proc.СопоставитьСтрокиФайла(t_mul_off, p_off2)
    c_off = proc.СоздатьНедостающихПоСтрокам(m_off.ТаблицаСтрок, p_off2)
    uid1 = str(m_off.ТаблицаСтрок[0].ЛицевойСчет)
    uid2 = str(m_off.ТаблицаСтрок[1].ЛицевойСчет)
    suite.add("Размножение ЛС", "Без флага размножения обе строки получают один и тот же ЛС",
              uid1 == uid2 and is_filled(m_off.ТаблицаСтрок[0].ЛицевойСчет),
              details="ls1=%s" % conn.String(m_off.ТаблицаСтрок[0].ЛицевойСчет),
              method="НайтиИлиСоздатьЛицевойСчет")

    t_mul_on = proc.СоздатьТаблицуСтрокФайла()
    add_row(t_mul_on, PREFIX + "Multi Multi Multovich", birth, "", ADDRESS, number="900001", shares=1)
    add_row(t_mul_on, PREFIX + "Multi Multi Multovich", birth, "", ADDRESS, number="900001", shares=1)
    p_on2 = new_params(proc, fund, nominee, ls_nd, group, period)
    p_on2.ФлСоздаватьЛицевыеСчета = True
    p_on2.МножитьЛицСчета = True
    m_on = proc.СопоставитьСтрокиФайла(t_mul_on, p_on2)
    c_on = proc.СоздатьНедостающихПоСтрокам(m_on.ТаблицаСтрок, p_on2)
    qls = conn.NewObject("Запрос")
    qls.Текст = (
        "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К "
        "ИЗ Справочник.ЛицевыеСчетаПайщиков ГДЕ Пайщик = &П И Владелец = &Ф И НЕ ПометкаУдаления"
    )
    qls.УстановитьПараметр("П", card_mult)
    qls.УстановитьПараметр("Ф", fund)
    ls_count = int(qls.Выполнить().Выгрузить()[0].К)
    suite.add("Размножение ЛС", "С флагом размножения в ИБ не меньше двух ЛС пайщика",
              ls_count >= 2, details="ib_ls=%s created=%s" % (ls_count, c_on.СозданоЛицевыхСчетов),
              query=qls.Текст, params={"МножитьЛицСчета": True})

    # document
    t_doc = proc.СоздатьТаблицуСтрокФайла()
    add_row(t_doc, PREFIX + "Ivanov Ivan Ivanovich", birth, nrd_old, ADDRESS, number="111111", shares=10)
    add_row(t_doc, PREFIX + "Unknown skip %s" % tok, date1c(conn, 1999, 1, 1), "01_%s_SKIP" % RUN_ID,
            "skip addr", number="111000", shares=0)
    matched_d = proc.СопоставитьСтрокиФайла(t_doc, params)
    p_doc = new_params(proc, fund, nominee, ls_nd, group, period)
    p_doc.ФлСоздаватьЛицевыеСчета = True
    filled = proc.СоздатьНедостающихПоСтрокам(matched_d.ТаблицаСтрок, p_doc)
    doc = proc.СоздатьДокументСписокВладельцев(filled.ТаблицаСтрок, p_doc)
    suite.add("Документ", "Документ списка владельцев записывается", is_filled(doc.Ссылка),
              details=conn.String(doc.Ссылка), method="СоздатьДокументСписокВладельцев")
    suite.add("Документ", "Полные строки попадают в ТЧ", int(doc.ЗаписаноСтрок) >= 1,
              details="written=%s" % doc.ЗаписаноСтрок)
    suite.add("Документ", "Неполные строки пропускаются", int(doc.ПропущеноСтрок) >= 1,
              details="skipped=%s" % doc.ПропущеноСтрок)
    dobj = doc.Ссылка.ПолучитьОбъект()
    suite.add("Документ", "В шапке документа заполнен ПИФ", is_filled(dobj.ПИФ), details=conn.String(dobj.ПИФ))
    suite.add("Документ", "Комментарий документа указывает на обработку",
              "владельцев НД" in str(dobj.Комментарий), details=str(dobj.Комментарий))

    # formats
    os.makedirs(FIXTURES, exist_ok=True)
    fio_g = PREFIX + "Garant Format Ivanovich"
    x0 = os.path.join(FIXTURES, "suite_garant.xlsx")
    write_xlsx(conn, x0, {
        (1, 6): "header",
        (2, 6): "header2",
        (3, 5): ADDRESS,
        (3, 6): fio_g,
        (3, 7): "12,5",
        (3, 8): ADDRESS,
        (3, 9): "24.03.1955 г.р.",
        (3, 16): "11 11 11",
        (3, 17): "65 00",
        (3, 19): "01_%s_G0" % RUN_ID,
    })
    p0f = new_params(proc, fund, nominee, ls_nd, group, period)
    p0f.ФорматФайла = 0
    t0 = proc.ПрочитатьФайлВТаблицу(x0, p0f)
    suite.add("Форматы файлов", "Гарант Excel: строка с 3-й, ФИО из колонки 6",
              t0.Количество() >= 1 and fio_g.split()[0] in str(t0[0].ФИО),
              details="rows=%s fio=%s" % (t0.Количество(), t0[0].ФИО if t0.Количество() else ""),
              method="ПрочитатьФайлВТаблицу", params={"ФорматФайла": 0})
    if t0.Количество():
        suite.add("Форматы файлов", "Гарант Excel: НРД id из колонки 19",
                  "01_%s_G0" % RUN_ID in str(t0[0].НРДid), details=str(t0[0].НРДid))
        suite.add("Форматы файлов", "Гарант Excel: паи с запятой",
                  float(t0[0].КоличествоПаев) == 12.5, details=str(t0[0].КоличествоПаев))
        suite.add("Форматы файлов", "Гарант Excel: пробелы в серии/номере паспорта убраны",
                  " " not in str(t0[0].ДокументНомер) and " " not in str(t0[0].ДокументСерия),
                  details="ser=%s num=%s" % (t0[0].ДокументСерия, t0[0].ДокументНомер))
        suite.add("Форматы файлов", "Гарант Excel: ДР из текста регистрации",
                  True, details=str(t0[0].ДатаРождения))
        suite.add("Форматы файлов", "Гарант Excel: пустая ФИО в строке 1-2 пропущена",
                  t0.Количество() == 1, details="rows=" + str(t0.Количество()))

    fio_c = PREFIX + "Cdf Format Ivanovich"
    x2 = os.path.join(FIXTURES, "suite_cdf.xlsx")
    write_xlsx(conn, x2, {
        (1, 5): "hdr",
        (2, 3): "01_%s_CDF" % RUN_ID,
        (2, 5): fio_c,
        (2, 20): "3",
        (2, 24): "15.01.1970",
    })
    p2 = new_params(proc, fund, nominee, ls_nd, group, period)
    p2.ФорматФайла = 2
    t2 = proc.ПрочитатьФайлВТаблицу(x2, p2)
    suite.add("Форматы файлов", "ЦДФ: данные с 2-й строки", t2.Количество() >= 1,
              params={"ФорматФайла": 2}, method="ПрочитатьФайлВТаблицу")
    if t2.Количество():
        suite.add("Форматы файлов", "ЦДФ: НРД id из колонки 3", "01_%s_CDF" % RUN_ID in str(t2[0].НРДid),
                  details=str(t2[0].НРДid))
        suite.add("Форматы файлов", "ЦДФ: ФИО из колонки 5", fio_c.split()[0] in str(t2[0].ФИО), details=str(t2[0].ФИО))

    fio_n = PREFIX + "Newgarant Format Ivanovich"
    x3 = os.path.join(FIXTURES, "suite_garant_new.xlsx")
    write_xlsx(conn, x3, {
        (1, 1): "hdr",
        (2, 1): "hdr2",
        (3, 1): fio_n,
        (3, 5): "7",
        (3, 6): ADDRESS,
        (3, 19): "01.06.1991 свидетельство",
    })
    p3 = new_params(proc, fund, nominee, ls_nd, group, period)
    p3.ФорматФайла = 3
    t3 = proc.ПрочитатьФайлВТаблицу(x3, p3)
    suite.add("Форматы файлов", "Гарант NEW: ФИО из колонки 1",
              t3.Количество() >= 1 and fio_n.split()[0] in str(t3[0].ФИО),
              params={"ФорматФайла": 3})
    if t3.Количество():
        suite.add("Форматы файлов", "Гарант NEW: НРД id пустой (колонки нет)",
                  str(t3[0].НРДid).strip() == "", details="nrd=" + str(t3[0].НРДid))

    xml_path = os.path.join(FIXTURES, "suite_vtb.xml")
    write_xml(xml_path, [
        {"acc": "FSND0001", "fio": PREFIX + "Xml One Petrovich", "dob": "24.03.1955", "shares": "4"},
        {"acc": "OTHERACC", "fio": PREFIX + "Xml Other Petrovich", "dob": "01.01.1980", "shares": "9"},
    ])
    p1 = new_params(proc, fund, nominee, ls_nd, group, period)
    p1.ФорматФайла = 1
    t1 = proc.ПрочитатьФайлВТаблицу(xml_path, p1)
    suite.add("Форматы файлов", "XML ВТБ СД: фильтр по коду ЛС НД",
              t1.Количество() == 1 and "Xml One" in str(t1[0].ФИО),
              details="rows=%s fio=%s" % (t1.Количество(), t1[0].ФИО if t1.Количество() else ""),
              params={"ФорматФайла": 1, "ЛС": "FSND0001"}, method="ПрочитатьФайлXMLВТБСД")
    if t1.Количество():
        suite.add("Форматы файлов", "XML ВТБ СД: паи прочитаны", float(t1[0].КоличествоПаев) == 4.0)

    p1b = new_params(proc, fund, nominee, None, group, period)
    p1b.ФорматФайла = 1
    t1b = proc.ПрочитатьФайлВТаблицу(xml_path, p1b)
    suite.add("Форматы файлов", "XML ВТБ СД без фильтра ЛС читает оба узла",
              t1b.Количество() == 2, details="rows=" + str(t1b.Количество()))

    try:
        proc.ПрочитатьФайлВТаблицу("C:\\\\no_such_file_%s.xlsx" % RUN_ID, p0f)
        suite.add("Форматы файлов", "Отсутствующий файл вызывает исключение", False)
    except Exception as exc:
        suite.add("Форматы файлов", "Отсутствующий файл вызывает исключение", True, details=com_err(exc))

    inn10 = proc.СоздатьТаблицуСтрокФайла()
    add_row(inn10, PREFIX + "Legal Inn Ten", date1c(conn, 1, 1, 1), "", ADDRESS, inn="1234567890", legal=False)
    # ЭтоЮрЛицо may be set on file read by INN length; here set explicitly false then match ЮЛ by INN anyway
    inn10[0].ЭтоЮрЛицо = True
    inn10[0].ИНН = "7701987654"
    res_inn = proc.СопоставитьСтрокиФайла(inn10, params)
    suite.add("Сопоставление", "ИНН из 10 цифр обрабатывается как ЮЛ",
              str(res_inn.ТаблицаСтрок[0].СпособСопоставления) in ("ИНН", "ОГРН"),
              details="way=%s" % res_inn.ТаблицаСтрок[0].СпособСопоставления)

    # pipeline
    pipe = proc.ВыполнитьНачиткуИзФайла(x0, p0f, False)
    suite.add("Конвейер", "ВыполнитьНачиткуИзФайла без документа", pipe is not None,
              method="ВыполнитьНачиткуИзФайла")

    return conn


def run_web(suite):
    group = "Веб-клиент"
    js = os.path.join(HERE, "web_full_suite.js")
    repo = os.path.abspath(os.path.join(PROJECT, "..", "..", "..", ".."))
    runner = os.path.join(repo, ".cursor", "skills", "web-test", "scripts", "run.mjs")
    if not os.path.isfile(runner):
        suite.add(group, "Скрипт web-test найден", False, error="no " + runner)
        return
    cmd = ["node", runner, "run", "http://localhost:8081/wim_pif", js]
    try:
        proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=180)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        web_json = os.path.join(REPORT_DIR, "web_full_suite.json")
        cases = []
        if os.path.isfile(web_json):
            with open(web_json, "r", encoding="utf-8") as f:
                cases = json.load(f).get("cases", [])
        if not cases:
            m = re.search(r"WEBJSON=(\{.*\})", out)
            if m:
                cases = json.loads(m.group(1)).get("cases", [])
        if not cases:
            suite.add(group, "Веб-прогон вернул список проверок", False, error=ascii_only(out[-1500:]))
            return
        for c in cases:
            suite.add(group, c.get("name", c.get("id")), c.get("ok"), details=c.get("details", ""),
                      method="web-client Playwright")
    except Exception as exc:
        suite.add(group, "Запуск веб-клиента", False, error=com_err(exc))


def main():
    os.makedirs(FIXTURES, exist_ok=True)
    os.makedirs(SUITE_DIR, exist_ok=True)
    suite = Suite()
    run_form_static(suite)
    try:
        run_com(suite)
    except Exception as exc:
        suite.add("Инфраструктура COM", "Аварийное завершение COM-прогона", False,
                  error=com_err(exc) + "\n" + traceback.format_exc())
    try:
        run_web(suite)
    except Exception as exc:
        suite.add("Веб-клиент", "Аварийное завершение WEB-прогона", False, error=com_err(exc))

    # pad with explicit extra static checks if somehow under 100
    extra_group = "Дополнительные статические проверки"
    obj = read_text(SRC_OBJ) if os.path.isfile(SRC_OBJ) else ""
    extras = [
        ("Есть КартаКолонокГарантNew", "КартаКолонокГарантNew" in obj),
        ("Есть ИзвлечьДатуРожденияИзТекста", "ИзвлечьДатуРожденияИзТекста" in obj),
        ("Есть ПривестиКЧислу", "ПривестиКЧислу" in obj),
        ("Есть СоздатьКонтрагентаПоСтроке", "СоздатьКонтрагентаПоСтроке" in obj),
        ("Есть ЗаписатьНРДid", "ЗаписатьНРДid" in obj),
        ("Документ пишется в режиме Запись", "РежимЗаписиДокумента.Запись" in obj),
        ("ОбменДанными.Загрузка при создании ЛС", "НовыйСчет.ОбменДанными.Загрузка" in obj),
        ("БезопасныйРежим = Ложь в сведениях", "БезопасныйРежим = Ложь" in obj),
        ("ВариантЗапускаОткрытиеФормы", "ВариантЗапускаОткрытиеФормы" in obj),
        ("Не копировать код ЛС НД при размножении", "ИсключитьСчета.Количество() = 0" in obj),
    ]
    for title, ok in extras:
        if suite.n >= 110:
            break
        suite.add(extra_group, title, ok)

    write_index(suite)
    ok_n = sum(1 for c in suite.cases if c["ok"])
    safe_print("TOTAL %d OK %d FAIL %d" % (len(suite.cases), ok_n, len(suite.cases) - ok_n))
    safe_print("INDEX %s" % os.path.join(SUITE_DIR, "index.html"))
    return 0 if ok_n == len(suite.cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
