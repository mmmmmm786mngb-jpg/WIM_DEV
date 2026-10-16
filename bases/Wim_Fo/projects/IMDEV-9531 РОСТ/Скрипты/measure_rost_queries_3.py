#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Замеры отборов РОСТ на дате с наибольшей фактической позицией и чтение регистра замеров.

Только чтение.
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
    "measure_rost_raw3.json",
)

REINVEST_QUERY = """
ВЫБРАТЬ
    т.Объект КАК Портфель,
    т.Значение КАК Статус
ПОМЕСТИТЬ ВТ_СтатусПортфелей
ИЗ
    РегистрСведений.ДополнительныеСведения КАК т
ГДЕ
    т.Свойство = &СвойствоСтатус
;

ВЫБРАТЬ РАЗРЕШЕННЫЕ
    т.Объект КАК Портфель,
    т.Значение КАК ДатаПослСтатуса
ПОМЕСТИТЬ ВТ_ДатыСтатусПортфелей
ИЗ
    РегистрСведений.ДополнительныеСведения КАК т
ГДЕ
    т.Свойство = &СвойствоДатаСтатус
;

ВЫБРАТЬ
    т.Портфель КАК Портфель,
    СУММА(т.Количество) КАК Количество
ПОМЕСТИТЬ втДС
ИЗ
    РегистрСведений.ФактическаяПозиция КАК т
ГДЕ
    т.Дата = &ПозицияНаДату
    И т.Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)

СГРУППИРОВАТЬ ПО
    т.Портфель
;

ВЫБРАТЬ
    т.Портфель КАК Портфель,
    т.Субпортфель КАК Субпортфель,
    т.Актив КАК Актив,
    т.Актив.Объект КАК Облигация,
    т.Количество КАК Количество
ПОМЕСТИТЬ втАктивы
ИЗ
    РегистрСведений.ФактическаяПозиция КАК т
ГДЕ
    т.Дата = &ПозицияНаДату
    И т.Актив.Объект ССЫЛКА Справочник.Облигации
;

ВЫБРАТЬ
    втАктивы.Портфель КАК Портфель,
    втАктивы.Субпортфель КАК Субпортфель,
    втАктивы.Актив КАК Актив,
    втАктивы.Облигация КАК Облигация,
    втАктивы.Количество КАК ОстатокЦБ,
    ЕСТЬNULL(к.РазмерДоходаВРублях, 0) КАК СуммаНКДзаЕд,
    ЕСТЬNULL(втАктивы.Количество, 0) * ЕСТЬNULL(к.РазмерДоходаВРублях, 0) КАК СуммаРеинвестирования
ПОМЕСТИТЬ втКупоны
ИЗ
    втАктивы КАК втАктивы
        ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.КупонноеРасписаниеПоОблигациям.СрезПоследних(
                КОНЕЦПЕРИОДА(&НаДату, ДЕНЬ),
                Облигация В
                    (ВЫБРАТЬ
                        т.Облигация
                    ИЗ
                        втАктивы КАК т)) КАК т
        ПО втАктивы.Облигация = т.Облигация
        ЛЕВОЕ СОЕДИНЕНИЕ Документ.КупонноеРасписание.Купоны КАК к
        ПО (т.Документ = к.Ссылка)
            И (к.ДатаВыплатыКупонногоДохода = &НаДату)

ИНДЕКСИРОВАТЬ ПО
    Портфель
;

ВЫБРАТЬ
    КОЛИЧЕСТВО(*) КАК Кво
ИЗ
    втКупоны КАК т
        ЛЕВОЕ СОЕДИНЕНИЕ втДС КАК втДС
        ПО т.Портфель = втДС.Портфель
        ЛЕВОЕ СОЕДИНЕНИЕ ВТ_СтатусПортфелей КАК ВТ_СтатусПортфелей
        ПО т.Портфель = ВТ_СтатусПортфелей.Портфель
        ЛЕВОЕ СОЕДИНЕНИЕ РегистрНакопления.ПрогнозПоПоручению.Остатки(&ПрогнозПозицияНаДату, Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК ПрогнозВлюта
        ПО т.Портфель = ПрогнозВлюта.Портфель
        ЛЕВОЕ СОЕДИНЕНИЕ РегистрНакопления.ПлановаяПозиция.Остатки(&ПрогнозПозицияНаДату, Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК ПланВалюта
        ПО т.Портфель = ПланВалюта.Портфель
        ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.РегистрРСА_СЧА.СрезПоследних(&ПрогнозПозицияНаДату, ) КАК тСЧА
        ПО т.Портфель = тСЧА.Портфель
"""


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
    try:
        return str(conn.String(value))
    except Exception:
        return str(value)


