#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностика базы ПИФ перед замером getDeposits.
Пишет UTF-8 отчет и короткий ASCII-статус в консоль.
"""

import os
import sys
import time
import traceback

import pythoncom
import win32com.client


OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "probe_report.txt")
CONNECT = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"


def log(lines, text):
    lines.append(text)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def run_query(conn, text, params=None):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for name, value in params.items():
            query.УстановитьПараметр(name, value)
    started = time.perf_counter()
    result = query.Выполнить()
    elapsed = time.perf_counter() - started
    table = result.Выгрузить()
    return table, elapsed


def cell(row, name):
    return getattr(row, name)


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        connector = win32com.client.Dispatch("V83.COMConnector")
        started = time.perf_counter()
        conn = connector.Connect(CONNECT)
        log(lines, "CONNECT_OK sec=%.3f" % (time.perf_counter() - started))

        fill_text = (
            "ВЫБРАТЬ\n"
            "    КОЛИЧЕСТВО(*) КАК Счетов,\n"
            "    СУММА(ВЫБОР КОГДА Счета.ДатаОткрытия = ДАТАВРЕМЯ(1, 1, 1) ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК БезДатыОткрытия,\n"
            "    СУММА(ВЫБОР КОГДА Счета.НоминалДепозита = 0 ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК БезНоминала,\n"
            "    СУММА(ВЫБОР КОГДА Счета.ДатаЗакрытия = ДАТАВРЕМЯ(1, 1, 1) ИЛИ Счета.ДатаЗакрытия >= ДАТАВРЕМЯ(2026, 10, 27) ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК Действующие\n"
            "ИЗ\n"
            "    Справочник.БанковскиеСчета КАК Счета\n"
            "ГДЕ\n"
            "    Счета.НачислениеПроцентов\n"
            "    И НЕ Счета.ПометкаУдаления"
        )
        table, elapsed = run_query(conn, fill_text)
        row = table[0]
        log(lines, "FILL sec=%.3f accounts=%s no_open=%s no_nominal=%s active=%s" % (
            elapsed, cell(row, "Счетов"), cell(row, "БезДатыОткрытия"),
            cell(row, "БезНоминала"), cell(row, "Действующие")))

        active_text = (
            "ВЫБРАТЬ\n"
            "    КОЛИЧЕСТВО(*) КАК Счетов,\n"
            "    СУММА(ВЫБОР КОГДА Счета.ДатаОткрытия = ДАТАВРЕМЯ(1, 1, 1) ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК БезДатыОткрытия,\n"
            "    СУММА(ВЫБОР КОГДА Счета.НоминалДепозита = 0 ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК БезНоминала,\n"
            "    МИНИМУМ(Счета.ДатаОткрытия) КАК МинДатаОткрытия\n"
            "ИЗ\n"
            "    Справочник.БанковскиеСчета КАК Счета\n"
            "ГДЕ\n"
            "    Счета.НачислениеПроцентов\n"
            "    И НЕ Счета.ПометкаУдаления\n"
            "    И (Счета.ДатаЗакрытия = ДАТАВРЕМЯ(1, 1, 1) ИЛИ Счета.ДатаЗакрытия >= ДАТАВРЕМЯ(2026, 10, 27))"
        )
        table, elapsed = run_query(conn, active_text)
        row = table[0]
        log(lines, "ACTIVE sec=%.3f accounts=%s no_open=%s no_nominal=%s min_open=%s" % (
            elapsed, cell(row, "Счетов"), cell(row, "БезДатыОткрытия"),
            cell(row, "БезНоминала"), cell(row, "МинДатаОткрытия")))

        algo_text = (
            "ВЫБРАТЬ\n"
            "    КОЛИЧЕСТВО(*) КАК Записей,\n"
            "    КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Алгоритмы.Объект) КАК Объектов\n"
            "ИЗ\n"
            "    РегистрСведений.АлгоритмыРасчетаПроцентов КАК Алгоритмы"
        )
        table, elapsed = run_query(conn, algo_text)
        row = table[0]
        log(lines, "ALGO sec=%.3f rows=%s objects=%s" % (
            elapsed, cell(row, "Записей"), cell(row, "Объектов")))

        reg_text = (
            "ВЫБРАТЬ\n"
            "    КОЛИЧЕСТВО(*) КАК Движений,\n"
            "    МИНИМУМ(Движения.Период) КАК МинПериод,\n"
            "    МАКСИМУМ(Движения.Период) КАК МаксПериод\n"
            "ИЗ\n"
            "    РегистрБухгалтерии.Управленческий КАК Движения"
        )
        log(lines, "REG_COUNT_START")
        table, elapsed = run_query(conn, reg_text)
        row = table[0]
        log(lines, "REG sec=%.3f rows=%s min=%s max=%s" % (
            elapsed, cell(row, "Движений"), cell(row, "МинПериод"), cell(row, "МаксПериод")))

        ext_count = 0
        extensions = conn.РасширенияКонфигурации.Получить()
        for ext in extensions:
            ext_count += 1
            log(lines, "EXT name=%s active=%s safe=%s version=%s" % (
                ext.Имя, ext.Активно, ext.БезопасныйРежим, ext.Версия))
        log(lines, "EXT_TOTAL %s" % ext_count)
        log(lines, "PROBE_DONE")
        print("PROBE_DONE")
    except Exception:
        log(lines, "PROBE_ERROR")
        log(lines, traceback.format_exc())
        print("PROBE_ERROR")
        return 1
    finally:
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
