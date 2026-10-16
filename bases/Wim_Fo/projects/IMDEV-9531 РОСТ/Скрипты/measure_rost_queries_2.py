#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Второй проход замеров РОСТ: даты позиции, срезы остатков и методы отбора обработки.

Только чтение. Создание поручений и отправка не вызываются.
"""

import json
import os
import tempfile
import time
import traceback

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Тестирование",
    "reports",
    "measure_rost_raw2.json",
)


def safe_print(text):
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"), flush=True)


def save(payload):
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)


def as_text(conn, value):
    if value is None:
        return ""
    try:
        return str(conn.String(value))
    except Exception:
        try:
            return str(value)
        except Exception:
            return ""


def query_rows(conn, text, fields, params=None, limit=50):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for name, value in params.items():
            query.УстановитьПараметр(name, value)
    started = time.perf_counter()
    selection = query.Выполнить().Выбрать()
    elapsed = time.perf_counter() - started
    rows = []
    while selection.Следующий() and len(rows) < limit:
        row = {}
        for field in fields:
            value = getattr(selection, field)
            if field in ("Кво", "Количество"):
                row[field] = int(value)
            else:
                row[field] = as_text(conn, value)
        rows.append(row)
    return round(elapsed, 3), rows


def main():
    payload = {"base": "WIN_FO_server", "mode": "read_only", "steps": []}
    save(payload)
    pythoncom.CoInitialize()
    safe_print("connect")
    started = time.perf_counter()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    payload["connect_sec"] = round(time.perf_counter() - started, 3)
    try:
        payload["session_date"] = as_text(conn, conn.ТекущаяДатаСеанса())
    except Exception as error:
        payload["session_date_error"] = str(error)[:300]
    save(payload)
    safe_print("connected")

    def step(name, func):
        safe_print("step " + name)
        started_step = time.perf_counter()
        try:
            info = func()
            info["name"] = name
            info["ok"] = True
            info["wall_sec"] = round(time.perf_counter() - started_step, 3)
            payload["steps"].append(info)
            save(payload)
            safe_print("ok " + name)
        except Exception as error:
            payload["steps"].append({
                "name": name,
                "ok": False,
                "error": str(error)[:1500],
                "trace": traceback.format_exc()[-2500:],
                "wall_sec": round(time.perf_counter() - started_step, 3),
            })
            save(payload)
            safe_print("ERR " + name + " " + str(error)[:250])

    holder = {}

    def dates():
        sec, rows = query_rows(
            conn,
            "ВЫБРАТЬ МАКСИМУМ(т.Дата) КАК МаксФакт, МИНИМУМ(т.Дата) КАК МинФакт, "
            "КОЛИЧЕСТВО(РАЗЛИЧНЫЕ т.Дата) КАК Кво "
            "ИЗ РегистрСведений.ФактическаяПозиция КАК т",
            ["МаксФакт", "МинФакт", "Кво"],
        )
        holder["max_fact_text"] = rows[0]["МаксФакт"]
        return {"sec": sec, "rows": rows}

    step("fact_span", dates)

    def fact_dates():
        sec, rows = query_rows(
            conn,
            "ВЫБРАТЬ т.Дата КАК Дата, КОЛИЧЕСТВО(*) КАК Кво "
            "ИЗ РегистрСведений.ФактическаяПозиция КАК т "
            "СГРУППИРОВАТЬ ПО т.Дата УПОРЯДОЧИТЬ ПО Дата УБЫВ",
            ["Дата", "Кво"],
            limit=15,
        )
        return {"sec": sec, "rows": rows}

    step("fact_by_date", fact_dates)

    def load_max_date():
        query = conn.NewObject("Запрос")
        query.Текст = "ВЫБРАТЬ МАКСИМУМ(т.Дата) КАК МаксФакт ИЗ РегистрСведений.ФактическаяПозиция КАК т"
        selection = query.Выполнить().Выбрать()
        selection.Следующий()
        holder["max_fact"] = selection.МаксФакт
        query2 = conn.NewObject("Запрос")
        query2.Текст = "ВЫБРАТЬ КОНЕЦПЕРИОДА(МАКСИМУМ(т.Дата), ДЕНЬ) КАК КонецДня ИЗ РегистрСведений.ФактическаяПозиция КАК т"
        selection2 = query2.Выполнить().Выбрать()
        selection2.Следующий()
        holder["max_fact_end"] = selection2.КонецДня
        return {"sec": 0, "max": as_text(conn, holder["max_fact"])}

    step("bind_dates", load_max_date)

    def virtual(name, text):
        def _run():
            sec, rows = query_rows(conn, text, ["Кво"], {"Дата": holder["max_fact_end"]})
            return {"sec": sec, "count": rows[0]["Кво"] if rows else None}
        step(name, _run)

    virtual(
        "vt_plan_currency",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПлановаяПозиция.Остатки(&Дата, "
        "Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т",
    )
    virtual(
        "vt_forecast_currency",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПрогнозПоПоручению.Остатки(&Дата, "
        "Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т",
    )
    virtual(
        "vt_plan_securities",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПлановаяПозиция.Остатки(&Дата, "
        "Актив.ВидАктива <> ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т",
    )
    virtual(
        "vt_scha",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.РегистрРСА_СЧА.СрезПоследних(&Дата, ) КАК т",
    )
    virtual(
        "fact_bonds",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.ФактическаяПозиция КАК т "
        "ГДЕ т.Дата = НАЧАЛОПЕРИОДА(&Дата, ДЕНЬ) И т.Актив.Объект ССЫЛКА Справочник.Облигации",
    )

    def open_processor():
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ т.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК т "
            "ГДЕ т.ИмяОбъекта = &Имя И НЕ т.ПометкаУдаления"
        )
        query.УстановитьПараметр("Имя", "СозданиеТорговыхПорученийРОСТ")
        selection = query.Выполнить().Выбрать()
        if not selection.Следующий():
            raise RuntimeError("processing not found")
        item = selection.Ссылка.ПолучитьОбъект()
        binary = item.ХранилищеОбработки.Получить()
        path = os.path.join(tempfile.gettempdir(), "rost_measure_readonly.epf")
        binary.Записать(path)
        processor = conn.ВнешниеОбработки.Создать(path, False)
        storage = item.ХранилищеНастроек.Получить()
        title = ""
        processor.УстановитьПользовательскиеНастройки(storage, title)
        holder["processor"] = processor
        strategies = int(processor.НастройкаСтратегий.Количество())
        return {
            "sec": 0,
            "version": as_text(conn, item.Версия),
            "strategies": strategies,
            "search_status": as_text(conn, processor.СтатусДляПоиска),
            "transfer_status": as_text(conn, processor.СтатусДляПеревода),
            "liquidity": as_text(conn, processor.АктивВимЛиквидность),
            "test_flag": as_text(conn, processor.ЭтоТест),
            "close_price_control": as_text(conn, processor.КонтрольПоЦенеЗакрытия),
            "epf": path,
        }

    step("open_processor", open_processor)

    def time_call(name, func):
        def _run():
            started_call = time.perf_counter()
            extra = func()
            extra["sec"] = round(time.perf_counter() - started_call, 3)
            return extra
        step(name, _run)

    def buy_list():
        processor = holder["processor"]
        processor.ОбновитьСписокПортфелейПокупка("", 0)
        return {"rows": int(processor.СписокПортфелейПокупка.Количество())}

    def sell_list():
        processor = holder["processor"]
        processor.ЗаполнитьСписокПродажаАктивов(True, "", 0)
        return {"rows": int(processor.СписокПортфелейПродажа.Количество())}

    def reinvest_list():
        processor = holder["processor"]
        processor.РеинвестОбновитьСписокПотфелей(holder["max_fact"], True, 0, 0, "", 0)
        return {"rows": int(processor.СписокПортфелейРеинвестирование.Количество()), "coupon_date": as_text(conn, holder["max_fact"])}

    def block_list():
        processor = holder["processor"]
        processor.БлокировкиПродажиОбновитьСписокПотфелей("LQDT", True, "", 0)
        return {"rows": int(processor.СписокПортфелейПродажиПодБлокировки.Количество())}

    def ofz_flow():
        processor = holder["processor"]
        started_call = time.perf_counter()
        processor.РассчитатьПотокПоОФЗ(holder["max_fact"])
        return {"sec": round(time.perf_counter() - started_call, 3), "log_len": len(as_text(conn, processor.Лог.ПолучитьТекст()))}

    time_call("buy_list", buy_list)
    time_call("sell_list", sell_list)
    time_call("reinvest_list", reinvest_list)
    time_call("block_list", block_list)
    step("ofz_flow", ofz_flow)

    def status_values():
        processor = holder["processor"]
        sec, rows = query_rows(
            conn,
            "ВЫБРАТЬ т.Значение КАК Статус, КОЛИЧЕСТВО(*) КАК Кво "
            "ИЗ РегистрСведений.ДополнительныеСведения КАК т "
            "ГДЕ т.Свойство = &Свойство "
            "СГРУППИРОВАТЬ ПО т.Значение УПОРЯДОЧИТЬ ПО Кво УБЫВ",
            ["Статус", "Кво"],
            {"Свойство": processor.ДопРеквизитСтатусПортфеля},
            limit=20,
        )
        return {"sec": sec, "rows": rows}

    step("status_values", status_values)

    def orders_span():
        sec, rows = query_rows(
            conn,
            "ВЫБРАТЬ МИНИМУМ(т.Дата) КАК МинДата, МАКСИМУМ(т.Дата) КАК МаксДата, КОЛИЧЕСТВО(*) КАК Кво "
            "ИЗ Документ.Поручение КАК т ГДЕ т.Проведен",
            ["МинДата", "МаксДата", "Кво"],
        )
        return {"sec": sec, "rows": rows}

    step("orders_span", orders_span)

    def measures():
        sec, rows = query_rows(
            conn,
            "ВЫБРАТЬ ПЕРВЫЕ 20 Замеры.КлючеваяОперация.Наименование КАК Имя, "
            "СУММА(Замеры.ВремяВыполнения) КАК Секунды, КОЛИЧЕСТВО(*) КАК Кво "
            "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
            "СГРУППИРОВАТЬ ПО Замеры.КлючеваяОперация.Наименование "
            "УПОРЯДОЧИТЬ ПО Секунды УБЫВ",
            ["Имя", "Секунды", "Кво"],
            limit=20,
        )
        return {"sec": sec, "rows": rows}

    step("measures", measures)

    safe_print("done")
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