def main():
    payload = {"steps": []}
    save(payload)
    pythoncom.CoInitialize()
    safe_print("connect")
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    safe_print("connected")
    holder = {}

    def step(name, func):
        safe_print("step " + name)
        started = time.perf_counter()
        try:
            info = func()
            info["name"] = name
            info["ok"] = True
            info["wall_sec"] = round(time.perf_counter() - started, 3)
            payload["steps"].append(info)
            save(payload)
            safe_print("ok " + name + " " + str(info.get("sec", "")))
        except Exception as error:
            payload["steps"].append({
                "name": name,
                "ok": False,
                "error": str(error)[:1800],
                "wall_sec": round(time.perf_counter() - started, 3),
            })
            save(payload)
            safe_print("ERR " + name + " " + str(error)[:300])

    def rows(text, fields, params=None, limit=100):
        query = conn.NewObject("Запрос")
        query.Текст = text
        if params:
            for key, value in params.items():
                query.УстановитьПараметр(key, value)
        started = time.perf_counter()
        selection = query.Выполнить().Выбрать()
        elapsed = time.perf_counter() - started
        result = []
        while selection.Следующий() and len(result) < limit:
            item = {}
            for field in fields:
                value = getattr(selection, field)
                if field in ("Кво", "Вес"):
                    item[field] = int(value)
                elif field in ("Секунды",):
                    item[field] = float(value)
                else:
                    item[field] = as_text(conn, value)[:300]
            result.append(item)
        return round(elapsed, 3), result

    def bind():
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ МИНИМУМ(т.Дата) КАК Д, КОНЕЦПЕРИОДА(МИНИМУМ(т.Дата), ДЕНЬ) КАК К "
            "ИЗ РегистрСведений.ФактическаяПозиция КАК т"
        )
        selection = query.Выполнить().Выбрать()
        selection.Следующий()
        holder["heavy"] = selection.Д
        holder["heavy_end"] = selection.К
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ т.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК т "
            "ГДЕ т.ИмяОбъекта = &Имя И НЕ т.ПометкаУдаления"
        )
        query.УстановитьПараметр("Имя", "СозданиеТорговыхПорученийРОСТ")
        selection = query.Выполнить().Выбрать()
        selection.Следующий()
        item = selection.Ссылка.ПолучитьОбъект()
        path = os.path.join(tempfile.gettempdir(), "rost_measure_readonly.epf")
        item.ХранилищеОбработки.Получить().Записать(path)
        processor = conn.ВнешниеОбработки.Создать(path, False)
        title = ""
        processor.УстановитьПользовательскиеНастройки(item.ХранилищеНастроек.Получить(), title)
        holder["processor"] = processor
        return {"sec": 0, "heavy": as_text(conn, holder["heavy"])}

    step("bind", bind)

    def count_bonds():
        sec, result = rows(
            "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво, КОЛИЧЕСТВО(РАЗЛИЧНЫЕ т.Портфель) КАК Вес "
            "ИЗ РегистрСведений.ФактическаяПозиция КАК т "
            "ГДЕ т.Дата = &Дата И т.Актив.Объект ССЫЛКА Справочник.Облигации",
            ["Кво", "Вес"],
            {"Дата": holder["heavy"]},
        )
        return {"sec": sec, "rows": result}

    step("bonds_on_heavy_date", count_bonds)

    def count_money():
        sec, result = rows(
            "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ РегистрСведений.ФактическаяПозиция КАК т "
            "ГДЕ т.Дата = &Дата И т.Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)",
            ["Кво"],
            {"Дата": holder["heavy"]},
        )
        return {"sec": sec, "rows": result}

    step("money_on_heavy_date", count_money)

    def reinvest():
        processor = holder["processor"]
        params = {
            "НаДату": holder["heavy"],
            "ПозицияНаДату": holder["heavy"],
            "ПрогнозПозицияНаДату": holder["heavy_end"],
            "СвойствоСтатус": processor.ДопРеквизитСтатусПортфеля,
            "СвойствоДатаСтатус": processor.ДопРеквизитДатаОперации,
        }
        sec, result = rows(REINVEST_QUERY, ["Кво"], params)
        return {"sec": sec, "rows": result, "position_date": as_text(conn, holder["heavy"])}

    step("reinvest_query_heavy", reinvest)

    def plan_rows():
        text = (
            "ВЫБРАТЬ т.Портфель КАК Портфель ПОМЕСТИТЬ вт "
            "ИЗ РегистрНакопления.ПлановаяПозиция.Остатки(&Дата, "
            "Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т; "
            "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ вт КАК вт"
        )
        sec, result = rows(text, ["Кво"], {"Дата": holder["heavy_end"]})
        return {"sec": sec, "rows": result}

    step("plan_currency_rows", plan_rows)

    def forecast_rows():
        text = (
            "ВЫБРАТЬ т.Портфель КАК Портфель ПОМЕСТИТЬ вт "
            "ИЗ РегистрНакопления.ПрогнозПоПоручению.Остатки(&Дата, "
            "Актив.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты)) КАК т; "
            "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ вт КАК вт"
        )
        sec, result = rows(text, ["Кво"], {"Дата": holder["heavy_end"]})
        return {"sec": sec, "rows": result}

    step("forecast_currency_rows", forecast_rows)

    def scha_rows():
        text = (
            "ВЫБРАТЬ т.Портфель КАК Портфель ПОМЕСТИТЬ вт "
            "ИЗ РегистрСведений.РегистрРСА_СЧА.СрезПоследних(&Дата, ) КАК т; "
            "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кво ИЗ вт КАК вт"
        )
        sec, result = rows(text, ["Кво"], {"Дата": holder["heavy_end"]})
        return {"sec": sec, "rows": result}

    step("scha_rows", scha_rows)

    def rost_measures():
        sec, result = rows(
            "ВЫБРАТЬ "
            "Замеры.ДатаНачалаЗамера КАК Старт, "
            "Замеры.КлючеваяОперация.Наименование КАК Имя, "
            "Замеры.ВремяВыполнения КАК Секунды, "
            "Замеры.ВесЗамера КАК Вес, "
            "Замеры.Комментарий КАК Комментарий, "
            "Замеры.ВыполненСОшибкой КАК Ошибка "
            "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
            "ГДЕ Замеры.КлючеваяОперация.Наименование ПОДОБНО \"%рост%\" "
            "ИЛИ Замеры.КлючеваяОперация.Наименование ПОДОБНО \"%Распорядитель%\" "
            "ИЛИ Замеры.КлючеваяОперация.Наименование ПОДОБНО \"%поручен%\" "
            "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера",
            ["Старт", "Имя", "Секунды", "Вес", "Комментарий", "Ошибка"],
            limit=200,
        )
        return {"sec": sec, "rows": result, "shown": len(result)}

    step("rost_measures", rost_measures)

    safe_print("done")
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
