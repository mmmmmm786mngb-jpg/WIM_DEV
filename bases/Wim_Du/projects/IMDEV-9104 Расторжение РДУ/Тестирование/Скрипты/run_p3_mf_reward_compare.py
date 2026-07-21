#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMDEV-9104-3: run MF reward compare EPF via COM and print result summary.
HTML report is written by the EPF itself.
"""

import os
import sys

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        safe_print("ERROR: pywin32 required (pip install pywin32)")
        return 1

    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    epf_path = os.path.join(base_dir, "внТестСравнениеMFВознаграждения.epf")
    html_path = os.path.join(
        base_dir, "reports", "imdev9104_p3_mf_reward_compare.html"
    )

    if not os.path.isfile(epf_path):
        safe_print("ERROR: EPF not found: " + epf_path)
        return 1

    os.makedirs(os.path.dirname(html_path), exist_ok=True)

    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn_str = "Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;"
        safe_print("Connect: " + conn_str)
        conn = com.Connect(conn_str)

        safe_print("Load EPF: " + epf_path)
        ext = conn.ExternalDataProcessors.Create(epf_path, False)

        pool = conn.Catalogs.Пул.FindByDescription("Розничное ДУ", True)
        if pool.IsEmpty():
            safe_print("ERROR: pool 'Розничное ДУ' not found")
            return 1

        ext.Пул = pool
        ext.ДатаРасчета = conn.EndOfDay(conn.CurrentDate())
        ext.ПутьHTML = html_path

        safe_print("Run compare (all contracts of pool)...")
        result = ext.СформироватьОтчетЗамеровТеста()

        ok = bool(result.Успех)
        n = int(result.КоличествоДоговоров)
        diff = int(result.Различий)
        match = bool(result.РезультатыСовпадают)
        ms_old = int(result.МсПоСтарому)
        ms_new = int(result.МсПоНовому)
        html_out = str(result.ПутьHTML)
        err = str(result.ТекстОшибки) if result.ТекстОшибки else ""

        safe_print("Success: " + str(ok))
        safe_print("Contracts: " + str(n))
        safe_print("Sums match: " + str(match) + " (diff=" + str(diff) + ")")
        safe_print("Time old ms: " + str(ms_old))
        safe_print("Time new ms: " + str(ms_new))
        safe_print("HTML: " + html_out)
        if err:
            safe_print("Error: " + err)
            return 1

        if not os.path.isfile(html_out):
            safe_print("WARN: HTML file not found after run")
            return 1

        safe_print("OK")
        return 0
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
