#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run IMDEV9458_DiagEmptyUKClients via COM on WIM_FIN."""

import datetime
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pythoncom
import win32com.client

EPF = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-9458 "
    r"Доработка обработки Формирование начислений НДФЛ"
    r"\Тестирование\IMDEV9458_DiagEmptyUKClients.epf"
)
OUT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-9458 "
    r"Доработка обработки Формирование начислений НДФЛ"
    r"\Тестирование\reports\diag_two_uk_clients_report.txt"
)


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_FIN';App='PyCOM';Locale=ru_RU;")
        print("CONNECTED")

        ext = conn.ExternalDataProcessors.Create(str(EPF))
        print("EPF loaded")

        names = conn.NewObject("Массив")
        names.Add("Львов Павел Глебович")
        names.Add("Баландин Дмитрий Викторович")

        params = conn.NewObject("Структура")
        params.Insert("ДатаОкончания", datetime.datetime(2026, 12, 31))
        params.Insert("СчетаОтбора", "90.01, 91.01, 91.03")
        params.Insert(
            "СчетаОбщиеОбороты",
            "68.01, 90.01, 90.02, 91.01.02, 91.01.09, 91.02.02, 91.02.03, "
            "91.02.04, 91.02.05, 91.02.06, 91.02.10, 91.02.11, 91.03, 91.04, 91.02.08",
        )
        params.Insert("ИменаКлиентов", names)

        print("Running diagnosis...")
        report = ext.ВыполнитьДиагностику(params)
        text = "" if report is None else str(report)

        print("Running source diagnosis...")
        report_src = ext.ВыполнитьДиагностикуИсточников(params)
        text_src = "" if report_src is None else str(report_src)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        OUT_SRC = OUT.with_name("diag_two_uk_sources_report.txt")
        OUT_SRC.write_text(text_src, encoding="utf-8")
        print("WROTE", OUT)
        print("WROTE", OUT_SRC)
        print("--- REPORT ---")
        print(text)
        print("--- SOURCES ---")
        print(text_src)
        return 0
    except Exception as exc:
        print("ERROR", type(exc).__name__, exc)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
