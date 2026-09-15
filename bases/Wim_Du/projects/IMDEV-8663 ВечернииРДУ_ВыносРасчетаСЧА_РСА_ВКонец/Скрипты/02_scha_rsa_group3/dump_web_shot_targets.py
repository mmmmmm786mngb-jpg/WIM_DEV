#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump navigation targets for web screenshots of IM86632 COMTEST docs."""

import json
import os
import sys

import pythoncom
import win32com.client

OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "Тестирование", "reports", "web_shots",
)
MARKER = "IM86632_COMTEST"


def uuid_to_1c_ref(uuid_str):
    s = str(uuid_str).replace("{", "").replace("}", "").strip()
    parts = s.split("-")
    if len(parts) == 5:
        return (parts[3] + parts[4] + parts[2] + parts[1] + parts[0]).lower()
    s = "".join(ch for ch in s if ch.isalnum())
    return (s[16:20] + s[20:32] + s[12:16] + s[8:12] + s[0:8]).lower()


def uid_of(conn, ref):
    try:
        return conn.String(ref.УникальныйИдентификатор())
    except Exception:
        try:
            return conn.XMLСтрока(ref)
        except Exception:
            return ""


def nav_of(conn, ref, meta_path, uid):
    try:
        link = conn.ПолучитьНавигационнуюСсылку(ref)
        if link:
            return str(link)
    except Exception:
        pass
    ref_hex = uuid_to_1c_ref(uid) if uid else ""
    if not ref_hex:
        return ""
    return "e1cib/data/%s?ref=%s" % (meta_path, ref_hex)


def make_date(conn, year, month, day, hour=0, minute=0, second=0):
    q = conn.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d, %d, %d, %d) КАК Д" % (
        year, month, day, hour, minute, second
    )
    return q.Выполнить().Выгрузить().Get(0).Д


