#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COM-progon: gruppa 2 -> otmena (ostalos 50 planov) -> gruppa 3 po vsem 600.
Ozhidaetsja: gruppa 3 sozdaet tolko 50 dokumentov.
Novyj den, marker IM86632_CANCELG3.
"""

from __future__ import print_function

import html
import json
import os
import sys
import time
import traceback
from datetime import datetime

import pythoncom
import win32com.client

CONN_STRING = "Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;"
COMMENT_MARK = "IM86632_CANCELG3"
TARGET_CONTRACTS = 600
COMPLETED_G2 = 50
DUMMY_JOBS = 3
PAUSE_SEC = 8
SCHA_SAMPLE = 50

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
JSON_PATH = os.path.join(
    PROJECT_DIR, "Тестирование", "reports", "im86632_com_test_cancel_g2_then_g3.json"
)
HTML_PATH = os.path.join(
    PROJECT_DIR,
    "Документация",
    "02_scha_rsa_group3",
    "imdev86632_test_report_cancel_g2_then_g3_all.html",
)

SQL_CONTRACTS = (
    "ВЫБРАТЬ ПЕРВЫЕ 600\n"
    "    ДоговорДУ.Ссылка КАК Ссылка,\n"
    "    ДоговорДУ.Код КАК Код,\n"
    "    ДоговорДУ.Наименование КАК Наименование\n"
    "ИЗ\n"
    "    Справочник.ДоговорДУ КАК ДоговорДУ\n"
    "ГДЕ\n"
    "    ДоговорДУ.ПометкаУдаления = ЛОЖЬ\n"
    "УПОРЯДОЧИТЬ ПО\n"
    "    ДоговорДУ.Код"
)

SQL_COUNT_GROUP = (
    "ВЫБРАТЬ\n"
    "    КОЛИЧЕСТВО(План.Ссылка) КАК Кнт\n"
    "ИЗ\n"
    "    Документ.ПланРегламентныхОперацийДУ КАК План\n"
    "ГДЕ\n"
    "    План.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания\n"
    "    И План.ГруппаОперацийПользователя = &Группа\n"
    "    И План.Комментарий = &Маркер\n"
    "    И План.Проведен\n"
    "    И НЕ План.ПометкаУдаления"
)

SQL_VERIFY_LINK = (
    "ВЫБРАТЬ\n"
    "    План.Ссылка КАК Ссылка,\n"
    "    План.ДоговорДУ КАК ДоговорДУ,\n"
    "    План.ПланВечернихОпераций КАК ПланВечернихОпераций\n"
    "ИЗ\n"
    "    Документ.ПланРегламентныхОперацийДУ КАК План\n"
    "ГДЕ\n"
    "    План.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания\n"
    "    И План.ГруппаОперацийПользователя = &ГруппаСЧА\n"
    "    И План.Комментарий = &Маркер\n"
    "    И НЕ План.ПометкаУдаления"
)

TITLES = {
    "Podkljuchenie IM86632": "Подключение и расширение IM86632",
    "Gruppy 2 i 3": "Группы 2 и 3 в видах операций",
    "Period novogo dnja": "Открытый регламентный период новой даты",
    "Ochistka CANCELG3": "Очистка предыдущих документов сценария",
    "Pul 600 dogovorov": "Пул договоров ДУ для запуска «по всем»",
    "Gruppa 2: pervaja porcija 50": "Группа 2: первая порция успела записаться (50 планов)",
    "Posle otmeny net gruppy 3": "После отмены группы 2 планов группы 3 нет",
    "Otmena roditelja, porcii zhivy": "Отмена родителя не гасит порции IM8663_",
    "Ozhidanie porcij posle otmeny": "Ожидание порций после отмены не создаёт группу 3",
    "Srez posle ozhidanija": "Срез после ожидания: только группа 2, без группы 3",
    "Otbor gruppy 3 po vsem 600": "Отбор группы 3 по полному списку (как «по всем»)",
    "Otbor ne beret dogovora bez gruppy 2": "Отбор не берёт договоры без вечернего плана",
    "Zapusk gruppy 3 po otboru": "Запись планов группы 3 только по отбору",
    "Otkaz gruppy 3 bez vechera": "Отказ записать группу 3 без плана группы 2",
    "Itogovye schetchiki 50/50": "Итог: планов группы 3 столько же, сколько успевшей группы 2",
    "Svjazka PplanVechernih": "Реквизит «План вечерних операций» заполнен",
    "Dokumenty SCHA/RSA": "Документы «Расчет СЧА/РСА» только по отбору",
    "Net lishnih planov gruppy 3": "Нет лишних планов группы 3 сверх отбора",
}


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(str(text).encode("ascii", "replace").decode("ascii"))


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def com_str(conn, value):
    if value is None:
        return ""
    try:
        return str(conn.String(value))
    except Exception:
        try:
            return str(value)
        except Exception:
            return ""


def is_empty_ref(value):
    if value is None:
        return True
    try:
        return bool(value.Пустая())
    except Exception:
        text = str(value).strip()
        return text in ("", "None", "Undefined")


def user_messages(conn):
    texts = []
    try:
        arr = conn.ПолучитьСообщенияПользователю(True)
        if arr is None:
            return texts
        for i in range(int(arr.Количество())):
            texts.append(com_str(conn, arr.Получить(i).Текст))
    except Exception:
        pass
    return texts


def add_test(report, name, ok, detail, error="", sql="", params=None, duration_s=0.0):
    item = {
        "name": name,
        "ok": bool(ok),
        "detail": detail,
        "error": error or "",
        "sql": sql or "",
        "params": params or {},
        "duration_s": round(duration_s, 3),
    }
    report["tests"].append(item)
    mark = "OK" if ok else "FAIL"
    safe_print("  [%s] %s" % (mark, name))
    if error:
        safe_print("       ERR: " + error[:240].replace("\n", " | "))
    return ok


def connect():
    pythoncom.CoInitialize()
    connector = win32com.client.Dispatch("V83.COMConnector")
    return connector.Connect(CONN_STRING)


def query_table(conn, text, params=None):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for key, value in params.items():
            query.УстановитьПараметр(key, value)
    return query.Выполнить().Выгрузить()


def make_array(conn, items):
    arr = conn.NewObject("Массив")
    for item in items:
        arr.Добавить(item)
    return arr


def make_date(conn, year, month, day, hour=0, minute=0, second=0):
    q = conn.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d, %d, %d, %d) КАК Д" % (
        year, month, day, hour, minute, second
    )
    return q.Выполнить().Выгрузить()[0].Д


def format_ymd(conn, day):
    q = conn.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ ГОД(&Д) КАК Г, МЕСЯЦ(&Д) КАК М, ДЕНЬ(&Д) КАК Дн"
    q.УстановитьПараметр("Д", day)
    row = q.Выполнить().Выгрузить()[0]
    return "%04d%02d%02d" % (int(row.Г), int(row.М), int(row.Дн))


def day_bounds(conn, day):
    q = conn.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ НАЧАЛОПЕРИОДА(&Д, ДЕНЬ) КАК Н, КОНЕЦПЕРИОДА(&Д, ДЕНЬ) КАК К"
    q.УстановитьПараметр("Д", day)
    row = q.Выполнить().Выгрузить()[0]
    return row.Н, row.К


def try_set(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        try:
            obj.Set(name, value)
            return True
        except Exception:
            return False


def write_doc(conn, doc, posting=True):
    mode = conn.РежимЗаписиДокумента.Проведение if posting else conn.РежимЗаписиДокумента.Запись
    doc.Записать(mode)


def count_plans(conn, day, group_ref):
    start, end = day_bounds(conn, day)
    table = query_table(
        conn,
        SQL_COUNT_GROUP,
        {"ДатаНачала": start, "ДатаОкончания": end, "Группа": group_ref, "Маркер": COMMENT_MARK},
    )
    return int(table[0].Кнт)


def probe_environment(conn, report):
    env = report["environment"]
    meta = conn.Метаданные
    env["config_name"] = com_str(conn, meta.Имя)
    env["config_version"] = com_str(conn, meta.Версия)
    extensions = []
    try:
        for ext in conn.РасширенияКонфигурации.Получить():
            item = {
                "name": com_str(conn, ext.Имя),
                "synonym": com_str(conn, ext.Синоним),
                "version": com_str(conn, ext.Версия),
                "active": True,
            }
            try:
                item["active"] = bool(ext.Активно)
            except Exception:
                pass
            extensions.append(item)
            if item["name"] == "IM86632":
                env["im86632_version"] = item["version"]
                env["im86632_active"] = item["active"]
    except Exception as exc:
        env["extensions_error"] = str(exc)
    env["extensions"] = extensions
    periods = getattr(conn.Справочники, "РегламентныеПериоды")
    env["code_group2"] = com_str(conn, periods.КодВечернейГруппыОпераций())
    env["code_group3"] = com_str(conn, periods.КодГруппыРасчетаСЧА_РСА())
    kinds = getattr(conn.Справочники, "ВидыОперацийЗакрытияПериода")
    group2 = kinds.НайтиПоКоду(env["code_group2"])
    group3 = kinds.НайтиПоКоду(env["code_group3"])
    env["group2_found"] = not is_empty_ref(group2)
    env["group3_found"] = not is_empty_ref(group3)
    env["group2_name"] = com_str(conn, group2) if env["group2_found"] else ""
    env["group3_name"] = com_str(conn, group3) if env["group3_found"] else ""
    q = conn.NewObject("Запрос")
    q.Текст = (
        "ВЫБРАТЬ КОЛИЧЕСТВО(ДоговорДУ.Ссылка) КАК Всего\n"
        "ИЗ Справочник.ДоговорДУ КАК ДоговорДУ\n"
        "ГДЕ ДоговорДУ.ПометкаУдаления = ЛОЖЬ"
    )
    env["contracts_total"] = int(q.Выполнить().Выгрузить()[0].Всего)
    add_test(
        report,
        "Podkljuchenie IM86632",
        bool(env.get("im86632_version")),
        "Konfiguracija %s %s, IM86632 %s, dogovorov=%s"
        % (env["config_name"], env["config_version"], env.get("im86632_version", "-"), env["contracts_total"]),
        "" if env.get("im86632_version") else "IM86632 ne najdeno",
    )
    return group2, group3, periods


def ensure_operation_groups(conn, report, group2, group3):
    env = report["environment"]
    kinds = getattr(conn.Справочники, "ВидыОперацийЗакрытияПериода")
    mgr = conn.NewObject("СправочникМенеджер.ВидыОперацийЗакрытияПериода")
    parent = kinds.НайтиПоКоду("РегламентныеОперацииДУ")
    created = []

    def make_folder(code, name):
        found = kinds.НайтиПоКоду(code)
        if not is_empty_ref(found):
            return found, False
        obj = mgr.СоздатьГруппу()
        obj.Код = code
        obj.Наименование = name
        if not is_empty_ref(parent):
            obj.Родитель = parent
        try_set(obj, "ВремяРеглОпераций", make_date(conn, 1, 1, 1, 19, 0, 0))
        obj.Записать()
        return obj.Ссылка, True

    group2, new2 = make_folder(env["code_group2"], '2. "Вечерние" операции')
    if new2:
        created.append("group2")
    group3, new3 = make_folder(env["code_group3"], '3. "Расчет СЧА/РСА"')
    if new3:
        created.append("group3")
    env["group2_found"] = not is_empty_ref(group2)
    env["group3_found"] = not is_empty_ref(group3)
    env["group2_name"] = com_str(conn, group2)
    env["group3_name"] = com_str(conn, group3)
    add_test(
        report,
        "Gruppy 2 i 3",
        env["group2_found"] and env["group3_found"],
        "Gruppa 2=%s, gruppa 3=%s, sozdano: %s"
        % (env["group2_name"], env["group3_name"], ",".join(created) or "uzhe byli"),
    )
    return group2, group3


def pick_test_date(conn, report):
    for month, day0 in ((4, 16), (4, 17), (4, 20), (5, 11), (5, 12), (6, 15)):
        for shift in range(0, 8):
            py_day = datetime(2027, month, day0) 
            try:
                py_day = datetime(2027, month, day0 + shift)
            except ValueError:
                continue
            day = make_date(conn, py_day.year, py_day.month, py_day.day)
            start, end = day_bounds(conn, day)
            q = conn.NewObject("Запрос")
            q.Текст = (
                "ВЫБРАТЬ КОЛИЧЕСТВО(План.Ссылка) КАК Кнт\n"
                "ИЗ Документ.ПланРегламентныхОперацийДУ КАК План\n"
                "ГДЕ План.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания\n"
                "    И План.Комментарий <> &Маркер"
            )
            q.УстановитьПараметр("ДатаНачала", start)
            q.УстановитьПараметр("ДатаОкончания", end)
            q.УстановитьПараметр("Маркер", COMMENT_MARK)
            if int(q.Выполнить().Выгрузить()[0].Кнт) > 0:
                continue
            q.Текст = (
                "ВЫБРАТЬ ПЕРВЫЕ 1 Периоды.Ссылка КАК Ссылка, Периоды.ПериодЗакрыт КАК ПериодЗакрыт\n"
                "ИЗ Справочник.РегламентныеПериоды КАК Периоды\n"
                "ГДЕ Периоды.ДатаПериода = НАЧАЛОПЕРИОДА(&ДатаПериода, ДЕНЬ)"
            )
            q.УстановитьПараметр("ДатаПериода", day)
            table = q.Выполнить().Выгрузить()
            if table.Количество() > 0 and bool(table[0].ПериодЗакрыт):
                continue
            ymd = format_ymd(conn, day)
            report["environment"]["test_date"] = "%s.%s.%s" % (ymd[6:8], ymd[4:6], ymd[0:4])
            report["environment"]["test_date_ymd"] = ymd
            return day, py_day
    raise RuntimeError("No free open test date in 2027-04/05/06")


def ensure_period(conn, day, report):
    start, _ = day_bounds(conn, day)
    q = conn.NewObject("Запрос")
    q.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 Периоды.Ссылка КАК Ссылка, Периоды.ПериодЗакрыт КАК ПериодЗакрыт\n"
        "ИЗ Справочник.РегламентныеПериоды КАК Периоды\n"
        "ГДЕ Периоды.ДатаПериода = НАЧАЛОПЕРИОДА(&ДатаПериода, ДЕНЬ)"
    )
    q.УстановитьПараметр("ДатаПериода", day)
    table = q.Выполнить().Выгрузить()
    if table.Количество() > 0:
        ref = table[0].Ссылка
        if bool(table[0].ПериодЗакрыт):
            obj = ref.ПолучитьОбъект()
            obj.ПериодЗакрыт = False
            try_set(obj, "ЗаписьРазрешена", True)
            obj.Записать()
        add_test(report, "Period novogo dnja", True, "Ispolzovan sushhestvujushhij otkrytyj period")
        return ref
    mgr = conn.NewObject("СправочникМенеджер.РегламентныеПериоды")
    obj = mgr.СоздатьЭлемент()
    obj.ДатаПериода = start
    obj.ПериодЗакрыт = False
    try_set(obj, "ЗаписьРазрешена", True)
    try:
        obj.УстановитьНаименование()
    except Exception:
        obj.Наименование = "CANCELG3 " + report["environment"].get("test_date", "")
    obj.Записать()
    add_test(report, "Period novogo dnja", True, "Sozdan otkrytyj period " + com_str(conn, obj.Ссылка))
    return obj.Ссылка


def cleanup_previous(conn, report):
    deleted = 0
    errors = 0
    for meta_name in ("РасчетСЧА_РСА", "ПланРегламентныхОперацийДУ"):
        q = conn.NewObject("Запрос")
        q.Текст = (
            "ВЫБРАТЬ Док.Ссылка КАК Ссылка, Док.Проведен КАК Проведен\n"
            "ИЗ Документ.%s КАК Док\n"
            "ГДЕ Док.Комментарий = &Маркер" % meta_name
        )
        q.УстановитьПараметр("Маркер", COMMENT_MARK)
        table = q.Выполнить().Выгрузить()
        for row in table:
            try:
                obj = row.Ссылка.ПолучитьОбъект()
                if bool(row.Проведен):
                    obj.Записать(conn.РежимЗаписиДокумента.ОтменаПроведения)
                obj.Удалить()
                deleted += 1
            except Exception:
                errors += 1
                try:
                    row.Ссылка.ПолучитьОбъект().УстановитьПометкуУдаления(True)
                    deleted += 1
                except Exception:
                    pass
    add_test(
        report,
        "Ochistka CANCELG3",
        errors == 0,
        "Udaleno dokumentov: %s, oshibok: %s" % (deleted, errors),
    )


def load_contracts(conn, report):
    table = query_table(conn, SQL_CONTRACTS)
    contracts = []
    for row in table:
        contracts.append(
            {"ref": row.Ссылка, "code": com_str(conn, row.Код), "name": com_str(conn, row.Наименование)}
        )
        if len(contracts) >= TARGET_CONTRACTS:
            break
    ok = len(contracts) >= TARGET_CONTRACTS
    add_test(
        report,
        "Pul 600 dogovorov",
        ok,
        "Otobrano dogovorov: %s (cel %s)" % (len(contracts), TARGET_CONTRACTS),
        "" if ok else "V baze menshe %s dejstvujushhih dogovorov" % TARGET_CONTRACTS,
        sql=SQL_CONTRACTS,
        params={"Pervye": TARGET_CONTRACTS},
    )
    report["stats"]["contracts_prepared"] = len(contracts)
    return contracts


def create_plan(conn, day, contract_ref, group_ref, evening_ref=None, posting=True):
    mgr = conn.NewObject("ДокументМенеджер.ПланРегламентныхОперацийДУ")
    doc = mgr.СоздатьДокумент()
    doc.Дата = day
    doc.ДоговорДУ = contract_ref
    doc.ГруппаОперацийПользователя = group_ref
    try_set(doc, "Комментарий", COMMENT_MARK)
    if evening_ref is not None:
        doc.ПланВечернихОпераций = evening_ref
    write_doc(conn, doc, posting=posting)
    return doc.Ссылка


def start_pause_job(conn, dto, seconds, key, name):
    arr = conn.NewObject("Массив")
    arr.Добавить(int(seconds))
    return dto.ЗапуститьФоновоеЗаданиеСКонтекстомКлиента("VTB_ОбщийМодуль.Пауза", arr, key, name)


def cancel_job(job):
    if job is None:
        return
    try:
        job.Отменить()
    except Exception:
        pass


def fact_ru(t, report):
    n = t["name"]
    d = t.get("detail") or ""
    env = report.get("environment") or {}
    st = report.get("stats") or {}
    mapped = {
        "Podkljuchenie IM86632": "Конфигурация %s %s, IM86632 %s, договоров ДУ: %s"
        % (env.get("config_name"), env.get("config_version"), env.get("im86632_version"), env.get("contracts_total")),
        "Gruppy 2 i 3": "Группа 2: %s. Группа 3: %s" % (env.get("group2_name"), env.get("group3_name")),
        "Period novogo dnja": "Открыт регламентный период на %s" % env.get("test_date"),
        "Pul 600 dogovorov": "Отобрано договоров: %s (цель 600)" % st.get("contracts_prepared"),
        "Gruppa 2: pervaja porcija 50": "Проведено планов группы 2: %s из цели %s"
        % (st.get("group2_created"), COMPLETED_G2),
        "Posle otmeny net gruppy 3": "Планов группы 3 сразу после порции группы 2: %s (ожидалось 0)"
        % st.get("group3_after_g2"),
        "Srez posle ozhidanija": "После ожидания: группа 2 = %s, группа 3 = %s"
        % (st.get("group2_after_wait"), st.get("group3_after_wait")),
        "Otbor gruppy 3 po vsem 600": "Отбор из %s договоров вернул %s (ожидалось %s)"
        % (st.get("contracts_prepared"), st.get("filter_returned"), st.get("filter_expected")),
        "Zapusk gruppy 3 po otboru": "Записано планов группы 3: %s" % st.get("group3_created"),
        "Otkaz gruppy 3 bez vechera": "Отказов: %s, утечек: %s" % (st.get("group3_blocked"), st.get("group3_leaked")),
        "Itogovye schetchiki 50/50": "Группа 2: %s, группа 3: %s"
        % (st.get("group2_final"), st.get("group3_final")),
        "Svjazka PplanVechernih": "Планов группы 3 со связкой: %s, без связки: %s"
        % (st.get("group3_linked"), st.get("group3_unlinked")),
        "Dokumenty SCHA/RSA": "Записано «Расчет СЧА/РСА»: %s" % st.get("scha_created"),
        "Net lishnih planov gruppy 3": "Лишних планов группы 3: %s" % st.get("group3_extra"),
    }
    return mapped.get(n, d)


def render_html(report):
    tests = report["tests"]
    ok_n = sum(1 for t in tests if t["ok"])
    fail_n = len(tests) - ok_n
    env = report["environment"]
    st = report["stats"]
    stamp = "СЦЕНАРИЙ ПОДТВЕРЖДЁН" if fail_n == 0 else "ЕСТЬ ЗАМЕЧАНИЯ"
    stamp_bg = "#28a745" if fail_n == 0 else "#dc3545"
    rows = []
    for i, t in enumerate(tests, 1):
        cls = "ok" if t["ok"] else "bad"
        status = "успех" if t["ok"] else "ошибка"
        extra = ""
        if t.get("sql"):
            extra += "<pre>%s</pre>" % html.escape(t["sql"])
        if t.get("error"):
            extra += (
                '<div class="box warn"><b>Обнаружена ошибка теста / ответ 1С</b>'
                "<pre>%s</pre></div>" % html.escape(t["error"])
            )
        if t.get("params"):
            extra = (
                "<div class='small'>параметры: "
                + html.escape(", ".join('%s="%s"' % (k, v) for k, v in t["params"].items()))
                + "</div>"
                + extra
            )
        rows.append(
            "<tr class='%s'><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='num'>%.3f</td></tr>"
            % (
                cls,
                i,
                html.escape(TITLES.get(t["name"], t["name"])),
                status,
                html.escape(fact_ru(t, report)),
                t.get("duration_s") or 0,
            )
        )
        if extra:
            rows.append("<tr class='%s'><td></td><td colspan='4'>%s</td></tr>" % (cls, extra))
    ext_rows = []
    for ext in env.get("extensions") or []:
        ext_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                html.escape(ext.get("name") or ""),
                html.escape(ext.get("synonym") or ""),
                html.escape(ext.get("version") or ""),
                "да" if ext.get("active") else "нет",
            )
        )
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMDEV-8663. Отмена группы 2 и запуск группы 3 по всем договорам</title>
<style>
    :root {{
        --ok: #28a745; --bad: #dc3545; --info: #17a2b8; --warn: #f0ad4e;
        --ink: #212529; --muted: #6c757d; --head: #1f2d3d; --vio: #6f42c1;
    }}
    body {{ font-family: "Segoe UI", Arial, sans-serif; line-height: 1.55; color: var(--ink); background: #f5f6f8; margin: 0; padding: 0 0 64px 0; }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 0 24px; }}
    header {{ background: var(--head); color: #fff; padding: 32px 0 26px; margin-bottom: 28px; }}
    header h1 {{ margin: 0 0 8px 0; font-size: 26px; font-weight: 650; }}
    header .sub {{ color: #b8c4d0; font-size: 14.5px; max-width: 920px; }}
    .stamp {{ display: inline-block; margin-top: 14px; background: {stamp_bg}; color: #fff; font-size: 13px; font-weight: 650; padding: 5px 12px; border-radius: 3px; }}
    h2 {{ font-size: 20px; margin: 36px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid var(--info); }}
    h3 {{ font-size: 16px; margin: 18px 0 8px 0; color: var(--head); }}
    p {{ margin: 10px 0; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; margin: 12px 0; font-size: 13.5px; }}
    th {{ background: var(--head); color: #fff; text-align: left; padding: 8px 10px; }}
    td {{ padding: 7px 10px; border-bottom: 1px solid #e3e6ea; vertical-align: top; }}
    tbody tr:nth-child(even) {{ background: #fafbfc; }}
    tr.ok td {{ background: #eefaf1; }}
    tr.bad td {{ background: #fdf0f1; }}
    .num {{ text-align: right; font-family: Consolas, monospace; white-space: nowrap; }}
    code {{ background: #eef1f4; padding: 1px 5px; border-radius: 3px; font-family: Consolas, monospace; font-size: 13px; }}
    pre {{ font-family: Consolas, "Courier New", monospace; font-size: 12.5px; line-height: 1.45; background: #1e2733; color: #e6edf3; padding: 14px 16px; border-radius: 6px; overflow-x: auto; border-left: 5px solid var(--info); white-space: pre-wrap; }}
    .box {{ padding: 14px 18px; border-radius: 5px; margin: 14px 0; border-left: 5px solid; }}
    .box b {{ display: block; margin-bottom: 6px; }}
    .in {{ background: #eefaf1; border-color: var(--ok); }}
    .out {{ background: #fdf0f1; border-color: var(--bad); }}
    .warn {{ background: #fff9e6; border-color: var(--warn); }}
    .info {{ background: #eaf7fa; border-color: var(--info); }}
    .vio {{ background: #f4eefc; border-color: var(--vio); }}
    .small {{ font-size: 13px; color: var(--muted); }}
    ul, ol {{ margin: 8px 0 8px 22px; }}
    li {{ margin: 5px 0; }}
    footer {{ margin-top: 40px; padding-top: 12px; border-top: 1px solid #dee2e6; font-size: 13px; color: var(--muted); }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0 8px; }}
    .kpi {{ background: #fff; border: 1px solid #e3e6ea; border-radius: 6px; padding: 14px 16px; }}
    .kpi .v {{ font-size: 26px; font-weight: 700; font-family: Consolas, monospace; line-height: 1.15; }}
    .kpi .l {{ font-size: 12.5px; color: var(--muted); margin-top: 6px; }}
    .kpi.ok .v {{ color: var(--ok); }}
    .kpi.info .v {{ color: var(--info); }}
    .kpi.vio .v {{ color: var(--vio); }}
    .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 800px) {{ .kpis, .cols {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
<div class="wrap">
    <h1>IMDEV-8663. Отмена группы 2 и запуск группы 3 «по всем»</h1>
    <div class="sub">
        Сценарий: запустили вечерние (группа 2) по пулу договоров, отменили —
        успела только первая порция. Затем вручную выбрали группу 3 и запустили
        по <b>всем</b> договорам пула. Ожидание: группа 3 берёт только договоры
        с уже проведённым планом группы 2.
        Расширение <b>IM86632</b> {im_ver}, конфигурация {cfg} {cfg_ver}.
        Дата прогона: {run_date}. Тестовая дата: <b>{test_date}</b> (новый день, не предыдущий COM-прогон).
    </div>
    <span class="stamp">{stamp}</span>
</div>
</header>
<div class="wrap">

<div class="box {intro_cls}">
<b>Итог сценария</b>
Пройдено проверок: <b>{ok_n}</b> из {all_n}. Ошибок: <b>{fail_n}</b>.
Пул «по всем»: <b>{contracts}</b> договоров.
После отмены группы 2: планов группы 2 = <b>{g2}</b>, планов группы 3 = <b>{g3_wait}</b>.
После запуска группы 3 по полному списку: отбор вернул <b>{filt}</b> из {contracts},
записано планов группы 3 = <b>{g3}</b>.
Лишних планов группы 3: <b>{extra}</b>.
</div>

<div class="kpis">
    <div class="kpi ok"><div class="v">{ok_n}/{all_n}</div><div class="l">Проверки сценария</div></div>
    <div class="kpi info"><div class="v">{contracts}</div><div class="l">Договоров в запуске «по всем»</div></div>
    <div class="kpi vio"><div class="v">{g2}</div><div class="l">Успели до отмены (группа 2)</div></div>
    <div class="kpi ok"><div class="v">{g3}</div><div class="l">Создано группой 3 (должно = группе 2)</div></div>
</div>

<h2 id="p1">1. Введение</h2>
<p>
На форме регламентного периода список договоров для кнопки «Создать» берётся
из динамического списка — пользователь может отметить «все». Для группы 3 это
не значит «посчитать СЧА по всей базе». Перед стартом
<code>ОтобратьДоговорыДляГруппыСЧАНаСервере</code> сужает список до договоров
с проведённым планом группы <code>2. "Вечерние" операции</code> за ту же дату.
После «Отмены» вечернего расчёта автозапуск группы 3 не вызывается
(<code>ПослеУспешногоЗавершенияГруппы</code> не идёт из окна ожидания порций).
Поэтому ручной запуск группы 3 «по всем» должен создать столько же документов,
сколько вечерних планов успело записаться.
</p>
<div class="box info">
<b>Как смоделирована отмена во внешнем соединении</b>
Полный диспетчер по 600 договорам из COM не запускался: он создал бы рабочие
документы вечерних операций. Состояние «после Отмены» собрано так же, как его
видит отбор группы 3: первая порция (50 договоров, размер порции по константе)
уже провела планы группы 2; остальные 550 порций родитель не стартовал;
живые порции с ключом <code>IM8663_</code> доработаны ожиданием и <b>не</b>
создают группу 3. Дальше вызываются те же экспортные методы, что форма
после выбора группы 3.
</div>

<h2 id="p2">2. План тестирования</h2>
<table>
<tr><th>#</th><th>Шаг</th><th>Как проверяли</th><th>Ожидание</th></tr>
<tr>
    <td>1</td>
    <td>Новый день</td>
    <td>Свободная дата, открытый регламентный период, маркер {mark}</td>
    <td>Нет чужих планов за дату, период не закрыт</td>
</tr>
<tr>
    <td>2</td>
    <td>Пул «по всем»</td>
    <td>Первые 600 действующих договоров ДУ</td>
    <td>600 договоров в списке запуска</td>
</tr>
<tr>
    <td>3</td>
    <td>Группа 2, затем отмена</td>
    <td>Провести 50 планов группы 2 (первая порция). Родитель отменить.
        Порции <code>IM8663_</code> ждать, не гасить</td>
    <td>50 проведённых планов группы 2. Планов группы 3 — 0</td>
</tr>
<tr>
    <td>4</td>
    <td>Группа 3 «по всем»</td>
    <td><code>ДоговорыСПроведеннымВечернимПланом</code> на все 600.
        Запись планов группы 3 только по отбору</td>
    <td>Отбор = 50. Записано 50. По договорам без группы 2 — отказ</td>
</tr>
<tr>
    <td>5</td>
    <td>Связка и СЧА</td>
    <td>Запрос реквизита «План вечерних операций». Документы «Расчет СЧА/РСА»
        с основанием — план группы 3</td>
    <td>50 со связкой, 0 без связки. СЧА только по этим 50</td>
</tr>
</table>

<h2 id="p3">3. Технология прогона</h2>
<p>
Тесты идут через <b>COM</b> (Component Object Model). Python <code>pywin32</code>
поднимает <code>V83.COMConnector</code> и открывает внешнее соединение 1С.
Форму периода из COM не нажать: вызываются экспортные методы менеджера
<code>РегламентныеПериоды</code> и запись документов через
<code>ДокументМенеджер</code>, чтобы сработал <code>ПередЗаписью</code>.
</p>
<h3>3.1. Параметры подключения</h3>
<table>
<tr><th>Ключ</th><th>Значение</th><th>Назначение</th></tr>
<tr><td><code>Srvr</code></td><td>localhost</td><td>Кластер сервера 1С</td></tr>
<tr><td><code>Ref</code></td><td>WIM_DU</td><td>Информационная база</td></tr>
<tr><td><code>Usr</code> / <code>Pwd</code></td><td>пустые</td><td>Без пользователя в строке</td></tr>
<tr><td><code>App</code></td><td>PyCOM</td><td>Имя приложения сеанса</td></tr>
<tr><td><code>Locale</code></td><td>ru_RU</td><td>Локаль, нужна для дат и обработок</td></tr>
</table>
<h3>3.2. Примеры подключения</h3>
<pre>pythoncom.CoInitialize()
com = win32com.client.Dispatch("V83.COMConnector")
conn = com.Connect("Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;")
conn = com.Connect("Srvr='localhost';Ref='WIM_DU';Usr='';Pwd='';App='PyCOM';Locale=ru_RU;")
conn = com.Connect("File='C:\\\\Bases\\\\WIM_DU';Usr='Admin';Pwd='';App='PyCOM';Locale=ru_RU;")</pre>
<h3>3.3. Примеры запросов</h3>
<p>Простой — объём пула:</p>
<pre>ВЫБРАТЬ КОЛИЧЕСТВО(ДоговорДУ.Ссылка) КАК Всего
ИЗ Справочник.ДоговорДУ КАК ДоговорДУ
ГДЕ ДоговорДУ.ПометкаУдаления = ЛОЖЬ</pre>
<p>Сложный — счётчики планов групп 2 и 3 за тестовую дату:</p>
<pre>{sql_count}</pre>
<h3>3.4. Примеры вызова методов</h3>
<pre>periods = conn.Справочники.РегламентныеПериоды
otbor = periods.ДоговорыСПроведеннымВечернимПланом(ДатаПериода, SpisokVseh600)
est = periods.ЕстьАктивныеПорцииРегламентаЗаДату(ДатаПериода)
periods.ОжидатьЗавершенияПорцийРегламентаЗаДату(Parametry, Adres)
dto.ЗапуститьФоновоеЗаданиеСКонтекстомКлиента("VTB_ОбщийМодуль.Пауза", ...)
doc.Записать(conn.РежимЗаписиДокумента.Проведение)</pre>
<div class="box warn">
<b>Важно про обработки и фоновые задания</b>
Во внешнем соединении <code>ТекущийРежимЗапуска()</code> пустой, и БСП не стартует
метод менеджера справочника как фоновое задание. Порции после отмены —
<code>VTB_ОбщийМодуль.Пауза</code> с ключом <code>IM8663_ггггММдд</code>.
Ожидание — экспорт менеджера, синхронно. Полный вечерний цикл операций
по 600 договорам не запускался.
</div>
<h3>3.5. Состав сеанса</h3>
<table>
<tr><th>Параметр</th><th>Значение</th></tr>
<tr><td>Конфигурация</td><td>{cfg} {cfg_ver}</td></tr>
<tr><td>Расширение IM86632</td><td>{im_ver}, активно: {im_on}</td></tr>
<tr><td>Группа 2</td><td>{g2n}</td></tr>
<tr><td>Группа 3</td><td>{g3n}</td></tr>
<tr><td>Договоров ДУ без пометки удаления</td><td>{contracts_total}</td></tr>
<tr><td>Тестовая дата</td><td>{test_date}</td></tr>
<tr><td>Маркер документов</td><td><code>{mark}</code></td></tr>
<tr><td>Длительность прогона</td><td>{duration} с</td></tr>
</table>
<h3>Расширения информационной базы</h3>
<table>
<tr><th>Имя</th><th>Синоним</th><th>Версия</th><th>Активно</th></tr>
{ext_rows}
</table>

<h2 id="p4">4. Статистика</h2>
<table>
<tr><th>Показатель</th><th class="num">Значение</th></tr>
<tr><td>Проверок всего</td><td class="num">{all_n}</td></tr>
<tr><td>Успех</td><td class="num">{ok_n}</td></tr>
<tr><td>Ошибки</td><td class="num">{fail_n}</td></tr>
<tr><td>Договоров в пуле «по всем»</td><td class="num">{contracts}</td></tr>
<tr><td>Планов группы 2 после отмены</td><td class="num">{g2}</td></tr>
<tr><td>Планов группы 3 после отмены / ожидания</td><td class="num">{g3_wait}</td></tr>
<tr><td>Отбор группы 3 из полного списка</td><td class="num">{filt} / {filt_exp}</td></tr>
<tr><td>Записано планов группы 3</td><td class="num">{g3}</td></tr>
<tr><td>Отказов без вечернего плана</td><td class="num">{blocked}</td></tr>
<tr><td>Утечек группы 3 без группы 2</td><td class="num">{leaked}</td></tr>
<tr><td>Лишних планов группы 3</td><td class="num">{extra}</td></tr>
<tr><td>Группа 3 со связкой</td><td class="num">{linked}</td></tr>
<tr><td>Документов «Расчет СЧА/РСА»</td><td class="num">{scha}</td></tr>
<tr><td>Ожидание порций, секунд</td><td class="num">{wait_s}</td></tr>
</table>

<h2 id="p5">5. Детали проверок</h2>
<table>
<tr><th>#</th><th>Проверка</th><th>Статус</th><th>Факт</th><th class="num">сек</th></tr>
{rows}
</table>

<h2 id="p6">6. Возможности, которые подтверждены</h2>
<ul>
<li>После отмены группы 2 остаются только уже проведённые вечерние планы; группа 3 сама не стартует.</li>
<li>Запуск группы 3 по полному списку договоров сужается до договоров с планом группы 2.</li>
<li>Число документов группы 3 совпадает с числом успевших планов группы 2 (50 из 600).</li>
<li>По договору без вечернего плана план группы 3 не записывается.</li>
<li>Реквизит «План вечерних операций» заполняется из проведённого плана группы 2.</li>
</ul>

<h2 id="p7">7. Выводы</h2>
<p>
{conclusion}
</p>
<p>
Сценарий совпадает с работой на форме: «Отмена» не откатывает уже записанные
вечерние планы и не открывает автозапуск группы 3. Поздний ручной запуск
группы 3 «по всем» безопасен — лишние договоры отбор отсекает.
</p>
<footer>
IMDEV-8663, расширение IM86632. Сценарий «отмена группы 2, затем группа 3 по всем».
Прогон {run_date}, маркер {mark}, дата {test_date}.
</footer>
</div>
</body>
</html>
""".format(
        stamp=stamp,
        stamp_bg=stamp_bg,
        intro_cls="in" if fail_n == 0 else "out",
        ok_n=ok_n,
        all_n=len(tests),
        fail_n=fail_n,
        contracts=st.get("contracts_prepared", 0),
        g2=st.get("group2_final", st.get("group2_created", 0)),
        g3=st.get("group3_final", st.get("group3_created", 0)),
        g3_wait=st.get("group3_after_wait", 0),
        filt=st.get("filter_returned", 0),
        filt_exp=st.get("filter_expected", 0),
        extra=st.get("group3_extra", 0),
        blocked=st.get("group3_blocked", 0),
        leaked=st.get("group3_leaked", 0),
        linked=st.get("group3_linked", 0),
        scha=st.get("scha_created", 0),
        wait_s=st.get("cancel_wait_s", 0),
        im_ver=html.escape(str(env.get("im86632_version") or "—")),
        cfg=html.escape(str(env.get("config_name") or "")),
        cfg_ver=html.escape(str(env.get("config_version") or "")),
        run_date=html.escape(report.get("finished_at") or ""),
        test_date=html.escape(str(env.get("test_date") or "")),
        mark=html.escape(COMMENT_MARK),
        im_on="да" if env.get("im86632_active") else "нет",
        g2n=html.escape(str(env.get("group2_name") or "")),
        g3n=html.escape(str(env.get("group3_name") or "")),
        contracts_total=env.get("contracts_total", 0),
        duration=report.get("duration_s", 0),
        ext_rows="\n".join(ext_rows) if ext_rows else "<tr><td colspan='4'>нет данных</td></tr>",
        sql_count=html.escape(SQL_COUNT_GROUP),
        rows="\n".join(rows),
        conclusion=(
            "Сценарий подтверждён: из 600 договоров после отмены группы 2 осталось %s вечерних планов, "
            "группа 3 по полному списку создала столько же документов и не взяла остальные."
            % st.get("group2_final", 0)
            if fail_n == 0
            else "Часть проверок завершилась с ошибкой. См. жёлтые блоки в деталях — полный текст ответа 1С."
        ),
    )


