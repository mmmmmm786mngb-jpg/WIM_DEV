#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Замер исходного и ускоренного пакета депозитов на стенде ПИФ.
Результат пишет в UTF-8, в консоль выводит только ASCII.
"""

import json
import os
import sys
import time
import traceback

import pythoncom
import win32com.client


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_PATH = os.path.join(ROOT, "benchmark_report.json")
CONNECT = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
RUNS = 3


def connect():
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONNECT)


def make_date(conn):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(2026, 10, 28) КАК Д"
    return query.Выполнить().Выгрузить()[0].Д


def grant_role(conn):
    user = conn.ПользователиИнформационнойБазы.НайтиПоИмени("admin")
    role = conn.Метаданные.Роли.ТестКурсора_ОсновнаяРоль
    if user.Роли.Содержит(role):
        return False
    user.Роли.Добавить(role)
    user.Записать()
    return True


def prepare_extension(conn):
    changed = False
    found = False
    extensions = conn.РасширенияКонфигурации.Получить()
    for ext in extensions:
        if str(ext.Имя) != "ТестКурсора":
            continue
        found = True
        if bool(ext.БезопасныйРежим) or not bool(ext.Активно):
            ext.БезопасныйРежим = False
            ext.Активно = True
            ext.Записать()
            changed = True
    return found, changed


def set_active(conn, active):
    extensions = conn.РасширенияКонфигурации.Получить()
    for ext in extensions:
        if str(ext.Имя) != "ТестКурсора":
            continue
        ext.Активно = active
        ext.БезопасныйРежим = False
        ext.Записать()


def parse_measure(text):
    data = {}
    for part in str(text).split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        data[name] = value
    return data


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def main():
    pythoncom.CoInitialize()
    report = {"runs": {}, "parts": {}, "errors": []}
    try:
        conn = connect()
        found, changed = prepare_extension(conn)
        report["extension_found"] = found
        report["extension_reactivated"] = changed
        if not found:
            report["errors"].append("extension not loaded")
            return 1
        if changed:
            conn = connect()
        try:
            report["role_granted"] = grant_role(conn)
        except Exception:
            report["errors"].append(traceback.format_exc())
            report["role_granted"] = False

        moment = make_date(conn)
        module = conn.ТестКурсора_Замер
        variants = ("Оригинал", "ОдинПроход")

        # Прогрев кэша СУБД, эти цифры в итог не входят.
        for variant in variants:
            module.Замерить(moment, variant)

        keys = {}
        for variant in variants:
            samples = []
            for _ in range(RUNS):
                parsed = parse_measure(module.Замерить(moment, variant))
                samples.append(int(parsed["ms"]))
                keys[variant] = parsed["key"]
                report["rows"] = int(parsed["rows"])
            report["runs"][variant] = {
                "samples_ms": samples,
                "min_ms": min(samples),
                "median_ms": median(samples),
            }

        report["same_original_onepass"] = keys["Оригинал"] == keys["ОдинПроход"]
        report["keys"] = keys

        for variant in variants:
            report["parts"][variant] = str(module.ЗамеритьЧасти(moment, variant))

        base = report["runs"]["Оригинал"]["median_ms"]
        one = report["runs"]["ОдинПроход"]["median_ms"]
        report["speedup_median"] = None if one == 0 else round(base / float(one), 2)
        report["time_cut_percent"] = None if base == 0 else round((base - one) * 100.0 / base, 1)
        print("BENCH_OK rows=%s orig=%s onepass=%s speedup=%s cut=%s same=%s" % (
            report.get("rows"),
            report["runs"]["Оригинал"]["median_ms"],
            report["runs"]["ОдинПроход"]["median_ms"],
            report["speedup_median"],
            report["time_cut_percent"],
            report["same_original_onepass"],
        ))
        return 0
    except Exception:
        report["errors"].append(traceback.format_exc())
        print("BENCH_ERROR")
        return 1
    finally:
        with open(OUT_PATH, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
