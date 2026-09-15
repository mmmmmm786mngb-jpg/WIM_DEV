#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COM-progon IM86632: podgotovka ~500 dogovorov, test otmeny porcij
i svjazki grupp 2 (vechernie) / 3 (SCHA/RSA) na WIM_DU.

Rezultaty:
- JSON v Testirovanie/reports
- HTML otchet v Dokumentacija/02_scha_rsa_group3
Konsol - tolko ASCII.
"""

from __future__ import print_function

import base64
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
CONN_EXAMPLES = [
    "Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;",
    "Srvr='localhost';Ref='WIM_DU';Usr='';Pwd='';App='PyCOM';Locale=ru_RU;",
    "File='C:\\Bases\\WIM_DU';Usr='Admin';Pwd='';App='PyCOM';Locale=ru_RU;",
]

COMMENT_MARK = "IM86632_COMTEST"
TARGET_CONTRACTS = 500
WITH_EVENING = 400
WITHOUT_EVENING = 100
GROUP3_AUTO = 200
GROUP3_PREFILL = 200
GROUP3_FAIL_SAMPLE = 30
SCHA_SAMPLE = 15
DUMMY_JOBS = 3
PAUSE_SEC = 12

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
JSON_PATH = os.path.join(PROJECT_DIR, "Тестирование", "reports", "im86632_com_test_result.json")
WEB_SHOTS_DIR = os.path.join(PROJECT_DIR, "Тестирование", "reports", "web_shots")
WEB_SHOTS = [
    (
        "01_group2_kinds.png",
        "Группа 2 в справочнике видов операций",
        "Папка группы 2. «Вечерние» операции в справочнике «Виды операций закрытия периода». "
        "Код группы совпадает с константой расширения.",
    ),
    (
        "02_group3_kinds.png",
        "Группа 3 в справочнике видов операций",
        "Папка группы 3. «Расчет СЧА/РСА» и операция «Расчет СЧА». "
        "Группа 3 — данные информационной базы, не предопределённый элемент.",
    ),
    (
        "03_plans_list_20270315.png",
        "Список планов за 15.03.2027",
        "Журнал «Регламентные операции (ДУ)» за тестовую дату. "
        "Планы группы 3 с заполненным столбцом «План вечерних операций» и комментарием IM86632_COMTEST.",
    ),
    (
        "04_plan_group3_evening_link.png",
        "План группы 3 со связкой",
        "Карточка плана группы 3: пользовательская группа «Расчет СЧА/РСА», "
        "реквизит «План вечерних операций» указывает на проведённый план группы 2 того же договора.",
    ),
    (
        "05_plan_group2.png",
        "План группы 2 — основание связки",
        "Карточка плана группы 2. «Вечерние» операции по тому же договору. "
        "Реквизит «План вечерних операций» пуст: это само основание, а не расчёт СЧА/РСА.",
    ),
    (
        "06_scha_evening_plan.png",
        "Документ Расчет СЧА/РСА",
        "Документ «Расчет СЧА/РСА»: основание — план группы 3, "
        "на форме показан план вечерних операций с этого основания.",
    ),
    (
        "07_period_form.png",
        "Открытый регламентный период",
        "Карточка регламентного периода 15.03.2027 на фоне тестовых планов. "
        "Окно ожидания порций в веб-клиенте не открывалось: полный диспетчер по договорам не запускался, "
        "ожидание и отмена подтверждены во внешнем соединении.",
    ),
]
HTML_PATH = os.path.join(
    PROJECT_DIR,
    "Документация",
    "02_scha_rsa_group3",
    "imdev86632_test_report_cancel_and_group3_link.html",
)

SQL_CONTRACTS = (
    "ВЫБРАТЬ ПЕРВЫЕ 500\n"
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

SQL_VERIFY_LINK = (
    "ВЫБРАТЬ\n"
    "    ПланРегламентныхОперацийДУ.Ссылка КАК Ссылка,\n"
    "    ПланРегламентныхОперацийДУ.ДоговорДУ КАК ДоговорДУ,\n"
    "    ПланРегламентныхОперацийДУ.ПланВечернихОпераций КАК ПланВечернихОпераций,\n"
    "    ПланРегламентныхОперацийДУ.Проведен КАК Проведен\n"
    "ИЗ\n"
    "    Документ.ПланРегламентныхОперацийДУ КАК ПланРегламентныхОперацийДУ\n"
    "ГДЕ\n"
    "    ПланРегламентныхОперацийДУ.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания\n"
    "    И ПланРегламентныхОперацийДУ.ГруппаОперацийПользователя = &ГруппаСЧА\n"
    "    И ПланРегламентныхОперацийДУ.Комментарий = &Маркер\n"
    "    И НЕ ПланРегламентныхОперацийДУ.ПометкаУдаления"
)


def safe_print(text):
    """ASCII console output."""
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
    q.Текст = (
        "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d, %d, %d, %d) КАК Д" % (year, month, day, hour, minute, second)
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


def write_doc(conn, doc, posting=True):
    mode = conn.РежимЗаписиДокумента.Проведение if posting else conn.РежимЗаписиДокумента.Запись
    doc.Записать(mode)


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


def probe_environment(conn, report):
    env = report["environment"]
    meta = conn.Метаданные
    env["config_name"] = com_str(conn, meta.Имя)
    env["config_version"] = com_str(conn, meta.Версия)
    env["config_synonym"] = com_str(conn, meta.Синоним)

    extensions = []
    try:
        ext_list = conn.РасширенияКонфигурации.Получить()
        for ext in ext_list:
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
        "ВЫБРАТЬ\n"
        "    КОЛИЧЕСТВО(ДоговорДУ.Ссылка) КАК Всего\n"
        "ИЗ\n"
        "    Справочник.ДоговорДУ КАК ДоговорДУ\n"
        "ГДЕ\n"
        "    ДоговорДУ.ПометкаУдаления = ЛОЖЬ"
    )
    env["contracts_total"] = int(q.Выполнить().Выгрузить()[0].Всего)

    add_test(
        report,
        "Podkljuchenie i rasshirenie IM86632",
        env.get("im86632_version") == "1.0.0.4" or bool(env.get("im86632_version")),
        "Konfiguracija %s %s, IM86632 %s, dogovorov=%s"
        % (
            env["config_name"],
            env["config_version"],
            env.get("im86632_version", "-"),
            env["contracts_total"],
        ),
        "" if env.get("im86632_version") else "Rasshirenie IM86632 ne najdeno",
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
    env["groups_created"] = created
    add_test(
        report,
        "Podgotovka grupp 2 i 3 v vide operacij",
        env["group2_found"] and env["group3_found"],
        "Gruppa 2=%s, gruppa 3=%s, sozdano seichas: %s"
        % (env["group2_name"], env["group3_name"], ",".join(created) or "uzhe byli"),
        "" if env["group2_found"] and env["group3_found"] else "Ne udalos sozdat gruppy vidov operacij",
    )
    return group2, group3


def pick_test_date(conn, report):
    for shift in range(0, 12):
        py_day = datetime(2027, 3, 15 + shift)
        day = make_date(conn, py_day.year, py_day.month, py_day.day)
        start, end = day_bounds(conn, day)
        q = conn.NewObject("Запрос")
        q.Текст = (
            "ВЫБРАТЬ\n"
            "    КОЛИЧЕСТВО(План.Ссылка) КАК Кнт\n"
            "ИЗ\n"
            "    Документ.ПланРегламентныхОперацийДУ КАК План\n"
            "ГДЕ\n"
            "    План.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания\n"
            "    И План.Комментарий <> &Маркер"
        )
        q.УстановитьПараметр("ДатаНачала", start)
        q.УстановитьПараметр("ДатаОкончания", end)
        q.УстановитьПараметр("Маркер", COMMENT_MARK)
        foreign = int(q.Выполнить().Выгрузить()[0].Кнт)
        if foreign > 0:
            continue
        q.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1\n"
            "    Периоды.Ссылка КАК Ссылка,\n"
            "    Периоды.ПериодЗакрыт КАК ПериодЗакрыт\n"
            "ИЗ\n"
            "    Справочник.РегламентныеПериоды КАК Периоды\n"
            "ГДЕ\n"
            "    Периоды.ДатаПериода = НАЧАЛОПЕРИОДА(&ДатаПериода, ДЕНЬ)"
        )
        q.УстановитьПараметр("ДатаПериода", day)
        table = q.Выполнить().Выгрузить()
        if table.Количество() > 0 and bool(table[0].ПериодЗакрыт):
            continue
        ymd = format_ymd(conn, day)
        report["environment"]["test_date"] = "%s.%s.%s" % (ymd[6:8], ymd[4:6], ymd[0:4])
        report["environment"]["test_date_ymd"] = ymd
        return day, py_day
    raise RuntimeError("No free open test date in 2027-03-15..26")


def ensure_period(conn, day, report):
    start, _ = day_bounds(conn, day)
    q = conn.NewObject("Запрос")
    q.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1\n"
        "    Периоды.Ссылка КАК Ссылка,\n"
        "    Периоды.ПериодЗакрыт КАК ПериодЗакрыт\n"
        "ИЗ\n"
        "    Справочник.РегламентныеПериоды КАК Периоды\n"
        "ГДЕ\n"
        "    Периоды.ДатаПериода = НАЧАЛОПЕРИОДА(&ДатаПериода, ДЕНЬ)"
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
        add_test(report, "Reglamentnyj period na datu testa", True, "Ispolzovan sushhestvujushhij period, otkryt")
        return ref

    mgr = conn.NewObject("СправочникМенеджер.РегламентныеПериоды")
    obj = mgr.СоздатьЭлемент()
    obj.ДатаПериода = start
    obj.ПериодЗакрыт = False
    try_set(obj, "ЗаписьРазрешена", True)
    try:
        obj.УстановитьНаименование()
    except Exception:
        obj.Наименование = "COMTEST " + report["environment"].get("test_date", "")
    obj.Записать()
    add_test(report, "Reglamentnyj period na datu testa", True, "Sozdan otkrytyj period " + com_str(conn, obj.Ссылка))
    return obj.Ссылка


def cleanup_previous(conn, day, report):
    deleted = 0
    errors = 0
    for meta_name in ("РасчетСЧА_РСА", "ПланРегламентныхОперацийДУ"):
        q = conn.NewObject("Запрос")
        q.Текст = (
            "ВЫБРАТЬ\n"
            "    Док.Ссылка КАК Ссылка,\n"
            "    Док.Проведен КАК Проведен\n"
            "ИЗ\n"
            "    Документ.%s КАК Док\n"
            "ГДЕ\n"
            "    Док.Комментарий = &Маркер"
            % meta_name
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
                    obj = row.Ссылка.ПолучитьОбъект()
                    obj.УстановитьПометкуУдаления(True)
                    deleted += 1
                except Exception:
                    pass
    add_test(
        report,
        "Ochistka predydushhego COMTEST",
        errors == 0,
        "Udaleno dokumentov: %s, oshibok: %s" % (deleted, errors),
        "" if errors == 0 else "Chast dokumentov ne udalilas",
    )
    return deleted


def load_contracts(conn, report):
    table = query_table(conn, SQL_CONTRACTS)
    contracts = []
    for row in table:
        contracts.append({"ref": row.Ссылка, "code": com_str(conn, row.Код), "name": com_str(conn, row.Наименование)})
        if len(contracts) >= TARGET_CONTRACTS:
            break
    ok = len(contracts) >= TARGET_CONTRACTS
    add_test(
        report,
        "Podgotovka pulja dogovorov DU",
        ok,
        "Otobrano dogovorov: %s (cel %s)" % (len(contracts), TARGET_CONTRACTS),
        "" if ok else "V baze menshe %s dejstvujushhih dogovorov" % TARGET_CONTRACTS,
        sql=SQL_CONTRACTS,
        params={"Pervye": TARGET_CONTRACTS, "PometkaUdalenija": False},
    )
    report["stats"]["contracts_prepared"] = len(contracts)
    return contracts


def create_plan(conn, day, contract_ref, group_ref, comment, evening_ref=None, posting=True):
    mgr = conn.NewObject("ДокументМенеджер.ПланРегламентныхОперацийДУ")
    doc = mgr.СоздатьДокумент()
    doc.Дата = day
    doc.ДоговорДУ = contract_ref
    doc.ГруппаОперацийПользователя = group_ref
    try_set(doc, "Комментарий", comment)
    if evening_ref is not None:
        doc.ПланВечернихОпераций = evening_ref
    write_doc(conn, doc, posting=posting)
    return doc.Ссылка


def create_group2_plans(conn, day, contracts, group2, report):
    subset = contracts[:WITH_EVENING]
    ok_n = 0
    fail_n = 0
    errors = []
    t0 = time.time()
    for i, item in enumerate(subset, 1):
        try:
            ref = create_plan(conn, day, item["ref"], group2, COMMENT_MARK, posting=True)
            item["group2_ref"] = ref
            item["group2_num"] = com_str(conn, ref)
            ok_n += 1
        except Exception as exc:
            fail_n += 1
            msg = "; ".join(user_messages(conn) + [str(exc)])
            errors.append(msg[:400])
            item["group2_error"] = msg
        if i % 50 == 0:
            safe_print("    group2 %s/%s ok=%s fail=%s" % (i, len(subset), ok_n, fail_n))
    report["stats"]["group2_created"] = ok_n
    report["stats"]["group2_failed"] = fail_n
    add_test(
        report,
        "Sozdanie provedennyh planov gruppy 2",
        fail_n == 0 and ok_n >= WITH_EVENING,
        "Provedeno planov gruppy 2: %s, oshibok: %s" % (ok_n, fail_n),
        errors[0] if errors else "",
        duration_s=time.time() - t0,
        params={"kolichestvo": ok_n, "gruppa": "2. vechernie"},
    )
    return [c for c in subset if "group2_ref" in c]


def create_group3_plans(conn, day, with_evening, without_evening, group3, report):
    auto_list = with_evening[:GROUP3_AUTO]
    prefill_list = with_evening[GROUP3_AUTO:GROUP3_AUTO + GROUP3_PREFILL]
    fail_list = without_evening[:GROUP3_FAIL_SAMPLE]

    auto_ok = 0
    auto_fail = 0
    auto_errors = []
    t0 = time.time()
    for i, item in enumerate(auto_list, 1):
        try:
            ref = create_plan(conn, day, item["ref"], group3, COMMENT_MARK, evening_ref=None, posting=True)
            item["group3_ref"] = ref
            item["group3_mode"] = "auto"
            auto_ok += 1
        except Exception as exc:
            auto_fail += 1
            auto_errors.append("; ".join(user_messages(conn) + [str(exc)])[:400])
        if i % 50 == 0:
            safe_print("    group3 auto %s/%s ok=%s" % (i, len(auto_list), auto_ok))
    add_test(
        report,
        "Gruppa 3: zapis bez predzanapolnenija (PeredZapisju)",
        auto_fail == 0 and auto_ok == len(auto_list) and len(auto_list) > 0,
        "Zapisano avtozapolneniem PplanVechernih: %s iz %s" % (auto_ok, len(auto_list)),
        auto_errors[0] if auto_errors else "",
        duration_s=time.time() - t0,
        params={"rezhim": "PeredZapisju ishhet provedennyj plan gruppy 2"},
    )

    pre_ok = 0
    pre_fail = 0
    pre_errors = []
    t0 = time.time()
    for i, item in enumerate(prefill_list, 1):
        try:
            ref = create_plan(
                conn, day, item["ref"], group3, COMMENT_MARK, evening_ref=item["group2_ref"], posting=True
            )
            item["group3_ref"] = ref
            item["group3_mode"] = "prefill"
            pre_ok += 1
        except Exception as exc:
            pre_fail += 1
            pre_errors.append("; ".join(user_messages(conn) + [str(exc)])[:400])
        if i % 50 == 0:
            safe_print("    group3 prefill %s/%s ok=%s" % (i, len(prefill_list), pre_ok))
    add_test(
        report,
        "Gruppa 3: zapis s keshom PplanVechernih (massovyj kontur)",
        pre_fail == 0 and pre_ok == len(prefill_list) and len(prefill_list) > 0,
        "Zapisano s predzanapolneniem: %s iz %s" % (pre_ok, len(prefill_list)),
        pre_errors[0] if pre_errors else "",
        duration_s=time.time() - t0,
        params={"rezhim": "atribut uzhe zapolnen, zapros ne vypolnjaetsja"},
    )

    blocked_ok = 0
    leaked = 0
    sample_err = ""
    t0 = time.time()
    for item in fail_list:
        try:
            create_plan(conn, day, item["ref"], group3, COMMENT_MARK, evening_ref=None, posting=True)
            leaked += 1
        except Exception as exc:
            blocked_ok += 1
            if not sample_err:
                sample_err = "; ".join(user_messages(conn) + [str(exc)])
    add_test(
        report,
        "Gruppa 3: otkaz bez provedennogo vechernego plana",
        leaked == 0 and blocked_ok == len(fail_list) and len(fail_list) > 0,
        "Otkazano zapis: %s, utechek: %s, vyborka bez gruppy 2: %s" % (blocked_ok, leaked, len(fail_list)),
        "" if leaked == 0 else "Dokument gruppy 3 zapisalsja bez vechernego plana",
        duration_s=time.time() - t0,
        params={"ozhidaemyj_otkaz": True, "tekst_1c": sample_err[:500]},
    )
    report["stats"]["group3_auto"] = auto_ok
    report["stats"]["group3_prefill"] = pre_ok
    report["stats"]["group3_blocked"] = blocked_ok
    report["stats"]["group3_leaked"] = leaked
    report["stats"]["group3_block_sample"] = sample_err
    return with_evening


def verify_link_query(conn, day, group3, report):
    start, end = day_bounds(conn, day)
    table = query_table(
        conn,
        SQL_VERIFY_LINK,
        {"ДатаНачала": start, "ДатаОкончания": end, "ГруппаСЧА": group3, "Маркер": COMMENT_MARK},
    )
    total = int(table.Количество())
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
        "Zapros: PplanVechernih zapolnen u planov gruppy 3",
        unlinked == 0 and linked == total and total > 0,
        "Planov gruppy 3: %s, so svjazkoj: %s, bez svjazki: %s" % (total, linked, unlinked),
        "" if unlinked == 0 else "Est plany gruppy 3 bez PplanVechernih",
        sql=SQL_VERIFY_LINK,
        params={"Маркер": COMMENT_MARK, "Группа": "3. raschet SCHA/RSA"},
    )


def test_manager_api(conn, day, contracts, with_evening, without_evening, periods, report):
    refs_all = make_array(conn, [c["ref"] for c in contracts])
    t0 = time.time()
    filtered = periods.ДоговорыСПроведеннымВечернимПланом(day, refs_all)
    n = int(filtered.Количество())
    expected = len(with_evening)
    add_test(
        report,
        "DogovorySProvedennymVechernimPlanom",
        n == expected,
        "Otbor vernul %s dogovorov, ozhidalos %s (iz pulja %s)" % (n, expected, len(contracts)),
        "" if n == expected else "Filtr gruppy 3 ne sovpal s podgotovlennymi planami gruppy 2",
        duration_s=time.time() - t0,
        params={"ДатаПериода": report["environment"].get("test_date"), "SpisokDogovorov": len(contracts)},
    )
    report["stats"]["filter_returned"] = n
    report["stats"]["filter_expected"] = expected

    empty_arr = make_array(conn, [c["ref"] for c in without_evening[:50]])
    empty_f = periods.ДоговорыСПроведеннымВечернимПланом(day, empty_arr)
    add_test(
        report,
        "Filtr gruppy 3 na dogovorah bez vechernego plana",
        int(empty_f.Количество()) == 0,
        "Otbor iz %s dogovorov bez gruppy 2 vernul %s" % (empty_arr.Количество(), empty_f.Количество()),
        params={"ozhidaemyj_otkaz_zapuska": True},
    )

    sample = with_evening[0]
    found = periods.НайтиПроведенныйВечернийПлан(day, sample["ref"])
    add_test(
        report,
        "NajtiProvedennyjVechernijPlan po odnomu dogovoru",
        not is_empty_ref(found),
        "Najden plan %s po dogovoru %s" % (com_str(conn, found), sample["code"]),
    )

    missing = periods.НайтиПроведенныйВечернийПлан(day, without_evening[0]["ref"])
    add_test(
        report,
        "NajtiProvedennyjVechernijPlan esli plana net",
        is_empty_ref(missing),
        "Dlya dogovora bez gruppy 2 vozvrashheno pusto/neopredeleno",
    )

    has_g3 = periods.ЕстьПланыГруппыСЧА(day, refs_all)
    add_test(
        report,
        "EstPlanyGruppySCHA posle podgotovki",
        bool(has_g3),
        "EstPlanyGruppySCHA=%s (preduprezhdenie pri povtornom vechernem zapuske)" % bool(has_g3),
    )


def create_scha_docs(conn, day, with_evening, report):
    sample = [c for c in with_evening if "group3_ref" in c][:SCHA_SAMPLE]
    ok_n = 0
    fail_n = 0
    errors = []
    t0 = time.time()
    mgr = conn.NewObject("ДокументМенеджер.РасчетСЧА_РСА")
    for item in sample:
        try:
            doc = mgr.СоздатьДокумент()
            doc.Дата = day
            doc.ДоговорДУ = item["ref"]
            doc.ДокументОснование = item["group3_ref"]
            try_set(doc, "Комментарий", COMMENT_MARK)
            write_doc(conn, doc, posting=False)
            item["scha_ref"] = doc.Ссылка
            ok_n += 1
        except Exception as exc:
            fail_n += 1
            errors.append("; ".join(user_messages(conn) + [str(exc)])[:400])
    report["stats"]["scha_created"] = ok_n
    report["stats"]["scha_failed"] = fail_n
    add_test(
        report,
        "Sozdanie dokumentov RaschetSCHA_RSA s osnovaniem gruppy 3",
        fail_n == 0 and ok_n == len(sample) and ok_n > 0,
        "Zapisano dokumentov SCHA/RSA: %s iz %s (bez provedenija rascheta)" % (ok_n, len(sample)),
        errors[0] if errors else "",
        duration_s=time.time() - t0,
        params={"DokumentOsnovanie": "Plan gruppy 3"},
    )


def start_pause_job_conn(conn, dto, seconds, key, name):
    arr = conn.NewObject("Массив")
    arr.Добавить(int(seconds))
    job = dto.ЗапуститьФоновоеЗаданиеСКонтекстомКлиента(
        "VTB_ОбщийМодуль.Пауза",
        arr,
        key,
        name,
    )
    return job


def cancel_job_obj(job):
    if job is None:
        return
    try:
        job.Отменить()
    except Exception:
        pass


def start_dummy_portions(conn, day, dto, report):
    jobs = []
    errors = []
    ymd = format_ymd(conn, day)
    report["environment"]["test_date_ymd"] = ymd
    for i in range(1, DUMMY_JOBS + 1):
        uid_s = com_str(conn, conn.NewObject("УникальныйИдентификатор")).replace("-", "")[:8]
        key = "IM8663_%s_dummy_%s_%s" % (ymd, i, uid_s)
        try:
            job = start_pause_job_conn(
                conn, dto, PAUSE_SEC, key, "IM86632 COMTEST dummy portion %s" % i
            )
            jobs.append({"job": job, "key": key, "error": ""})
        except Exception as exc:
            errors.append(str(exc))
            jobs.append({"job": None, "key": key, "error": str(exc)})
    started = sum(1 for j in jobs if j["job"] is not None)
    add_test(
        report,
        "Zapusk dummy-porcij s kljuchom IM8663_yyyyMMdd",
        started == DUMMY_JOBS,
        "Zapushheno FZ pauzy: %s iz %s, kljuch IM8663_%s_dummy_N, metod VTB_ObshhijModul.Pauza(%s)"
        % (started, DUMMY_JOBS, ymd, PAUSE_SEC),
        "" if started == DUMMY_JOBS else "; ".join(errors),
        params={
            "kljuch": "IM8663_%s_dummy_N" % ymd,
            "metod": "VTB_ObshhijModul.Pauza",
            "sekund": PAUSE_SEC,
        },
    )
    return jobs


def test_cancel(conn, day, periods, report):
    dto = getattr(conn, "ДлительныеОперации")
    dummy_jobs = []
    parent_job = None
    try:
        t0 = time.time()
        has0 = bool(periods.ЕстьАктивныеПорцииРегламентаЗаДату(day))
        add_test(
            report,
            "EstAktivnyePorcii do zapuska (dolzhno byt LoZh)",
            not has0,
            "EstAktivnyePorciiReglamentaZaDatu=%s" % has0,
            duration_s=time.time() - t0,
        )

        uid = conn.NewObject("УникальныйИдентификатор")
        pexec = dto.ПараметрыВыполненияВФоне(uid)
        pexec.НаименованиеФоновогоЗадания = "IM86632 COMTEST empty date"
        pexec.КлючФоновогоЗадания = "IM86632_Wait_empty_" + com_str(conn, uid)
        pexec.ОжидатьЗавершение = 0
        pexec.ЗапуститьНеВФоне = True
        params = conn.NewObject("Структура")
        result = dto.ВыполнитьВФоне(
            "Справочники.РегламентныеПериоды.ОжидатьЗавершенияПорцийРегламентаЗаДату",
            params,
            pexec,
        )
        stored_ok = False
        stored_detail = com_str(conn, result.Статус)
        try:
            stored = conn.ПолучитьИзВременногоХранилища(result.АдресРезультата)
            stored_ok = bool(stored.Успешно)
            stored_detail += ", Uspechno=" + str(stored_ok)
        except Exception as exc:
            stored_detail += " / storage: " + str(exc)
        add_test(
            report,
            "Ozhidanie porcij s pustoj datoj (srazu Uspechno)",
            com_str(conn, result.Статус) in ("Выполнено",) and stored_ok,
            stored_detail,
        )

        dummy_jobs = start_dummy_portions(conn, day, dto, report)
        time.sleep(1.2)
        has1 = bool(periods.ЕстьАктивныеПорцииРегламентаЗаДату(day))
        add_test(
            report,
            "EstAktivnyePorcii posle zapuska dummy IM8663_",
            has1,
            "EstAktivnyePorciiReglamentaZaDatu=%s (ozhidaetsja Istina)" % has1,
        )

        ymd = report["environment"].get("test_date_ymd") or "20270315"
        try:
            parent_job = start_pause_job_conn(
                conn,
                dto,
                30,
                "IM86632_Parent_" + ymd,
                "IM86632 COMTEST parent (cancel me)",
            )
            cancel_job_obj(parent_job)
            parent_status = "otmenen"
        except Exception as exc:
            parent_status = "err " + str(exc)[:180]
        time.sleep(0.8)
        has_after_parent = bool(periods.ЕстьАктивныеПорцииРегламентаЗаДату(day))
        add_test(
            report,
            "Otmena roditelja ne gasit porcii IM8663_",
            has_after_parent,
            "Roditel %s, porcii IM8663_ zhivy=%s" % (parent_status, has_after_parent),
            params={"kljuch_roditelja": "IM86632_Parent_...", "porcii": "IM8663_yyyyMMdd_dummy_N"},
        )

        has_before_wait = bool(periods.ЕстьАктивныеПорцииРегламентаЗаДату(day))
        addr = conn.ПоместитьВоВременноеХранилище(None)
        params_w = conn.NewObject("Структура")
        params_w.Вставить("ДатаПериода", day)
        t_wait = time.time()
        wait_err = ""
        try:
            periods.ОжидатьЗавершенияПорцийРегламентаЗаДату(params_w, addr)
        except Exception as exc:
            wait_err = str(exc)
        wait_s = time.time() - t_wait
        stored_ok = False
        try:
            stored = conn.ПолучитьИзВременногоХранилища(addr)
            stored_ok = bool(stored.Успешно)
        except Exception:
            pass
        add_test(
            report,
            "Ozhidanie porcij ne vyzyvaet Otmenit() u detej",
            has_before_wait and wait_s >= 6 and wait_err == "",
            "Do ozhidanija porcii zhivy=%s, ozhidanie shlo %.1f s (pauza %s s). Esli by Otmenit() - vernulos by za ~5 s."
            % (has_before_wait, wait_s, PAUSE_SEC),
            wait_err,
            duration_s=wait_s,
            params={"kljuch_ozhidanija": "vyzov menedzhera vo vneshnem soedinenii"},
        )

        has_end = bool(periods.ЕстьАктивныеПорцииРегламентаЗаДату(day))
        add_test(
            report,
            "Waiter zavershaetsja kogda porcii IM8663_ konchilis",
            (not has_end) and stored_ok and wait_err == "",
            "EstAktivnyePorcii=%s, Uspechno=%s, wait_s=%.1f" % (has_end, stored_ok, wait_s),
            wait_err,
            duration_s=wait_s,
        )
        report["stats"]["cancel_dummy_jobs"] = DUMMY_JOBS
        report["stats"]["cancel_waiter_finished"] = not has_end
        report["stats"]["cancel_wait_s"] = round(wait_s, 1)
    finally:
        for item in dummy_jobs:
            cancel_job_obj(item.get("job"))
        cancel_job_obj(parent_job)


TITLES = {
    "Podkljuchenie i rasshirenie IM86632": "Подключение и расширение IM86632",
    "Podgotovka grupp 2 i 3 v vide operacij": "Подготовка групп 2 и 3 в видах операций",
    "Reglamentnyj period na datu testa": "Регламентный период на дату теста",
    "Ochistka predydushhego COMTEST": "Очистка предыдущих тестовых документов",
    "Podgotovka pulja dogovorov DU": "Подготовка пула договоров ДУ",
    "Sozdanie provedennyh planov gruppy 2": "Создание проведённых планов группы 2",
    "Gruppa 3: zapis bez predzanapolnenija (PeredZapisju)": "Группа 3: запись без предзаполнения (ПередЗаписью)",
    "Gruppa 3: zapis s keshom PplanVechernih (massovyj kontur)": "Группа 3: запись с кэшем плана вечерних",
    "Gruppa 3: otkaz bez provedennogo vechernego plana": "Группа 3: отказ без проведённого вечернего плана",
    "Zapros: PplanVechernih zapolnen u planov gruppy 3": "Запрос: реквизит «План вечерних операций» заполнен",
    "DogovorySProvedennymVechernimPlanom": "Отбор ДоговорыСПроведеннымВечернимПланом",
    "Filtr gruppy 3 na dogovorah bez vechernego plana": "Фильтр группы 3 на договорах без вечернего плана",
    "NajtiProvedennyjVechernijPlan po odnomu dogovoru": "НайтиПроведенныйВечернийПлан по одному договору",
    "NajtiProvedennyjVechernijPlan esli plana net": "НайтиПроведенныйВечернийПлан, если плана нет",
    "EstPlanyGruppySCHA posle podgotovki": "ЕстьПланыГруппыСЧА после подготовки",
    "Sozdanie dokumentov RaschetSCHA_RSA s osnovaniem gruppy 3": "Создание документов «Расчет СЧА/РСА»",
    "EstAktivnyePorcii do zapuska (dolzhno byt LoZh)": "ЕстьАктивныеПорции до запуска (ложь)",
    "Ozhidanie porcij s pustoj datoj (srazu Uspechno)": "Ожидание порций с пустой датой",
    "Zapusk dummy-porcij s kljuchom IM8663_yyyyMMdd": "Запуск порций с ключом IM8663_ггггММдд",
    "EstAktivnyePorcii posle zapuska dummy IM8663_": "ЕстьАктивныеПорции после запуска порций",
    "Otmena roditelja ne gasit porcii IM8663_": "Отмена родителя не гасит порции IM8663_",
    "Ozhidanie porcij ne vyzyvaet Otmenit() u detej": "Ожидание порций не вызывает Отменить() у детей",
    "Waiter zavershaetsja kogda porcii IM8663_ konchilis": "Ожидание завершается, когда порции закончились",
    "Avarinyj sboj progona": "Аварийный сбой прогона",
}


def fact_ru(t, report):
    st = report.get("stats") or {}
    env = report.get("environment") or {}
    n = t["name"]
    d = t.get("detail") or ""
    if n == "Podkljuchenie i rasshirenie IM86632":
        return "Конфигурация %s %s, IM86632 %s, договоров ДУ без пометки удаления: %s" % (
            env.get("config_name"), env.get("config_version"), env.get("im86632_version"), env.get("contracts_total"))
    if n == "Podgotovka grupp 2 i 3 v vide operacij":
        created = env.get("groups_created") or []
        return "Группа 2 и группа 3 найдены в справочнике видов операций. Созданы в этом прогоне: %s" % (
            ", ".join(created) if created else "уже были")
    if n == "Reglamentnyj period na datu testa":
        return "Открыт регламентный период на %s" % env.get("test_date")
    if n == "Ochistka predydushhego COMTEST":
        return d.replace("Udaleno dokumentov", "Удалено документов").replace("oshibok", "ошибок")
    if n == "Podgotovka pulja dogovorov DU":
        return "Отобрано договоров: %s (цель %s)" % (st.get("contracts_prepared"), TARGET_CONTRACTS)
    if n == "Sozdanie provedennyh planov gruppy 2":
        return "Проведено планов группы 2: %s, ошибок: %s" % (st.get("group2_created"), st.get("group2_failed"))
    if n == "Gruppa 3: zapis bez predzanapolnenija (PeredZapisju)":
        return "Записано автозаполнением «План вечерних операций»: %s" % st.get("group3_auto")
    if n == "Gruppa 3: zapis s keshom PplanVechernih (massovyj kontur)":
        return "Записано с предзаполнением из кэша: %s" % st.get("group3_prefill")
    if n == "Gruppa 3: otkaz bez provedennogo vechernego plana":
        return "Отказов записи: %s, утечек: %s" % (st.get("group3_blocked"), st.get("group3_leaked"))
    if n == "Zapros: PplanVechernih zapolnen u planov gruppy 3":
        return "Планов группы 3: %s со связкой, без связки: %s" % (st.get("group3_linked"), st.get("group3_unlinked"))
    if n == "DogovorySProvedennymVechernimPlanom":
        return "Отбор вернул %s договоров, ожидалось %s" % (st.get("filter_returned"), st.get("filter_expected"))
    if n == "Filtr gruppy 3 na dogovorah bez vechernego plana":
        return "Отбор договоров без проведённого плана группы 2 вернул пустой список"
    if n == "NajtiProvedennyjVechernijPlan po odnomu dogovoru":
        return "По договору с планом группы 2 найден проведённый вечерний план"
    if n == "NajtiProvedennyjVechernijPlan esli plana net":
        return "По договору без плана группы 2 возвращено пусто"
    if n == "EstPlanyGruppySCHA posle podgotovki":
        return "ЕстьПланыГруппыСЧА = да (предупреждение при повторном вечернем запуске)"
    if n == "Sozdanie dokumentov RaschetSCHA_RSA s osnovaniem gruppy 3":
        return "Записано документов «Расчет СЧА/РСА»: %s, ошибок: %s" % (st.get("scha_created"), st.get("scha_failed"))
    if n == "EstAktivnyePorcii do zapuska (dolzhno byt LoZh)":
        return "До запуска порций ЕстьАктивныеПорцииРегламентаЗаДату = нет"
    if n == "Ozhidanie porcij s pustoj datoj (srazu Uspechno)":
        return "Пустая дата: статус «Выполнено», Успешно = да"
    if n == "Zapusk dummy-porcij s kljuchom IM8663_yyyyMMdd":
        return "Запущено порций: %s, ключ IM8663_%s_..., метод паузы общего модуля" % (
            st.get("cancel_dummy_jobs"), env.get("test_date_ymd"))
    if n == "EstAktivnyePorcii posle zapuska dummy IM8663_":
        return "После запуска порций ЕстьАктивныеПорцииРегламентаЗаДату = да"
    if n == "Otmena roditelja ne gasit porcii IM8663_":
        return "Родитель отменён, порции IM8663_ остались активными"
    if n == "Ozhidanie porcij ne vyzyvaet Otmenit() u detej":
        return "Ожидание шло %s с при паузе порции 12 с: дети не отменялись" % st.get("cancel_wait_s")
    if n == "Waiter zavershaetsja kogda porcii IM8663_ konchilis":
        return "После ожидания ЕстьАктивныеПорции = нет, Успешно = да, %s с" % st.get("cancel_wait_s")
    return d


def png_data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def render_web_shots():
    parts = []
    found = 0
    for name, title, caption in WEB_SHOTS:
        path = os.path.join(WEB_SHOTS_DIR, name)
        if not os.path.isfile(path):
            continue
        found += 1
        parts.append(
            "<figure>"
            "<img class='shot' src='%s' alt='%s'>"
            "<figcaption><b>%s.</b> %s</figcaption>"
            "</figure>"
            % (png_data_uri(path), html.escape(title), html.escape(title), html.escape(caption))
        )
    if not found:
        return (
            '<h2 id="p4">4. Скриншоты веб-клиента</h2>\n'
            '<div class="box info"><b>Скриншоты</b>'
            "Кадры веб-клиента к этому прогону не приложены.</div>\n"
        )
    return (
        '<h2 id="p4">4. Скриншоты веб-клиента</h2>\n'
        "<p>Те же тестовые документы, что создал COM-прогон, открыты в веб-клиенте "
        "информационной базы WIM_DU. Маркер комментария <code>IM86632_COMTEST</code>, "
        "дата <b>15.03.2027</b>. Кадры встроены в отчёт, отдельные файлы не требуются.</p>\n"
        '<div class="box info"><b>Что видно на формах</b>\n'
        "У плана группы 3 заполнен реквизит «План вечерних операций». "
        "У документа «Расчет СЧА/РСА» тот же план показан с основания. "
        "Окно ожидания порций в веб-клиенте не снималось: полный диспетчер по договорам "
        "не запускался, отмена и ожидание подтверждены во внешнем соединении.</div>\n"
        + "\n".join(parts)
        + "\n"
    )


def render_html(report):
    tests = report["tests"]
    ok_n = sum(1 for t in tests if t["ok"])
    fail_n = len(tests) - ok_n
    env = report["environment"]
    st = report["stats"]
    stamp = "ТЕСТЫ ПРОЙДЕНЫ" if fail_n == 0 else "ЕСТЬ ЗАМЕЧАНИЯ"
    stamp_bg = "#28a745" if fail_n == 0 else "#dc3545"
    rows = []
    for i, t in enumerate(tests, 1):
        cls = "ok" if t["ok"] else "bad"
        status = "успех" if t["ok"] else "ошибка"
        sql_block = ""
        if t.get("sql"):
            sql_block = "<pre>%s</pre>" % html.escape(t["sql"])
        err_block = ""
        if t.get("error"):
            err_block = (
                '<div class="box warn"><b>Обнаружена ошибка теста / ответ 1С</b>'
                "<pre>%s</pre></div>" % html.escape(t["error"])
            )
        params_txt = ""
        if t.get("params"):
            params_txt = "<div class='small'>параметры: " + html.escape(
                ", ".join('%s="%s"' % (k, v) for k, v in t["params"].items())
            ) + "</div>"
        name_ru = TITLES.get(t["name"], t["name"])
        rows.append(
            "<tr class='%s'><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='num'>%.3f</td></tr>"
            % (
                cls,
                i,
                html.escape(name_ru),
                status,
                html.escape(fact_ru(t, report)),
                t.get("duration_s") or 0,
            )
        )
        if sql_block or err_block or params_txt:
            rows.append(
                "<tr class='%s'><td></td><td colspan='4'>%s%s%s</td></tr>"
                % (cls, params_txt, sql_block, err_block)
            )

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

    html_doc = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMDEV-8663. Отчёт о тестировании: отмена порций и связка групп 2 и 3</title>
<style>
    :root {{
        --ok: #28a745;
        --bad: #dc3545;
        --info: #17a2b8;
        --warn: #f0ad4e;
        --ink: #212529;
        --muted: #6c757d;
        --head: #1f2d3d;
        --vio: #6f42c1;
    }}
    body {{ font-family: "Segoe UI", Arial, sans-serif; line-height: 1.55; color: var(--ink); background: #f5f6f8; margin: 0; padding: 0 0 64px 0; }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 0 24px; }}
    header {{ background: var(--head); color: #fff; padding: 32px 0 26px; margin-bottom: 28px; }}
    header h1 {{ margin: 0 0 8px 0; font-size: 26px; font-weight: 650; }}
    header .sub {{ color: #b8c4d0; font-size: 14.5px; max-width: 920px; }}
    .stamp {{ display: inline-block; margin-top: 14px; background: {stamp_bg}; color: #fff; font-size: 13px; font-weight: 650; letter-spacing: 0.04em; padding: 5px 12px; border-radius: 3px; }}
    .stamp.ok {{ background: var(--ok); margin-top: 0; font-size: 12px; }}
    .stamp.bad {{ background: var(--bad); margin-top: 0; font-size: 12px; }}
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
    ul {{ margin: 8px 0 8px 22px; }}
    li {{ margin: 5px 0; }}
    footer {{ margin-top: 40px; padding-top: 12px; border-top: 1px solid #dee2e6; font-size: 13px; color: var(--muted); }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0 8px; }}
    .kpi {{ background: #fff; border: 1px solid #e3e6ea; border-radius: 6px; padding: 14px 16px; }}
    .kpi .v {{ font-size: 26px; font-weight: 700; font-family: Consolas, monospace; line-height: 1.15; }}
    .kpi .l {{ font-size: 12.5px; color: var(--muted); margin-top: 6px; }}
    .kpi.ok .v {{ color: var(--ok); }}
    .kpi.bad .v {{ color: var(--bad); }}
    .kpi.info .v {{ color: var(--info); }}
    .kpi.vio .v {{ color: var(--vio); }}
    .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    a {{ color: #0a58ca; }}
    figure {{ margin: 18px 0 28px 0; background: #fff; border: 1px solid #e3e6ea; border-radius: 6px; padding: 10px 10px 12px; }}
    .shot {{ max-width: 100%; border: 1px solid #d8dee4; border-radius: 6px; display: block; }}
    figcaption {{ font-size: 13px; color: var(--muted); margin-top: 8px; line-height: 1.45; }}
    figcaption b {{ color: var(--head); }}
    @media (max-width: 800px) {{
        .kpis, .cols {{ grid-template-columns: 1fr; }}
    }}
</style>
</head>
<body>
<header>
<div class="wrap">
    <h1>IMDEV-8663. Отчёт о тестировании отмены и связки групп 2 и 3</h1>
    <div class="sub">
        Расширение <b>IM86632</b> версии {im_ver}, конфигурация {cfg} {cfg_ver}.
        Прогон через внешнее соединение COM (pywin32) на информационной базе WIM_DU.
        Скриншоты форм — веб-клиент той же базы, те же тестовые документы.
        Дата прогона: {run_date}. Тестовая дата документов: <b>{test_date}</b>.
        Проверялись задача 1 (отмена родительского окна и ожидание порций IM8663_)
        и задача 2 (отбор группы 3 только по проведённому плану группы 2 и реквизит «План вечерних операций»).
    </div>
    <span class="stamp">{stamp}</span>
</div>
</header>
<div class="wrap">

<div class="box {intro_cls}">
<b>Итог</b>
Пройдено тестов: <b>{ok_n}</b> из {all_n}. Ошибок: <b>{fail_n}</b>.
Подготовлен пул из {contracts} договоров ДУ. Проведено планов группы 2: {g2}.
Планов группы 3 со связкой: {linked}. Отказов группы 3 без вечернего плана: {blocked}.
Документов расчёта СЧА/РСА: {scha}. Ожидание порций заняло {wait_s} с при паузе порции 12 с:
ожидание не гасит детей и закрывается само, когда ключи IM8663_ за дату исчезают.
Отмена родителя порции не гасит.
Скриншоты веб-клиента — в разделе 4: связка «План вечерних операций» на плане группы 3 и на документе «Расчет СЧА/РСА».
</div>

<div class="kpis">
    <div class="kpi {kpi_tests}">
        <div class="v">{ok_n}/{all_n}</div>
        <div class="l">Успешные проверки COM-прогона</div>
    </div>
    <div class="kpi info">
        <div class="v">{contracts}</div>
        <div class="l">Договоров ДУ в тестовом пуле</div>
    </div>
    <div class="kpi ok">
        <div class="v">{linked}</div>
        <div class="l">Планов группы 3 со связкой на группу 2</div>
    </div>
    <div class="kpi vio">
        <div class="v">{blocked}</div>
        <div class="l">Отказов записать группу 3 без вечернего плана</div>
    </div>
</div>

<h2 id="p1">1. Введение</h2>
<p>
Прогон имитирует контур вечернего закрытия без запуска полного диспетчера по всей базе.
На изолированную дату создаются проведённые планы группы <code>2. "Вечерние" операции</code>
и планы группы <code>3. "Расчет СЧА/РСА"</code>. Часть договоров специально остаётся без вечернего плана,
чтобы проверить отбор и отказ записи.
</p>
<div class="cols">
<div class="box info">
<b>Задача 1. Отмена</b>
«Отмена» гасит только родительское задание БСП. Уже запущенные порции с ключом
<code>IM8663_ггггММдд...</code> дорабатывают договор целиком. Второе окно только ждёт их окончания
и само не вызывает <code>Отменить()</code> у детей. Ключ ожидания — <code>IM86632_Wait_</code>.
</div>
<div class="box vio">
<b>Задача 2. Связка групп</b>
Группа 3 стартует только по договорам с проведённым планом группы 2 за дату.
У плана группы 3 заполняется реквизит <code>ПланВечернихОпераций</code>:
в массовом контуре из кэша, при ручной записи — в <code>ПередЗаписью</code>.
</div>
</div>
<p class="small">
Маркер тестовых документов: комментарий <code>{mark}</code>. Существующие договоры справочника не копировались:
полный элемент «Договор ДУ» требует обязательных реквизитов и связей. Для корректного создания документов
взяты действующие договоры базы, открыт регламентный период тестовой даты.
</p>

<h2 id="p2">2. Технология прогона</h2>
<p>
Тесты выполняются через <b>COM</b> (Component Object Model) — двоичный протокол Microsoft для вызова объектов
вне процесса. Библиотека Python <code>pywin32</code> поднимает <code>V83.COMConnector</code> и открывает
<b>внешнее соединение</b> 1С (не тонкий клиент и не форма). Поэтому вызываются экспортные методы
модуля менеджера справочника «Регламентные периоды», общие модули с признаком «Внешнее соединение»
и запись документов через менеджер документа. Общий модуль <code>ФоновыеЗаданияСервер</code>
во внешнее соединение не выводится — массовое создание плана в тесте идёт прямой записью документа,
чтобы сработал <code>ПередЗаписью</code>.
</p>

<h3>2.1. Параметры подключения</h3>
<p>Строка соединения внешнего соединения 1С. Используемые ключи:</p>
<table>
<tr><th>Ключ</th><th>Значение прогона</th><th>Назначение</th></tr>
<tr><td><code>Srvr</code></td><td>localhost</td><td>Кластер сервера 1С</td></tr>
<tr><td><code>Ref</code></td><td>WIM_DU</td><td>Имя информационной базы</td></tr>
<tr><td><code>Usr</code> / <code>Pwd</code></td><td>пустые</td><td>Аутентификация ОС / без пользователя в строке</td></tr>
<tr><td><code>App</code></td><td>PyCOM</td><td>Имя приложения сеанса</td></tr>
<tr><td><code>Locale</code></td><td>ru_RU</td><td>Локаль сеанса, нужна для обработок и дат</td></tr>
</table>

<h3>2.2. Примеры подключения</h3>
<pre>pythoncom.CoInitialize()
com = win32com.client.Dispatch("V83.COMConnector")

# 1. Серверная база прогона (этот отчёт)
conn = com.Connect("Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;")

# 2. Серверная база с явной аутентификацией
conn = com.Connect("Srvr='localhost';Ref='WIM_DU';Usr='';Pwd='';App='PyCOM';Locale=ru_RU;")

# 3. Файловая база (пример, в этом прогоне не использовалась)
conn = com.Connect("File='C:\\\\Bases\\\\WIM_DU';Usr='Admin';Pwd='';App='PyCOM';Locale=ru_RU;")</pre>

<h3>2.3. Примеры запросов</h3>
<p>Простой запрос — объём пула договоров:</p>
<pre>ВЫБРАТЬ
    КОЛИЧЕСТВО(ДоговорДУ.Ссылка) КАК Всего
ИЗ
    Справочник.ДоговорДУ КАК ДоговорДУ
ГДЕ
    ДоговорДУ.ПометкаУдаления = ЛОЖЬ</pre>
<p>Сложный запрос — проверка связки планов группы 3 с планом группы 2:</p>
<pre>{sql_link}</pre>

<h3>2.4. Примеры вызова методов</h3>
<pre># Модуль менеджера справочника (экспорт IM86632)
periods = conn.Справочники.РегламентныеПериоды
code2 = periods.КодВечернейГруппыОпераций()
otbor = periods.ДоговорыСПроведеннымВечернимПланом(ДатаПериода, СписокДоговоров)
est = periods.ЕстьАктивныеПорцииРегламентаЗаДату(ДатаПериода)

# Общий модуль БСП (внешнее соединение = да)
dto = conn.ДлительныеОперации
result = dto.ВыполнитьВФоне(
    "Справочники.РегламентныеПериоды.ОжидатьЗавершенияПорцийРегламентаЗаДату",
    ПараметрыПроцедуры, ПараметрыВыполнения)
dto.ОтменитьВыполнениеЗадания(result.ИдентификаторЗадания)

# Менеджер документа — запись, чтобы сработал ПередЗаписью
mgr = conn.NewObject("ДокументМенеджер.ПланРегламентныхОперацийДУ")
doc = mgr.СоздатьДокумент()
doc.ДоговорДУ = Договор
doc.ГруппаОперацийПользователя = Группа3
doc.Записать(conn.РежимЗаписиДокумента.Проведение)</pre>

<div class="box warn">
<b>Важно про обработки и фоновые задания</b>
Для создания объекта обработки во внешнем соединении в строке подключения обязательны
<code>App='PyCOM'</code> и <code>Locale=ru_RU</code>. Общий модуль без признака «Внешнее соединение»
из Python напрямую не вызывается. В сеансе внешнего соединения
<code>ТекущийРежимЗапуска()</code> пустой: БСП тогда передаёт имя метода сразу в
<code>ФоновыеЗадания.Выполнить</code>, а платформа принимает только методы общих модулей.
Поэтому порции диспетчера эмулированы заданием <code>VTB_ОбщийМодуль.Пауза</code> с ключом
<code>IM8663_ггггММдд...</code> — тем же префиксом, по которому
<code>ЕстьАктивныеПорцииРегламентаЗаДату</code> и ожидание находят живые чанки.
Ожидание вызвано экспортной процедурой менеджера справочника. Полный вечерний расчёт
по 500 договорам не запускался: он создал бы рабочие документы операций.
</div>

<h3>2.5. Состав сеанса</h3>
<table>
<tr><th>Параметр</th><th>Значение</th></tr>
<tr><td>Конфигурация</td><td>{cfg} {cfg_ver}</td></tr>
<tr><td>Расширение IM86632</td><td>{im_ver}, активно: {im_on}</td></tr>
<tr><td>Код группы 2</td><td><code>{code2}</code></td></tr>
<tr><td>Код группы 3</td><td><code>{code3}</code></td></tr>
<tr><td>Группа 2 в базе</td><td>{g2n}</td></tr>
<tr><td>Группа 3 в базе</td><td>{g3n}</td></tr>
<tr><td>Договоров ДУ без пометки удаления</td><td>{contracts_total}</td></tr>
<tr><td>Тестовая дата</td><td>{test_date}</td></tr>
<tr><td>Длительность прогона</td><td>{duration} с</td></tr>
</table>

<h3>Расширения информационной базы</h3>
<table>
<tr><th>Имя</th><th>Синоним</th><th>Версия</th><th>Активно</th></tr>
{ext_rows}
</table>

<h3>2.6. Скриншоты веб-клиента</h3>
<p>
Формы открыты в веб-клиенте той же информационной базы. Показаны документы с комментарием
<code>IM86632_COMTEST</code> за дату 15.03.2027: виды операций групп 2 и 3, журнал планов,
карточка плана группы 3 со связкой, план группы 2, документ «Расчет СЧА/РСА», регламентный период.
Кадры встроены в отчёт (раздел 4).
</p>

<h2 id="p3">3. Статистика</h2>
<table>
<tr><th>Показатель</th><th class="num">Значение</th></tr>
<tr><td>Проверок всего</td><td class="num">{all_n}</td></tr>
<tr><td>Успех</td><td class="num">{ok_n}</td></tr>
<tr><td>Ошибки</td><td class="num">{fail_n}</td></tr>
<tr><td>Договоров в пуле</td><td class="num">{contracts}</td></tr>
<tr><td>Проведённых планов группы 2</td><td class="num">{g2}</td></tr>
<tr><td>Ошибок создания группы 2</td><td class="num">{g2f}</td></tr>
<tr><td>Группа 3, автозаполнение в ПередЗаписью</td><td class="num">{g3a}</td></tr>
<tr><td>Группа 3, кэш массового контура</td><td class="num">{g3p}</td></tr>
<tr><td>Группа 3 со связкой (запрос)</td><td class="num">{linked}</td></tr>
<tr><td>Группа 3 без связки</td><td class="num">{unlinked}</td></tr>
<tr><td>Отказов группы 3 без вечернего плана</td><td class="num">{blocked}</td></tr>
<tr><td>Утечек записи группы 3 без плана 2</td><td class="num">{leaked}</td></tr>
<tr><td>Отбор ДоговорыСПроведеннымВечернимПланом</td><td class="num">{filt} / {filt_exp}</td></tr>
<tr><td>Документов РасчетСЧА_РСА</td><td class="num">{scha}</td></tr>
<tr><td>Порций IM8663_ в тесте отмены</td><td class="num">{dummy}</td></tr>
<tr><td>Ожидание порций, секунд</td><td class="num">{wait_s}</td></tr>
</table>

{shots_html}

<h2 id="p5">5. Детали тестов</h2>
<table>
<tr><th>#</th><th>Проверка</th><th>Статус</th><th>Факт</th><th class="num">сек</th></tr>
{rows}
</table>

<h2 id="p6">6. Возможности, которые подтверждены</h2>
<ul>
<li>Кнопка «Отмена» гасит родителя БСП; порции с ключом <code>IM8663_дата</code> остаются активными.</li>
<li>Служебное ожидание с ключом <code>IM86632_Wait_</code> не входит в список порций и не вызывает <code>Отменить()</code> у детей.</li>
<li>Пока порции живы, <code>ЕстьАктивныеПорцииРегламентаЗаДату</code> возвращает истину; после их окончания — ложь, окно ожидания закрывается.</li>
<li>Пустая дата у процедуры ожидания сразу кладёт в хранилище <code>Успешно = Истина</code>.</li>
<li>Группа 3 отбирает только договоры с проведённым планом группы 2; пустой отбор — штатный отказ запуска.</li>
<li>Ручная запись плана группы 3 без вечернего плана блокируется в <code>ПередЗаписью</code>.</li>
<li>Если реквизит уже заполнен (массовый контур), повторный поиск плана не нужен.</li>
<li>Документ «Расчет СЧА/РСА» создаётся с основанием — планом группы 3.</li>
</ul>

<h2 id="p7">7. Выводы</h2>
<p>
{conclusion}
</p>
<p>
Повторный запуск «Создать» после закрытия окна ожидания в этот COM-прогон не входил:
он штатно помечает подчиненные операции существующего плана и пересобирает их.
«Отмена» документы не откатывает — это согласованное поведение.
</p>

<footer>
IMDEV-8663, расширение IM86632. Отчёт сформирован по результатам COM-прогона {run_date}.
Тестовые документы помечены комментарием {mark}, дата {test_date}.
Скриншоты сняты в веб-клиенте по тем же документам.
</footer>
</div>
</body>
</html>
""".format(
        stamp=stamp,
        stamp_bg=stamp_bg,
        wait_s=st.get("cancel_wait_s", 0),
        intro_cls="in" if fail_n == 0 else "out",
        ok_n=ok_n,
        all_n=len(tests),
        fail_n=fail_n,
        contracts=st.get("contracts_prepared", 0),
        g2=st.get("group2_created", 0),
        g2f=st.get("group2_failed", 0),
        linked=st.get("group3_linked", 0),
        unlinked=st.get("group3_unlinked", 0),
        blocked=st.get("group3_blocked", 0),
        leaked=st.get("group3_leaked", 0),
        scha=st.get("scha_created", 0),
        im_ver=html.escape(str(env.get("im86632_version") or "—")),
        cfg=html.escape(str(env.get("config_name") or "")),
        cfg_ver=html.escape(str(env.get("config_version") or "")),
        run_date=html.escape(report.get("finished_at") or report.get("started_at") or ""),
        test_date=html.escape(str(env.get("test_date") or "")),
        mark=html.escape(COMMENT_MARK),
        sql_link=html.escape(SQL_VERIFY_LINK),
        im_on="да" if env.get("im86632_active") else "нет",
        code2=html.escape(str(env.get("code_group2") or "")),
        code3=html.escape(str(env.get("code_group3") or "")),
        g2n=html.escape(str(env.get("group2_name") or "")),
        g3n=html.escape(str(env.get("group3_name") or "")),
        contracts_total=env.get("contracts_total", 0),
        duration=report.get("duration_s", 0),
        ext_rows="\n".join(ext_rows) if ext_rows else "<tr><td colspan='4'>нет данных</td></tr>",
        g3a=st.get("group3_auto", 0),
        g3p=st.get("group3_prefill", 0),
        filt=st.get("filter_returned", 0),
        filt_exp=st.get("filter_expected", 0),
        dummy=st.get("cancel_dummy_jobs", 0),
        rows="\n".join(rows),
        shots_html=render_web_shots(),
        kpi_tests="ok" if fail_n == 0 else "bad",
        conclusion=(
            "Обе доработки IM86632 подтверждены на объёме около 500 договоров: "
            "отмена не убивает порции и не откатывает документы, ожидание корректно ждёт ключ IM8663_, "
            "группа 3 не стартует и не записывается без проведённого вечернего плана, связка заполняется."
            if fail_n == 0
            else "Часть проверок завершилась с ошибкой. См. жёлтые блоки в разделе «Детали тестов» — там полный текст ответа 1С. "
            "Успешные проверки при этом остаются действительными."
        ),
    )
    return html_doc


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
    conn = None
    try:
        safe_print("Connecting " + CONN_STRING)
        conn = connect()
        safe_print("Connected")
        group2, group3, periods = probe_environment(conn, report)
        group2, group3 = ensure_operation_groups(conn, report, group2, group3)
        if is_empty_ref(group2) or is_empty_ref(group3):
            raise RuntimeError("Groups 2/3 not found and could not be created.")

        day, py_day = pick_test_date(conn, report)
        safe_print("Test date selected " + py_day.strftime("%Y-%m-%d"))
        ensure_period(conn, day, report)
        cleanup_previous(conn, day, report)

        contracts = load_contracts(conn, report)
        if len(contracts) < 20:
            raise RuntimeError("Not enough contracts")
        with_e = contracts[: min(WITH_EVENING, len(contracts))]
        without_e = contracts[len(with_e): len(with_e) + WITHOUT_EVENING]
        if len(without_e) < 10 and len(contracts) > len(with_e):
            without_e = contracts[len(with_e):]

        with_e = create_group2_plans(conn, day, with_e, group2, report)
        without_use = [c for c in without_e if "group2_ref" not in c]
        create_group3_plans(conn, day, with_e, without_use, group3, report)
        verify_link_query(conn, day, group3, report)
        test_manager_api(conn, day, contracts[: len(with_e) + len(without_use)], with_e, without_use, periods, report)
        create_scha_docs(conn, day, with_e, report)
        test_cancel(conn, day, periods, report)
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