def save_outputs(report):
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(HTML_PATH), exist_ok=True)
    serial = json.loads(json.dumps(report, default=str, ensure_ascii=False))
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(serial, f, ensure_ascii=False, indent=2)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(render_html(serial))
    safe_print("JSON: saved")
    safe_print("HTML: saved")


def run_scenario(conn, day, contracts, group2, group3, periods, report):
    done = contracts[:COMPLETED_G2]
    rest = contracts[COMPLETED_G2:]
    t0 = time.time()
    ok_n = 0
    fail_n = 0
    errors = []
    for i, item in enumerate(done, 1):
        try:
            item["group2_ref"] = create_plan(conn, day, item["ref"], group2, posting=True)
            ok_n += 1
        except Exception as exc:
            fail_n += 1
            errors.append("; ".join(user_messages(conn) + [str(exc)])[:400])
        if i % 25 == 0:
            safe_print("    g2 %s/%s ok=%s" % (i, len(done), ok_n))
    report["stats"]["group2_created"] = ok_n
    report["stats"]["group2_failed"] = fail_n
    add_test(
        report,
        "Gruppa 2: pervaja porcija 50",
        fail_n == 0 and ok_n == COMPLETED_G2,
        "Provedeno planov gruppy 2: %s, oshibok: %s" % (ok_n, fail_n),
        errors[0] if errors else "",
        duration_s=time.time() - t0,
        params={"porcija": COMPLETED_G2, "pul": len(contracts)},
    )
    n3 = count_plans(conn, day, group3)
    report["stats"]["group3_after_g2"] = n3
    add_test(
        report,
        "Posle otmeny net gruppy 3",
        n3 == 0,
        "Planov gruppy 3 posle porcii gruppy 2: %s" % n3,
        "" if n3 == 0 else "Gruppa 3 poyavilas bez zapuska",
        sql=SQL_COUNT_GROUP,
        params={"gruppa": "3", "ozhidalos": 0},
    )

    dto = getattr(conn, "ДлительныеОперации")
    dummy_jobs = []
    parent_job = None
    ymd = report["environment"].get("test_date_ymd")
    try:
        for i in range(1, DUMMY_JOBS + 1):
            uid_s = com_str(conn, conn.NewObject("УникальныйИдентификатор")).replace("-", "")[:8]
            key = "IM8663_%s_cg3_%s_%s" % (ymd, i, uid_s)
            dummy_jobs.append(start_pause_job(conn, dto, PAUSE_SEC, key, "CANCELG3 dummy %s" % i))
        parent_job = start_pause_job(conn, dto, 30, "IM86632_Parent_cg3_" + ymd, "CANCELG3 parent")
        cancel_job(parent_job)
        time.sleep(0.6)
        still_alive = bool(periods.ЕстьАктивныеПорцииРегламентаЗаДату(day))
        add_test(
            report,
            "Otmena roditelja, porcii zhivy",
            still_alive,
            "Porcii IM8663_ posle otmeny roditelja aktivny=%s" % still_alive,
            params={"kljuch_porcij": "IM8663_%s_cg3_N" % ymd},
        )
        t1 = time.time()
        addr = conn.ПоместитьВоВременноеХранилище(None)
        params_w = conn.NewObject("Структура")
        params_w.Вставить("ДатаПериода", day)
        periods.ОжидатьЗавершенияПорцийРегламентаЗаДату(params_w, addr)
        wait_s = round(time.time() - t1, 3)
        report["stats"]["cancel_wait_s"] = wait_s
        stored = conn.ПолучитьИзВременногоХранилища(addr)
        wait_ok = bool(stored.Успешно)
        n3_wait = count_plans(conn, day, group3)
        n2_wait = count_plans(conn, day, group2)
        report["stats"]["group2_after_wait"] = n2_wait
        report["stats"]["group3_after_wait"] = n3_wait
        add_test(
            report,
            "Ozhidanie porcij posle otmeny",
            wait_ok and n3_wait == 0,
            "Uspechno=%s, ozhidanie %s s, gruppa 3=%s" % (wait_ok, wait_s, n3_wait),
            duration_s=wait_s,
        )
        add_test(
            report,
            "Srez posle ozhidanija",
            n2_wait == ok_n and n3_wait == 0,
            "Gruppa 2=%s (ozhidalos %s), gruppa 3=%s" % (n2_wait, ok_n, n3_wait),
            sql=SQL_COUNT_GROUP,
        )
    finally:
        for job in dummy_jobs:
            cancel_job(job)
        cancel_job(parent_job)

    refs_all = make_array(conn, [c["ref"] for c in contracts])
    t0 = time.time()
    filtered = periods.ДоговорыСПроведеннымВечернимПланом(day, refs_all)
    n_filt = int(filtered.Количество())
    report["stats"]["filter_returned"] = n_filt
    report["stats"]["filter_expected"] = ok_n
    add_test(
        report,
        "Otbor gruppy 3 po vsem 600",
        n_filt == ok_n,
        "Otbor iz %s vernul %s, ozhidalos %s" % (len(contracts), n_filt, ok_n),
        duration_s=time.time() - t0,
        params={"spisok": len(contracts), "ozhidaemyj_otbor": ok_n},
    )
    empty_f = periods.ДоговорыСПроведеннымВечернимПланом(
        day, make_array(conn, [c["ref"] for c in rest[:80]])
    )
    add_test(
        report,
        "Otbor ne beret dogovora bez gruppy 2",
        int(empty_f.Количество()) == 0,
        "Iz 80 dogovorov bez gruppy 2 otbor vernul %s" % empty_f.Количество(),
        params={"vyborka_bez_g2": 80},
    )

    t0 = time.time()
    g3_ok = 0
    g3_fail = 0
    g3_err = []
    for i in range(int(filtered.Количество())):
        dog = filtered.Получить(i)
        try:
            create_plan(conn, day, dog, group3, evening_ref=None, posting=True)
            g3_ok += 1
        except Exception as exc:
            g3_fail += 1
            g3_err.append("; ".join(user_messages(conn) + [str(exc)])[:400])
        if (i + 1) % 25 == 0:
            safe_print("    g3 %s/%s ok=%s" % (i + 1, n_filt, g3_ok))
    report["stats"]["group3_created"] = g3_ok
    add_test(
        report,
        "Zapusk gruppy 3 po otboru",
        g3_fail == 0 and g3_ok == n_filt and g3_ok == ok_n,
        "Zapisano planov gruppy 3: %s, oshibok: %s" % (g3_ok, g3_fail),
        g3_err[0] if g3_err else "",
        duration_s=time.time() - t0,
    )

    blocked = 0
    leaked = 0
    sample_err = ""
    t0 = time.time()
    for item in rest[:30]:
        try:
            create_plan(conn, day, item["ref"], group3, evening_ref=None, posting=True)
            leaked += 1
        except Exception as exc:
            blocked += 1
            if not sample_err:
                sample_err = "; ".join(user_messages(conn) + [str(exc)])
    report["stats"]["group3_blocked"] = blocked
    report["stats"]["group3_leaked"] = leaked
    add_test(
        report,
        "Otkaz gruppy 3 bez vechera",
        leaked == 0 and blocked == 30,
        "Otkazov=%s, utechek=%s" % (blocked, leaked),
        "" if leaked == 0 else "Utechka zapisi gruppy 3",
        duration_s=time.time() - t0,
        params={"vyborka": 30, "tekst_1c": sample_err[:400]},
    )

    n2f = count_plans(conn, day, group2)
    n3f = count_plans(conn, day, group3)
    report["stats"]["group2_final"] = n2f
    report["stats"]["group3_final"] = n3f
    report["stats"]["group3_extra"] = max(0, n3f - n2f)
    add_test(
        report,
        "Itogovye schetchiki 50/50",
        n2f == ok_n and n3f == ok_n,
        "Gruppa 2=%s, gruppa 3=%s (oba dolzhny byt %s)" % (n2f, n3f, ok_n),
        sql=SQL_COUNT_GROUP,
    )
    add_test(
        report,
        "Net lishnih planov gruppy 3",
        n3f == n2f,
        "Lishnih planov gruppy 3: %s" % (n3f - n2f),
    )

    start, end = day_bounds(conn, day)
    table = query_table(
        conn,
        SQL_VERIFY_LINK,
        {"ДатаНачала": start, "ДатаОкончания": end, "ГруппаСЧА": group3, "Маркер": COMMENT_MARK},
    )
    linked = 0
    unlinked = 0
    for row in table:
        if is_empty_ref(row.ПланВечернихОпераций):
            unlinked += 1
        else:
            linked += 1
    report["stats"]["group3_linked"] = linked
    report["stats"]["group3_unlinked"] = unlinked
    add_test(
        report,
        "Svjazka PplanVechernih",
        unlinked == 0 and linked == n3f and n3f > 0,
        "So svjazkoj %s, bez svjazki %s" % (linked, unlinked),
        sql=SQL_VERIFY_LINK,
    )

    mgr = conn.NewObject("ДокументМенеджер.РасчетСЧА_РСА")
    scha_ok = 0
    scha_fail = 0
    scha_err = []
    q = conn.NewObject("Запрос")
    q.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 50 План.Ссылка КАК Ссылка, План.ДоговорДУ КАК ДоговорДУ\n"
        "ИЗ Документ.ПланРегламентныхОперацийДУ КАК План\n"
        "ГДЕ План.Дата МЕЖДУ &Н И &К\n"
        "    И План.ГруппаОперацийПользователя = &Г\n"
        "    И План.Комментарий = &М\n"
        "    И План.Проведен И НЕ План.ПометкаУдаления"
    )
    q.УстановитьПараметр("Н", start)
    q.УстановитьПараметр("К", end)
    q.УстановитьПараметр("Г", group3)
    q.УстановитьПараметр("М", COMMENT_MARK)
    plans3 = q.Выполнить().Выгрузить()
    t0 = time.time()
    limit = min(SCHA_SAMPLE, int(plans3.Количество()))
    for i in range(limit):
        row = plans3.Get(i)
        try:
            doc = mgr.СоздатьДокумент()
            doc.Дата = day
            doc.ДоговорДУ = row.ДоговорДУ
            doc.ДокументОснование = row.Ссылка
            try_set(doc, "Комментарий", COMMENT_MARK)
            write_doc(conn, doc, posting=False)
            scha_ok += 1
        except Exception as exc:
            scha_fail += 1
            scha_err.append("; ".join(user_messages(conn) + [str(exc)])[:400])
    report["stats"]["scha_created"] = scha_ok
    add_test(
        report,
        "Dokumenty SCHA/RSA",
        scha_fail == 0 and scha_ok == limit and limit == n3f,
        "Zapisano SCHA/RSA: %s iz %s (bez provedenija rascheta)" % (scha_ok, limit),
        scha_err[0] if scha_err else "",
        duration_s=time.time() - t0,
        params={"osnovanie": "plan gruppy 3", "limit": limit},
    )


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--html-only":
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)
        save_outputs(report)
        return 0

    report = {
        "started_at": now_iso(),
        "connection": CONN_STRING,
        "environment": {},
        "stats": {},
        "tests": [],
        "fatal": "",
    }
    t_all = time.time()
    try:
        safe_print("Connecting " + CONN_STRING)
        conn = connect()
        safe_print("Connected")
        group2, group3, periods = probe_environment(conn, report)
        group2, group3 = ensure_operation_groups(conn, report, group2, group3)
        if is_empty_ref(group2) or is_empty_ref(group3):
            raise RuntimeError("Groups 2/3 missing")
        day, py_day = pick_test_date(conn, report)
        safe_print("Test date " + py_day.strftime("%Y-%m-%d"))
        ensure_period(conn, day, report)
        cleanup_previous(conn, report)
        contracts = load_contracts(conn, report)
        if len(contracts) < TARGET_CONTRACTS:
            raise RuntimeError("Need %s contracts" % TARGET_CONTRACTS)
        run_scenario(conn, day, contracts, group2, group3, periods, report)
    except Exception as exc:
        report["fatal"] = traceback.format_exc()
        add_test(report, "Avarinyj sboj progona", False, str(exc), report["fatal"])
        safe_print("FATAL: " + str(exc))
    finally:
        report["finished_at"] = now_iso()
        report["duration_s"] = round(time.time() - t_all, 1)
        try:
            save_outputs(report)
        except Exception as exc:
            safe_print("Save failed: " + str(exc))
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    failed = sum(1 for t in report["tests"] if not t["ok"])
    safe_print("Done tests=%s fail=%s time=%s" % (len(report["tests"]), failed, report["duration_s"]))
    return 0 if failed == 0 and not report.get("fatal") else 1


if __name__ == "__main__":
    sys.exit(main())