def main():
    pythoncom.CoInitialize()
    com = win32com.client.Dispatch("V83.COMConnector")
    conn = com.Connect("Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;")
    os.makedirs(os.path.abspath(OUT_DIR), exist_ok=True)

    date_start = make_date(conn, 2027, 3, 15, 0, 0, 0)
    date_end = make_date(conn, 2027, 3, 15, 23, 59, 59)
    targets = {"marker": MARKER, "date": "15.03.2027"}

    q = conn.NewObject("Запрос")
    q.Текст = """
    ВЫБРАТЬ ПЕРВЫЕ 1
        План.Ссылка КАК Ссылка,
        План.Номер КАК Номер,
        План.Дата КАК Дата,
        ПРЕДСТАВЛЕНИЕ(План.ДоговорДУ) КАК Договор,
        ПРЕДСТАВЛЕНИЕ(План.ГруппаОперацийПользователя) КАК Группа,
        ПРЕДСТАВЛЕНИЕ(План.ПланВечернихОпераций) КАК ПланВечерних
    ИЗ
        Документ.ПланРегламентныхОперацийДУ КАК План
    ГДЕ
        План.Комментарий = &Маркер
        И План.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания
        И НЕ План.ПометкаУдаления
        И План.ПланВечернихОпераций <> ЗНАЧЕНИЕ(Документ.ПланРегламентныхОперацийДУ.ПустаяСсылка)
    УПОРЯДОЧИТЬ ПО
        План.Номер
    """
    q.УстановитьПараметр("Маркер", MARKER)
    q.УстановитьПараметр("ДатаНачала", date_start)
    q.УстановитьПараметр("ДатаОкончания", date_end)
    data = q.Выполнить().Выгрузить()
    if data.Количество() > 0:
        row = data.Get(0)
        uid = uid_of(conn, row.Ссылка)
        targets["plan_g3"] = {
            "number": str(row.Номер),
            "contract": str(row.Договор),
            "group": str(row.Группа),
            "evening": str(row.ПланВечерних),
            "uid": uid,
            "nav": nav_of(conn, row.Ссылка, "Документ.ПланРегламентныхОперацийДУ", uid),
        }

    q2 = conn.NewObject("Запрос")
    q2.Текст = """
    ВЫБРАТЬ ПЕРВЫЕ 1
        План.Ссылка КАК Ссылка,
        План.Номер КАК Номер,
        ПРЕДСТАВЛЕНИЕ(План.ДоговорДУ) КАК Договор,
        ПРЕДСТАВЛЕНИЕ(План.ГруппаОперацийПользователя) КАК Группа
    ИЗ
        Документ.ПланРегламентныхОперацийДУ КАК План
    ГДЕ
        План.Комментарий = &Маркер
        И План.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания
        И НЕ План.ПометкаУдаления
        И План.ПланВечернихОпераций = ЗНАЧЕНИЕ(Документ.ПланРегламентныхОперацийДУ.ПустаяСсылка)
        И План.Проведен
    УПОРЯДОЧИТЬ ПО
        План.Номер
    """
    q2.УстановитьПараметр("Маркер", MARKER)
    q2.УстановитьПараметр("ДатаНачала", date_start)
    q2.УстановитьПараметр("ДатаОкончания", date_end)
    data2 = q2.Выполнить().Выгрузить()
    if data2.Количество() > 0:
        row = data2.Get(0)
        uid = uid_of(conn, row.Ссылка)
        targets["plan_g2"] = {
            "number": str(row.Номер),
            "contract": str(row.Договор),
            "group": str(row.Группа),
            "uid": uid,
            "nav": nav_of(conn, row.Ссылка, "Документ.ПланРегламентныхОперацийДУ", uid),
        }

    q3 = conn.NewObject("Запрос")
    q3.Текст = """
    ВЫБРАТЬ ПЕРВЫЕ 1
        Док.Ссылка КАК Ссылка,
        Док.Номер КАК Номер,
        ПРЕДСТАВЛЕНИЕ(Док.ДоговорДУ) КАК Договор,
        ПРЕДСТАВЛЕНИЕ(Док.ДокументОснование) КАК Основание
    ИЗ
        Документ.РасчетСЧА_РСА КАК Док
    ГДЕ
        Док.Комментарий = &Маркер
        И НЕ Док.ПометкаУдаления
    УПОРЯДОЧИТЬ ПО
        Док.Номер
    """
    q3.УстановитьПараметр("Маркер", MARKER)
    data3 = q3.Выполнить().Выгрузить()
    if data3.Количество() > 0:
        row = data3.Get(0)
        uid = uid_of(conn, row.Ссылка)
        targets["scha"] = {
            "number": str(row.Номер),
            "contract": str(row.Договор),
            "base": str(row.Основание),
            "uid": uid,
            "nav": nav_of(conn, row.Ссылка, "Документ.РасчетСЧА_РСА", uid),
        }

    q4 = conn.NewObject("Запрос")
    q4.Текст = """
    ВЫБРАТЬ ПЕРВЫЕ 1
        Период.Ссылка КАК Ссылка,
        ПРЕДСТАВЛЕНИЕ(Период.Ссылка) КАК Представление
    ИЗ
        Справочник.РегламентныеПериоды КАК Период
    ГДЕ
        Период.ДатаПериода = НАЧАЛОПЕРИОДА(&ДатаНачала, ДЕНЬ)
        И НЕ Период.ПометкаУдаления
    """
    q4.УстановитьПараметр("ДатаНачала", date_start)
    data4 = q4.Выполнить().Выгрузить()
    if data4.Количество() > 0:
        row = data4.Get(0)
        uid = uid_of(conn, row.Ссылка)
        targets["period"] = {
            "title": str(row.Представление),
            "uid": uid,
            "nav": nav_of(conn, row.Ссылка, "Справочник.РегламентныеПериоды", uid),
        }

    out = os.path.abspath(os.path.join(OUT_DIR, "targets.json"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(targets, f, ensure_ascii=False, indent=2)

    print("OK wrote", out)
    print(json.dumps(targets, ensure_ascii=True, indent=2))
    pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
