#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Нагрузочный прогон выгрузок МО - ФО уровня 5 (мандаты и котировки).

Используются ОРИГИНАЛЬНЫЕ обработки МО: настоящий XDTO-пакет и настоящая
отправка в веб-сервис разработческой ФО (публикация http://localhost/win_fo).
Замеры: авто-ключи МО (Выгрузить/Опубликовать) и ключи приема ФО ОбменБэкОфис.*;
дополнительно python-время каждого вызова.

Запуск: python run_mo_load.py build|prepare|mandates|quotes (по одному шагу)
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "Тестирование", "stand"))
import stand_common as sc  # noqa: E402

BUILD = os.path.join(HERE, "build", "mo")
RESULT = os.path.join(HERE, "mo_load_run.json")
BUILD_SCRIPT = os.path.expanduser(r"~\.claude\skills\epf-build\scripts\epf-build.ps1")
FO_WSDL = "http://localhost/win_fo/ws/avancore_ws.1cws?wsdl"

MANDATES = 300
QUOTE_ROWS = 5000
QUOTE_ASSETS = 500

MO_SOURCES = {
    "внВыгрузкаСчетовМандатов_МО_ФО": "внВыгрузкаСчетовМандатов_МО_ФО_epf",
    "внВыгрузкаКотировокМО_ФО": "внВыгрузкаКотировокМО_ФО_epf",
}


def log(text):
    print("%s %s" % (datetime.datetime.now().strftime("%H:%M:%S"), text), flush=True)


def build():
    os.makedirs(BUILD, exist_ok=True)
    db = sc.registry_db("wim_mo")
    for name, folder in MO_SOURCES.items():
        xml = os.path.join(PROJECT, "ОРИГИНАЛЫ", "МО", folder, name + ".xml")
        out = os.path.join(BUILD, name + ".epf")
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", BUILD_SCRIPT,
               "-SourceFile", xml, "-OutputFile", out,
               "-InfoBaseServer", db["server"], "-InfoBaseRef", db["ref"], "-Checks", "off"]
        run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = os.path.exists(out) and "successfully" in (run.stdout or "")
        log("build %s %s" % (name, "OK" if ok else "FAIL"))
        if not ok:
            print((run.stdout or "")[-1500:])
            raise SystemExit(1)


def write_loaded(obj):
    obj.ОбменДанными.Загрузка = True
    # Данные стендовые: регистрация изменений на узлах обмена не нужна
    obj.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
    obj.Записать()
    return obj.Ссылка


def ensure_place(mo, catalog, code, name, extra):
    rows = sc.query_rows(
        mo, "ВЫБРАТЬ Сп.Ссылка КАК Ссылка ИЗ Справочник.%s КАК Сп ГДЕ Сп.КодМестаХранения = &Код" % catalog,
        {"Код": code})
    if rows:
        return rows[0]["Ссылка"]
    obj = getattr(mo.Справочники, catalog).СоздатьЭлемент()
    obj.Наименование = name
    obj.КодМестаХранения = code
    for attr, value in extra.items():
        setattr(obj, attr, value)
    log("MO place created %s" % code)
    return write_loaded(obj)


def prepare():
    mo = sc.connect("wim_mo")
    log("connected wim_mo")
    rub = sc.query_rows(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = &Код",
                        {"Код": "643"})[0]["Ссылка"]
    depo = ensure_place(mo, "СчетаДЕПО", "T5L5_DEPO", "T5L5 Depo", {})
    bank = ensure_place(mo, "БанковскиеСчета", "T5L5_BANK", "T5L5 Bank",
                        {"Валюта": rub, "НомерСчета": "T5L5BANK"})
    kinds = mo.ПланыВидовХарактеристик.ВидыСчетаМандата
    have = {row["Код"] for row in sc.query_rows(
        mo, "ВЫБРАТЬ М.КодМандата КАК Код ИЗ Справочник.Мандаты КАК М ГДЕ М.КодМандата ПОДОБНО &Маска",
        {"Маска": "T5L5_%"})}
    have_acc = {row["Код"] for row in sc.query_rows(
        mo, "ВЫБРАТЬ С.КодСчета КАК Код ИЗ Справочник.СчетаМандатов КАК С ГДЕ С.КодСчета ПОДОБНО &Маска",
        {"Маска": "T5L5_%"})}
    created = 0
    for number in range(1, MANDATES + 1):
        code = "T5L5_%04d" % number
        if code in have:
            ref = sc.query_rows(
                mo, "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.Мандаты КАК М ГДЕ М.КодМандата = &Код",
                {"Код": code})[0]["Ссылка"]
        else:
            obj = mo.Справочники.Мандаты.СоздатьЭлемент()
            obj.Наименование = "T5L5 Mandat %04d" % number
            obj.КодМандата = code
            obj.ТипМандата = mo.Перечисления.ТипыМандата.R
            obj.ВалютаМандата = rub
            ref = write_loaded(obj)
            created += 1
        for kind, place, account_kind in (("D", depo, kinds.Депозитарный), ("B", bank, kinds.Банковский)):
            acc_code = "%s_%s" % (code, kind)
            if acc_code in have_acc:
                continue
            acc = mo.Справочники.СчетаМандатов.СоздатьЭлемент()
            acc.Владелец = ref
            acc.Наименование = acc_code
            acc.КодСчета = acc_code
            acc.ВидСчетаМандата = account_kind
            acc.МестоХранения = place
            write_loaded(acc)
        if created and created % 50 == 0:
            log("mandates created %d" % created)
    log("mandates total new %d" % created)


