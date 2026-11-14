#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Прогон замеров пяти задач уровня 5 и пять HTML-отчетов.

Внешние сервисы не вызываются: работают копии из каталога build.
"""

import datetime
import os
import shutil
import sys
import tempfile
import traceback

from stand_common import PREFIX, connect, load_state, query_rows, save_state

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(HERE, "build")
REPORTS = os.path.join(PROJECT, "Тестирование", "reports")

OCTOBER = {
    "mmvb": [
        ("Вся загрузка", "115,7", "141,1"),
        ("Чтение", "98,6", "110,2"),
        ("Запись", "13,7", "25,6"),
    ],
    "tcris": [
        ("Вся загрузка", "34,5", "32,0"),
        ("Чтение Rates", "0,3", "0,3"),
        ("Сопоставление", "0,6-1,0", "0,6-1,0"),
        ("Запись", "31,0-33,2", "31,0-33,2"),
    ],
    "indexes": [
        ("Вся загрузка", "10,5-10,9", "10,5-10,9"),
        ("Чтение", "5,3-5,4", "5,3-5,4"),
        ("Запись", "4,0-4,1", "4,0-4,1"),
    ],
}


def log(text):
    print(text, flush=True)


def open_epf(conn, filename):
    source = os.path.join(BUILD, filename)
    tmp = os.path.join(tempfile.gettempdir(), "t5l5_" + filename)
    shutil.copyfile(source, tmp)
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    epf = conn.ВнешниеОбработки.Создать(tmp, False, protection)
    return epf, tmp


def command_params(conn):
    params = conn.NewObject("Структура")
    empty = conn.Справочники.ДополнительныеОтчетыИОбработки.ПустаяСсылка()
    params.Вставить("ДополнительнаяОбработкаСсылка", empty)
    return params


def run_call(label, func):
    started = datetime.datetime.now()
    try:
        func()
        log("OK " + label)
        return {"label": label, "ok": True, "error": "", "started": started.isoformat(timespec="seconds")}
    except Exception as error:
        text = traceback.format_exc().splitlines()[-1][:500]
        log("FAIL " + label + " " + text)
        return {"label": label, "ok": False, "error": text, "started": started.isoformat(timespec="seconds")}


def fill_mandates(mo, epf):
    epf.РозничноеДУ = False
    codes = mo.NewObject("Массив")
    for index in range(1, 4):
        codes.Добавить("%s_%04d" % (PREFIX, index))
    mandates = query_rows(
        mo,
        "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.Мандаты КАК М "
        "ГДЕ М.КодМандата В (&Коды) УПОРЯДОЧИТЬ ПО М.КодМандата",
        {"Коды": codes},
    )
    for item in mandates:
        row = epf.Мандаты.Добавить()
        mo.ЗаполнитьЗначенияСвойств(row, item["Ссылка"])
        row.Ссылка = item["Ссылка"]
        row.Выгружать = True
    accounts = query_rows(
        mo,
        "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Справочник.СчетаМандатов КАК С "
        "ГДЕ С.Владелец.КодМандата В (&Коды) УПОРЯДОЧИТЬ ПО С.КодСчета",
        {"Коды": codes},
    )
    for item in accounts:
        row = epf.СчетаМандатов.Добавить()
        mo.ЗаполнитьЗначенияСвойств(row, item["Ссылка"])
        row.Ссылка = item["Ссылка"]
        row.Выгружать = True
    return len(mandates), len(accounts)


def fill_quotes(mo, epf):
    rub = query_rows(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = &Код", {"Код": "643"})
    currency = rub[0]["Ссылка"] if rub else None
    for index in range(1, 4):
        row = epf.Котировки.Добавить()
        row.ВнешнийКод = "%sQ%02d" % (PREFIX, index)
        row.РыночнаяЦена = 100 + index
        if currency is not None:
            row.Валюта = currency
    return epf.Котировки.Количество()


def ensure_measurements(conn, enabled):
    manager = getattr(conn.Константы, "ВыполнятьЗамерыПроизводительности")
    manager.Установить(enabled)


def make_packet(fo, section_name):
    factory = fo.ФабрикаXDTO
    ns = "http://avancore.ru/xsd"
    packet = factory.Создать(factory.Тип(ns, "Пакет"))
    header = factory.Создать(factory.Тип(ns, "Заголовок"))
    header.УникальныйИдентификатор = fo.String(fo.NewObject("УникальныйИдентификатор"))
    header.ДатаВыполнения = fo.ТекущаяДатаСеанса()
    header.ИдентификаторСистемы = "T5L5"
    header.ИмяПользователя = "Стенд"
    header.ДатаВыгрузки = fo.ТекущаяДатаСеанса()
    header.Комментарий = "Stand " + str(section_name)
    packet.Заголовок = header
    return packet


def load_packet(fo, with_directories):
    packet = make_packet(fo, with_directories)
    processor = fo.Обработки.ОбменДаннымиБэкОфис.Создать()
    processor.ЗагрузитьПакет(packet)


def max_stamp(conn):
    rows = query_rows(
        conn,
        "ВЫБРАТЬ МАКСИМУМ(Замеры.ДатаЗаписи) КАК ДатаЗаписи ИЗ РегистрСведений.ЗамерыВремени КАК Замеры",
    )
    if not rows or rows[0]["ДатаЗаписи"] is None:
        return ""
    return str(rows[0]["ДатаЗаписи"])


def latest_keys(conn, names, not_before):
    array = conn.NewObject("Массив")
    for name in names:
        array.Добавить(name)
    rows = query_rows(
        conn,
        "ВЫБРАТЬ Замеры.КлючеваяОперация.Имя КАК Имя, Замеры.ВремяВыполнения КАК Время, "
        "Замеры.ВесЗамера КАК Вес, Замеры.Комментарий КАК Комментарий, Замеры.ДатаЗаписи КАК ДатаЗаписи "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "ГДЕ Замеры.КлючеваяОперация.Имя В (&Имена)",
        {"Имена": array},
    )
    chosen = {}
    for row in rows:
        name = str(row["Имя"])
        stamp = str(row["ДатаЗаписи"])
        if not_before and stamp <= not_before:
            continue
        previous = chosen.get(name)
        if previous is None or stamp > previous["stamp"]:
            chosen[name] = {
                "name": name,
                "seconds": float(row["Время"]) if row["Время"] is not None else None,
                "weight": str(row["Вес"]),
                "comment": str(row["Комментарий"] or ""),
                "stamp": stamp,
            }
    return chosen


def task_status(keys, expected, call):
    missing = [name for name in expected if name not in keys]
    if call and not call["ok"] and missing:
        return "failed", missing
    if missing:
        return "failed", missing
    return "ok", []


def html_page(title, intro, rows, october, improvement, prefix_note, failed):
    status = "Неуспех" if failed else "Успех"
    color = "#dc3545" if failed else "#28a745"
    body_rows = []
    for row in rows:
        seconds = "" if row["seconds"] is None else ("%.3f" % row["seconds"])
        body_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (row["name"], seconds, row["weight"], row["comment"])
        )
    if not body_rows:
        body_rows.append("<tr><td colspan='4'>Ключи этого прогона не записаны</td></tr>")
    october_rows = []
    for step, retail, ordinary in october:
        october_rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (step, retail, ordinary))
    if not october_rows:
        october_rows.append("<tr><td colspan='3'>Октябрьских строк на проде нет</td></tr>")
    return """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>%s</title>
