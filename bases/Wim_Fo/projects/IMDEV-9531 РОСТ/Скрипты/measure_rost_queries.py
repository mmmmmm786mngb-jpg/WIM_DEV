#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Замеры чтения по обработке "Создание торговых поручений РОСТ" в разработческой базе ФО.

Скрипт только выполняет запросы. Документы не создает, статусы не меняет, на биржу ничего не отправляет.
Результат пишется в JSON после каждого шага.
"""

import json
import os
import time
import traceback

import pythoncom
import win32com.client

CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Тестирование",
    "reports",
    "measure_rost_raw.json",
)

SECRET_KEYS = ("пароль", "логин", "password", "pwd")
PROCESSING_REFS = []


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
        return str(value)


def run_select(conn, text, params=None):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for name, value in params.items():
            query.УстановитьПараметр(name, value)
    started = time.perf_counter()
    result = query.Выполнить()
    selection = result.Выбрать()
    rows = []
    while selection.Следующий():
        row = {}
        # Колонки результата недоступны единообразно через COM, читаем известные поля из текста не здесь.
        rows.append(selection)
        break
    elapsed = time.perf_counter() - started
    return elapsed, selection, result


def timed_unload(conn, text, params=None, max_rows_note=True):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for name, value in params.items():
            query.УстановитьПараметр(name, value)
    started = time.perf_counter()
    table = query.Выполнить().Выгрузить()
    elapsed = time.perf_counter() - started
    count = int(table.Количество())
    return elapsed, count


def first_row_map(conn, text, fields, params=None):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for name, value in params.items():
            query.УстановитьПараметр(name, value)
    started = time.perf_counter()
    selection = query.Выполнить().Выбрать()
    elapsed = time.perf_counter() - started
    data = {}
    if selection.Следующий():
        for field in fields:
            data[field] = getattr(selection, field)
    return elapsed, data


def main():
    payload = {
        "base": "WIN_FO_server",
        "connection": "Srvr=localhost;Ref=WIN_FO_server;Usr=admin;App=PyCOM;Locale=ru_RU",
        "mode": "read_only",
        "steps": [],
        "errors": [],
    }
    save(payload)

    pythoncom.CoInitialize()
    safe_print("connect")
    started = time.perf_counter()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    payload["connect_sec"] = round(time.perf_counter() - started, 3)
    payload["metadata_name"] = as_text(conn, conn.Метаданные.Имя)
    payload["metadata_version"] = as_text(conn, conn.Метаданные.Версия)
    save(payload)
    safe_print("connected " + payload["metadata_name"] + " " + payload["metadata_version"])

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
            safe_print("ok " + name + " " + str(info.get("sec", info["wall_sec"])))
        except Exception as error:
            text = traceback.format_exc()
            payload["errors"].append({"name": name, "error": str(error), "trace": text[-4000:]})
            payload["steps"].append({
                "name": name,
                "ok": False,
                "error": str(error),
                "wall_sec": round(time.perf_counter() - started_step, 3),
            })
            save(payload)
            safe_print("ERR " + name + " " + str(error)[:300])

    def count_query(title, text, params=None):
        def _run():
            elapsed, data = first_row_map(conn, text, ["Кво"], params)
            return {"title": title, "sec": round(elapsed, 3), "count": int(data.get("Кво", 0))}
        step(title, _run)

    count_query("cnt_orders", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ Документ.Поручение КАК т")
    count_query("cnt_orders_posted", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ Документ.Поручение КАК т ГДЕ т.Проведен")
    count_query("cnt_fact", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.ФактическаяПозиция КАК т")
    count_query("cnt_extra", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.ДополнительныеСведения КАК т")
    count_query("cnt_plan_turn", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПлановаяПозиция КАК т")
    count_query("cnt_forecast_turn", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПрогнозПоПоручению КАК т")
    count_query("cnt_scha", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.РегистрРСА_СЧА КАК т")
    count_query("cnt_coupons", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.КупонноеРасписаниеПоОблигациям КАК т")
    count_query("cnt_statuses", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.СтатусыПоручений КАК т")
    count_query("cnt_quotes", "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.КотировкиЦБНаБирже КАК т")

    dates = {}

    def load_dates():
        elapsed, data = first_row_map(
            conn,
            "ВЫБРАТЬ МАКСИМУМ(т.Дата) КАК МаксФакт, "
            "НАЧАЛОПЕРИОДА(ТекущаяДатаСеанса(), ДЕНЬ) КАК Сегодня, "
            "КОНЕЦПЕРИОДА(ТекущаяДатаСеанса(), ДЕНЬ) КАК КонецСегодня "
            "ИЗ РегистрСведений.ФактическаяПозиция КАК т",
            ["МаксФакт", "Сегодня", "КонецСегодня"],
        )
        dates["max_fact"] = data["МаксФакт"]
        dates["today"] = data["Сегодня"]
        dates["today_end"] = data["КонецСегодня"]
        return {
            "sec": round(elapsed, 3),
            "max_fact": as_text(conn, data["МаксФакт"]),
            "today": as_text(conn, data["Сегодня"]),
        }

    step("dates", load_dates)

    def orders_by_day():
        text = (
            "ВЫБРАТЬ НАЧАЛОПЕРИОДА(т.Дата, ДЕНЬ) КАК День, КОЛИЧЕСТВО(*) КАК Кво "
            "ИЗ Документ.Поручение КАК т "
            "ГДЕ т.Дата >= ДОБАВИТЬКДАТЕ(&Макс, ДЕНЬ, -40) И т.Проведен "
            "СГРУППИРОВАТЬ ПО НАЧАЛОПЕРИОДА(т.Дата, ДЕНЬ) "
            "УПОРЯДОЧИТЬ ПО День УБЫВ"
        )
        query = conn.NewObject("Запрос")
        query.Текст = text
        query.УстановитьПараметр("Макс", dates["max_fact"])
        started_q = time.perf_counter()
        selection = query.Выполнить().Выбрать()
        rows = []
        while selection.Следующий() and len(rows) < 25:
            rows.append({"day": as_text(conn, selection.День), "count": int(selection.Кво)})
        return {"sec": round(time.perf_counter() - started_q, 3), "rows": rows}

    step("orders_by_day", orders_by_day)

    def top_properties():
        text = (
            "ВЫБРАТЬ ПЕРВЫЕ 25 т.Свойство.Наименование КАК Имя, КОЛИЧЕСТВО(*) КАК Кво "
            "ИЗ РегистрСведений.ДополнительныеСведения КАК т "
            "СГРУППИРОВАТЬ ПО т.Свойство.Наименование "
            "УПОРЯДОЧИТЬ ПО Кво УБЫВ"
        )
        query = conn.NewObject("Запрос")
        query.Текст = text
        started_q = time.perf_counter()
        selection = query.Выполнить().Выбрать()
        rows = []
        while selection.Следующий():
            rows.append({"name": as_text(conn, selection.Имя), "count": int(selection.Кво)})
        return {"sec": round(time.perf_counter() - started_q, 3), "rows": rows}

    step("top_properties", top_properties)

    def find_processing():
        text = (
            "ВЫБРАТЬ т.Наименование КАК Имя, т.ИмяОбъекта КАК Объект, т.Версия КАК Версия, т.Ссылка КАК Ссылка "
            "ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК т "
            "ГДЕ т.Наименование ПОДОБНО \"%РОСТ%\" ИЛИ т.ИмяОбъекта ПОДОБНО \"%РОСТ%\""
        )
        query = conn.NewObject("Запрос")
        query.Текст = text
        started_q = time.perf_counter()
        selection = query.Выполнить().Выбрать()
        rows = []
        refs = []
        while selection.Следующий():
            rows.append({
                "name": as_text(conn, selection.Имя),
                "object": as_text(conn, selection.Объект),
                "version": as_text(conn, selection.Версия),
            })
            refs.append(selection.Ссылка)
        PROCESSING_REFS[:] = refs
        return {"sec": round(time.perf_counter() - started_q, 3), "rows": rows, "count": len(refs)}

    step("find_processing", find_processing)

    settings_bag = {}

    def read_settings():
        refs = PROCESSING_REFS
        if not refs:
            return {"sec": 0, "note": "processing not found"}
        chosen = None
        for ref in refs:
            obj = ref.ПолучитьОбъект()
            name = as_text(conn, obj.Наименование)
            if "Создание торговых" in name or "торговых поручений" in name.lower():
                chosen = obj
                break
        if chosen is None:
            chosen = refs[0].ПолучитьОбъект()
        storage = chosen.ХранилищеНастроек
        settings = storage.Получить()
        keys = [
            "ДопРеквизитСтатусПортфеля",
            "ДопРеквизитДатаОперации",
            "СтатусДляПоиска",
            "СтатусДляПеревода",
            "АктивВимЛиквидность",
            "КонтрольПоЦенеЗакрытия",
            "ВыключитьПокупки",
            "ВыключитьПродажи",
            "ПроцентКомиссияБрокер",
            "НастройкаСтратегий",
        ]
        readable = {}
        for key in keys:
            try:
                value = getattr(settings, key)
                settings_bag[key] = value
                if key == "НастройкаСтратегий":
                    readable[key] = "xml_len=" + str(len(as_text(conn, value)))
                else:
                    readable[key] = as_text(conn, value)[:200]
            except Exception as error:
                readable[key] = "ERR " + str(error)[:200]
        payload["settings_preview"] = readable
        return {"sec": 0, "keys": readable}

    step("read_settings", read_settings)

    def virtual_count(title, text, params):
        def _run():
            elapsed, data = first_row_map(conn, text, ["Кво"], params)
            return {"title": title, "sec": round(elapsed, 3), "count": int(data.get("Кво", 0))}
        step(title, _run)

    fact_date = dates["max_fact"]
    period_end = dates["today_end"]

    virtual_count(
        "vt_plan_currency",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПлановаяПозиция.Остатки(&Дата, "
        "Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т",
        {"Дата": period_end},
    )
    virtual_count(
        "vt_forecast_currency",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПрогнозПоПоручению.Остатки(&Дата, "
        "Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т",
        {"Дата": period_end},
    )
    virtual_count(
        "vt_forecast_withdraw",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПрогнозПоПоручению.Остатки(&Дата, "
        "Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты) "
        "И Поручение.ВидОперацииНеторговогоПоручения = ЗНАЧЕНИЕ(Перечисление.ВидыОперацийНеторговыхПоручений.Вывод)) КАК т",
        {"Дата": period_end},
    )
    virtual_count(
        "vt_plan_non_currency",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрНакопления.ПлановаяПозиция.Остатки(&Дата, "
        "Актив.ВидАктива <> ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т",
        {"Дата": period_end},
    )
    virtual_count(
        "vt_scha_slice",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.РегистрРСА_СЧА.СрезПоследних(&Дата, ) КАК т",
        {"Дата": period_end},
    )
    virtual_count(
        "fact_bonds_on_max_date",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.ФактическаяПозиция КАК т "
        "ГДЕ т.Дата = &Дата И т.Актив.Объект ССЫЛКА Справочник.Облигации",
        {"Дата": fact_date},
    )
    virtual_count(
        "fact_currency_on_max_date",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.ФактическаяПозиция КАК т "
        "ГДЕ т.Дата = &Дата И т.Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)",
        {"Дата": fact_date},
    )
    virtual_count(
        "fact_all_on_max_date",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.ФактическаяПозиция КАК т ГДЕ т.Дата = &Дата",
        {"Дата": fact_date},
    )

    def coupon_join():
        text = (
            "ВЫБРАТЬ т.Актив.Объект КАК Облигация, т.Количество КАК Количество "
            "ПОМЕСТИТЬ втАктивы ИЗ РегистрСведений.ФактическаяПозиция КАК т "
            "ГДЕ т.Дата = &Дата И т.Актив.Объект ССЫЛКА Справочник.Облигации; "
            "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ втАктивы КАК втАктивы "
            "ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.КупонноеРасписаниеПоОблигациям.СрезПоследних("
            "КОНЕЦПЕРИОДА(&ДатаКупона, ДЕНЬ), Облигация В (ВЫБРАТЬ т.Облигация ИЗ втАктивы КАК т)) КАК с "
            "ПО втАктивы.Облигация = с.Облигация "
            "ЛЕВОЕ СОЕДИНЕНИЕ Документ.КупонноеРасписание.Купоны КАК к "
            "ПО с.Документ = к.Ссылка И к.ДатаВыплатыКупонногоДохода = &ДатаКупона "
            "ГДЕ ЕСТЬNULL(к.РазмерДоходаВРублях, 0) > 0"
        )
        elapsed, data = first_row_map(conn, text, ["Кво"], {"Дата": fact_date, "ДатаКупона": fact_date})
        return {"sec": round(elapsed, 3), "rows_with_coupon": int(data.get("Кво", 0)), "coupon_date": as_text(conn, fact_date)}

    step("coupon_join_on_fact_date", coupon_join)

    def close_price_sample():
        text = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 т.Актив КАК Актив ИЗ РегистрСведений.КотировкиЦБНаБирже.СрезПоследних(&Дата, "
            "Биржа = ЗНАЧЕНИЕ(Справочник.Биржи.ММВБ)) КАК т"
        )
        elapsed, data = first_row_map(conn, text, ["Актив"], {"Дата": period_end})
        asset = data.get("Актив")
        text2 = (
            "ВЫБРАТЬ т.ЦенаЗакрытия КАК Котировка ИЗ РегистрСведений.КотировкиЦБНаБирже.СрезПоследних(&Дата, "
            "Актив = &Актив И Биржа = ЗНАЧЕНИЕ(Справочник.Биржи.ММВБ)) КАК т"
        )
        runs = []
        for _ in range(3):
            elapsed2, data2 = first_row_map(conn, text2, ["Котировка"], {"Дата": period_end, "Актив": asset})
            runs.append(round(elapsed2, 3))
        return {"sec": round(elapsed, 3), "repeats_sec": runs, "asset": as_text(conn, asset)}

    step("close_price_per_asset", close_price_sample)

    def orders_today_scan():
        text = (
            "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ Документ.Поручение КАК т "
            "ГДЕ т.Дата >= &Нач И т.Дата <= &Кон И т.Проведен"
        )
        elapsed, data = first_row_map(
            conn, text, ["Кво"], {"Нач": dates["today"], "Кон": dates["today_end"]}
        )
        return {"sec": round(elapsed, 3), "count": int(data.get("Кво", 0))}

    step("orders_today", orders_today_scan)

    save(payload)
    safe_print("done")
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