def open_epf(conn, name):
    source = os.path.join(BUILD, name + ".epf")
    tmp = os.path.join(tempfile.gettempdir(), "t5l5_mo_" + name + ".epf")
    shutil.copyfile(source, tmp)
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    return conn.ВнешниеОбработки.Создать(tmp, False, protection)


def collect(conn, mask, since):
    rows = sc.query_rows(
        conn,
        "ВЫБРАТЬ Замеры.КлючеваяОперация.Имя КАК Ключ, Замеры.ВремяВыполнения КАК Секунды, "
        "Замеры.ВесЗамера КАК Вес, Замеры.Комментарий КАК Комментарий "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "ГДЕ Замеры.КлючеваяОперация.Имя ПОДОБНО &Маска И Замеры.ДатаЗаписиЛокальная >= &Начало "
        "УПОРЯДОЧИТЬ ПО Замеры.ДатаЗаписиЛокальная",
        {"Маска": mask, "Начало": since})
    return [{"key": r["Ключ"], "seconds": float(r["Секунды"]), "weight": float(r["Вес"]),
             "comment": str(r["Комментарий"] or "")[:300]} for r in rows]


def save(label, entry):
    results = {}
    if os.path.exists(RESULT):
        with open(RESULT, encoding="utf-8") as handle:
            results = json.load(handle)
    results[label] = entry
    with open(RESULT, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)
    log("saved " + RESULT)


def run_mandates():
    mo = sc.connect("wim_mo")
    fo = sc.connect("wim_fo")
    if not mo.Константы.ВыполнятьЗамерыПроизводительности.Получить():
        mo.Константы.ВыполнятьЗамерыПроизводительности.Установить(True)
        log("MO measurements turned ON for the run")
    mo_since = mo.ТекущаяДатаСеанса() - datetime.timedelta(seconds=10)
    fo_since = fo.ТекущаяДатаСеанса() - datetime.timedelta(seconds=10)
    epf = open_epf(mo, "внВыгрузкаСчетовМандатов_МО_ФО")
    epf.АдресWS = FO_WSDL
    epf.РозничноеДУ = False
    codes = mo.NewObject("Массив")
    for number in range(1, MANDATES + 1):
        codes.Добавить("T5L5_%04d" % number)
    mandates = sc.query_rows(
        mo, "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.Мандаты КАК М "
            "ГДЕ М.КодМандата В (&Коды) УПОРЯДОЧИТЬ ПО М.КодМандата", {"Коды": codes})
    for item in mandates:
        row = epf.Мандаты.Добавить()
        mo.ЗаполнитьЗначенияСвойств(row, item["Ссылка"])
        row.Ссылка = item["Ссылка"]
        row.Выгружать = True
    accounts = sc.query_rows(
        mo, "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Справочник.СчетаМандатов КАК С "
            "ГДЕ С.Владелец.КодМандата В (&Коды) УПОРЯДОЧИТЬ ПО С.КодСчета", {"Коды": codes})
    for item in accounts:
        row = epf.СчетаМандатов.Добавить()
        mo.ЗаполнитьЗначенияСвойств(row, item["Ссылка"])
        row.Ссылка = item["Ссылка"]
        row.Выгружать = True
    log("filled: мандатов %d, счетов %d" % (len(mandates), len(accounts)))

    entry = {"mandates": len(mandates), "accounts": len(accounts), "calls": [], "mo_rows": [], "fo_rows": []}
    for section in ("Мандаты", "СчетаМандатов"):
        started = time.perf_counter()
        error = ""
        try:
            epf.Выгрузить(section)
        except Exception as exc:  # noqa: BLE001 - ошибка узла в конце не отменяет отправку
            error = str(exc)[:600]
        elapsed = time.perf_counter() - started
        entry["calls"].append({"section": section, "python_seconds": round(elapsed, 2), "error": error})
        log("Выгрузить %s: %.1f с %s" % (section, elapsed, error[:150]))
    try:
        entry["log_tail"] = str(epf.ТекстовыйЛог.ПолучитьТекст())[-1500:]
    except Exception:
        entry["log_tail"] = ""
    entry["mo_rows"] = collect(mo, "внВыгрузкаСчетовМандатов%", mo_since)
    entry["fo_rows"] = collect(fo, "ОбменБэкОфис.%", fo_since)
    save("mandates", entry)
    for row in entry["mo_rows"] + entry["fo_rows"]:
        log("  %-60s %8.3f с  вес %6.0f" % (row["key"], row["seconds"], row["weight"]))