<style>
body { font-family: Segoe UI, sans-serif; margin: 24px; color: #222; }
h1 { font-size: 22px; }
.badge { display: inline-block; color: #fff; background: %s; padding: 4px 10px; border-radius: 4px; }
table { border-collapse: collapse; width: 100%%; margin: 12px 0 24px; }
th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #17a2b8; color: #fff; }
.note { background: #fff3cd; padding: 12px; margin: 12px 0; }
.info { background: #e7f5ff; padding: 12px; margin: 12px 0; }
</style></head><body>
<h1>%s</h1>
<p><span class="badge">%s</span></p>
<p>%s</p>
<div class="info">Длительности стенда - это проверка пути после снятия внешнего вызова. Это не время прода.</div>
<h2>Стенд</h2>
<table><tr><th>Ключ</th><th>Секунды</th><th>Вес</th><th>Комментарий</th></tr>
%s
</table>
<h2>Профиль прода, 16.10-02.11.2026, среднее</h2>
<table><tr><th>Шаг</th><th>Розница, с</th><th>Обычный ФО, с</th></tr>
%s
</table>
<div class="note"><b>Место к доработке.</b> %s</div>
<p>%s</p>
</body></html>
""" % (title, color, title, status, intro, "\n".join(body_rows), "\n".join(october_rows), improvement, prefix_note)


def write_reports(result):
    os.makedirs(REPORTS, exist_ok=True)
    prefix_note = "Элементы стенда имеют префикс %s. Учетные данные Rates в отчет не входят." % PREFIX
    pages = [
        ("mmvb-quotes.html", "Котировки ММВБ", result["mmvb"], OCTOBER["mmvb"],
         "Чтение на проде смешивает сервис котировок, разбор ответа и построчный лог. На стенде сервис заменен локальными строками, поэтому секунды стенда не делят эти три части."),
        ("indexes.html", "Индексы", result["indexes"], OCTOBER["indexes"],
         "10-11 секунд раз в день укладываются в окно. Отдельную оптимизацию по октябрьскому профилю не выделяем."),
        ("tcris.html", "TCRIS", result["tcris"], OCTOBER["tcris"],
         "На проде около 96 процентов времени сидит в записи: значение пишется каждому сопоставленному контрагенту каждый день. На стенде записан один контрагент."),
        ("mo-mandates.html", "Мандаты МО-ФО", result["mandates"], [],
         "Октябрьского профиля нет. На стенде видны выгрузка из МО без публикации и прием пакета на ФО."),
        ("mo-quotes.html", "Котировки МО-ФО", result["quotes"], [],
         "Октябрьского профиля нет. На стенде видны публикация из МО без веб-сервиса и прием пакета на ФО."),
    ]
    for filename, title, block, october, improvement in pages:
        path = os.path.join(REPORTS, filename)
        text = html_page(title, block.get("intro", "") + " " + block.get("error", ""), block.get("rows", []), october, improvement, prefix_note, block.get("status") != "ok")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        log("report " + filename)


def rows_for(found, names):
    rows = []
    for name in names:
        if name in found:
            rows.append(found[name])
    return rows


def restore_constants():
    state = load_state()
    for base_id, info in state.get("bases", {}).items():
        conn = connect(base_id)
        manager = getattr(conn.Константы, "ВыполнятьЗамерыПроизводительности")
        manager.Установить(bool(info.get("constant_was_on")))
        log("constant restored %s was_on=%s" % (base_id, info.get("constant_was_on")))


def main():
    calls = []
    fo = connect("wim_fo")
    fo_before = max_stamp(fo)
    ensure_measurements(fo, True)
    params = command_params(fo)

    def mmvb():
        epf, tmp = open_epf(fo, "внЗагрузкаКотировокММВБ.epf")
        try:
            epf.ВыполнитьКоманду("ФоновоеВыполнение", params)
        finally:
            os.remove(tmp)

    def indexes():
        epf, tmp = open_epf(fo, "внЗагрузкаИндексовФО.epf")
        try:
            epf.ВыполнитьКоманду("ФоновоеВыполнение", params)
        finally:
            os.remove(tmp)

    def tcris():
        epf, tmp = open_epf(fo, "ЗагрузкаДопРеквизитаTCRIS.epf")
        try:
            epf.ВыполнитьКоманду("ФоновоеВыполнение", params)
        finally:
            os.remove(tmp)

    calls.append(run_call("mmvb", mmvb))
    calls.append(run_call("indexes", indexes))
    calls.append(run_call("tcris", tcris))

    mo = connect("wim_mo")
    mo_before = max_stamp(mo)
    ensure_measurements(mo, True)

    def mandates():
        epf, tmp = open_epf(mo, "внВыгрузкаСчетовМандатов_МО_ФО.epf")
        try:
            fill_mandates(mo, epf)
            epf.Выгрузить("Мандаты")
            epf.Выгрузить("СчетаМандатов")
        finally:
            os.remove(tmp)

    def quotes():
        epf, tmp = open_epf(mo, "внВыгрузкаКотировокМО_ФО.epf")
        try:
            fill_quotes(mo, epf)
            epf.Опубликовать()
        finally:
            os.remove(tmp)

    calls.append(run_call("mandates", mandates))
    calls.append(run_call("quotes", quotes))

    receive_note = ""
    def receive_directories():
        load_packet(fo, True)

    def receive_quotes():
        load_packet(fo, False)

    calls.append(run_call("receive-directories", receive_directories))
    calls.append(run_call("receive-quotes", receive_quotes))

    fo_names = [
        "ЗагрузкаКотировокММВБ", "ЗагрузкаКотировокММВБ.Чтение", "ЗагрузкаКотировокММВБ.Запись",
        "ЗагрузкаИндексов", "ЗагрузкаИндексов.Чтение", "ЗагрузкаИндексов.Запись",
        "ЗагрузкаTCRIS", "ЗагрузкаTCRIS.ЧтениеRates", "ЗагрузкаTCRIS.Сопоставление", "ЗагрузкаTCRIS.Запись",
    ]
    mo_names = [
        "внВыгрузкаСчетовМандатов_МО_ФО_Выгрузить_Мандаты_Сервер",
        "внВыгрузкаСчетовМандатов_МО_ФО_Выгрузить_СчетаМандатов_Сервер",
        "внВыгрузкаКотировокМО_ФО_Опубликовать_Сервер",
    ]
    fo_found = latest_keys(fo, fo_names, fo_before)
    exchange = latest_keys(fo, ["ОбменБэкОфис.Пакет"], fo_before)
    extra = query_rows(
        fo,
        "ВЫБРАТЬ Замеры.КлючеваяОперация.Имя КАК Имя, Замеры.ВремяВыполнения КАК Время, "
        "Замеры.ВесЗамера КАК Вес, Замеры.Комментарий КАК Комментарий, Замеры.ДатаЗаписи КАК ДатаЗаписи "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "ГДЕ Замеры.КлючеваяОперация.Имя ПОДОБНО &Маска",
        {"Маска": "ОбменБэкОфис.%"},
    )
    for row in extra:
        name = str(row["Имя"])
        stamp = str(row["ДатаЗаписи"])
        if fo_before and stamp <= fo_before:
            continue
        previous = exchange.get(name)
        if previous is None or stamp > previous["stamp"]:
            exchange[name] = {
                "name": name,
                "seconds": float(row["Время"]) if row["Время"] is not None else None,
                "weight": str(row["Вес"]),
                "comment": str(row["Комментарий"] or ""),
                "stamp": stamp,
            }
    mo_found = latest_keys(mo, mo_names, mo_before)

    def block(title, names, found, call_name, intro):
        call = next(item for item in calls if item["label"] == call_name)
        status, missing = task_status(found, names, call)
        return {
            "status": status,
            "missing": missing,
            "intro": intro,
            "rows": rows_for(found, list(found.keys()) if not names else names),
            "error": call["error"],
        }

    result = {
        "calls": calls,
        "receive_note": receive_note,
        "mmvb": block("mmvb", ["ЗагрузкаКотировокММВБ", "ЗагрузкаКотировокММВБ.Чтение", "ЗагрузкаКотировокММВБ.Запись"], fo_found, "mmvb", "Проверка пути загрузки котировок ММВБ на локальных строках."),
        "indexes": block("indexes", ["ЗагрузкаИндексов", "ЗагрузкаИндексов.Чтение", "ЗагрузкаИндексов.Запись"], fo_found, "indexes", "Проверка пути загрузки индексов на коротком ответе."),
        "tcris": block("tcris", ["ЗагрузкаTCRIS", "ЗагрузкаTCRIS.ЧтениеRates", "ЗагрузкаTCRIS.Сопоставление", "ЗагрузкаTCRIS.Запись"], fo_found, "tcris", "Проверка пути TCRIS на одной строке рейтинга."),
        "mandates": {
            "status": "ok",
            "intro": "Выгрузка мандатов из МО и прием пакета на ФО.",
            "rows": rows_for(mo_found, [
                "внВыгрузкаСчетовМандатов_МО_ФО_Выгрузить_Мандаты_Сервер",
                "внВыгрузкаСчетовМандатов_МО_ФО_Выгрузить_СчетаМандатов_Сервер",
            ]) + [item for name, item in exchange.items() if "Справочники" in name or name == "ОбменБэкОфис.Пакет"],
            "error": "",
        },
        "quotes": {
            "status": "ok",
            "intro": "Выгрузка котировок из МО и прием пакета на ФО.",
            "rows": rows_for(mo_found, ["внВыгрузкаКотировокМО_ФО_Опубликовать_Сервер"]) + [item for name, item in exchange.items() if "Документы" in name or name == "ОбменБэкОфис.Пакет"],
            "error": "",
        },
    }
    for key, names, found, label in (
        ("mandates", [
            "внВыгрузкаСчетовМандатов_МО_ФО_Выгрузить_Мандаты_Сервер",
            "внВыгрузкаСчетовМандатов_МО_ФО_Выгрузить_СчетаМандатов_Сервер",
        ], mo_found, "mandates"),
        ("quotes", ["внВыгрузкаКотировокМО_ФО_Опубликовать_Сервер"], mo_found, "quotes"),
    ):
        status, missing = task_status(found, names, next(item for item in calls if item["label"] == label))
        result[key]["status"] = status
        result[key]["missing"] = missing
        result[key]["error"] = next(item for item in calls if item["label"] == label)["error"]
    save_state_run(result)
    write_reports(result)
    restore_constants()
    log("DONE")
    return 0


def save_state_run(result):
    path = os.path.join(HERE, "last_run.json")
    import json
    payload = {}
    for key in ("mmvb", "indexes", "tcris", "mandates", "quotes"):
        block = result[key]
        payload[key] = {
            "status": block["status"],
            "missing": block.get("missing", []),
            "error": block.get("error", ""),
            "keys": [row["name"] for row in block.get("rows", [])],
        }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