def run_quotes():
    mo = sc.connect("wim_mo")
    fo = sc.connect("wim_fo")
    mo_since = mo.ТекущаяДатаСеанса() - datetime.timedelta(seconds=10)
    fo_since = fo.ТекущаяДатаСеанса() - datetime.timedelta(seconds=10)
    external = sc.query_rows(
        mo, "ВЫБРАТЬ Сп.Ссылка КАК Ссылка ИЗ Справочник.ВнешниеИнформационныеБазы КАК Сп "
            "ГДЕ Сп.Наименование = &Имя", {"Имя": "T9532 ФО стенд"})[0]["Ссылка"]
    rub = sc.query_rows(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = &Код",
                        {"Код": "643"})[0]["Ссылка"]
    assets = sc.query_rows(
        mo, "ВЫБРАТЬ ПЕРВЫЕ %d А.Ссылка КАК Ссылка, А.ВнешнийКод КАК Код ИЗ Справочник.Активы КАК А "
            "ГДЕ А.ВнешнийКод <> \"\" И НЕ А.ПометкаУдаления УПОРЯДОЧИТЬ ПО А.ВнешнийКод" % QUOTE_ASSETS, {})
    log("assets %d" % len(assets))
    epf = open_epf(mo, "внВыгрузкаКотировокМО_ФО")
    epf.АдресWS = external
    today = mo.ТекущаяДатаСеанса()
    days = max(1, QUOTE_ROWS // max(len(assets), 1))
    added = 0
    for day in range(days):
        period = today - datetime.timedelta(days=day)
        for item in assets:
            if added >= QUOTE_ROWS:
                break
            row = epf.Котировки.Добавить()
            row.Период = period
            row.Актив = item["Ссылка"]
            row.Валюта = rub
            row.ВнешнийКод = item["Код"]
            row.РыночнаяЦена = 100
            added += 1
    log("filled quotes rows %d (assets %d x days %d)" % (added, len(assets), days))
    entry = {"rows": added, "calls": [], "mo_rows": [], "fo_rows": []}
    started = time.perf_counter()
    error = ""
    try:
        epf.Опубликовать()
    except Exception as exc:  # noqa: BLE001
        error = str(exc)[:600]
    elapsed = time.perf_counter() - started
    entry["calls"].append({"section": "Опубликовать", "python_seconds": round(elapsed, 2), "error": error})
    log("Опубликовать: %.1f с %s" % (elapsed, error[:150]))
    entry["mo_rows"] = collect(mo, "внВыгрузкаКотировокМО_ФО%", mo_since)
    entry["fo_rows"] = collect(fo, "ОбменБэкОфис.%", fo_since)
    save("quotes", entry)
    for row in entry["mo_rows"] + entry["fo_rows"]:
        log("  %-60s %8.3f с  вес %6.0f" % (row["key"], row["seconds"], row["weight"]))


def main():
    steps = {"build": build, "prepare": prepare, "mandates": run_mandates, "quotes": run_quotes}
    for arg in sys.argv[1:]:
        steps[arg]()


if __name__ == "__main__":
    main()
