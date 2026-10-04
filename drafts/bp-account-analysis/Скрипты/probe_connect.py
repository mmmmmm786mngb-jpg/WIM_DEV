#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe COM connection to BP demo and inspect account analysis report."""

import pythoncom
import win32com.client
import traceback

OUT = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Скрипты\probe_result.txt"


def log(lines, text):
    lines.append(text)


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        log(lines, "COM connector created")
        conn_str = "File='C:\\1c\\БП_ДЕМО';App='PyCOM';Locale=ru_RU;"
        try:
            conn = com.Connect(conn_str)
            log(lines, "Connected without user")
        except Exception as e:
            log(lines, "Connect without user failed: " + str(e))
            conn = None
            for user in ("Администратор", "Admin", ""):
                try:
                    conn = com.Connect(conn_str + "Usr='" + user + "';")
                    log(lines, "Connected as: " + user)
                    break
                except Exception as e2:
                    log(lines, "Fail user " + user + ": " + str(e2)[:400])
        if conn is None:
            with open(OUT, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return

        md = conn.Metadata
        log(lines, "Config: " + str(md.Name) + " / " + str(md.Synonym) + " / " + str(md.Version))

        reports = md.Reports
        log(lines, "Reports count: " + str(reports.Count()))
        found = []
        for i in range(reports.Count()):
            rep = reports.Get(i)
            name = str(rep.Name)
            syn = str(rep.Synonym)
            if "Анализ" in name or "Анализ" in syn or "Счет" in name:
                found.append(name + " | " + syn)
        log(lines, "Matched reports:")
        for item in found:
            log(lines, "  " + item)

        # organization
        query = conn.NewObject("Query")
        query.Text = (
            "ВЫБРАТЬ ПЕРВЫЕ 20 Наименование, ИНН "
            "ИЗ Справочник.Организации "
            "ГДЕ Наименование ПОДОБНО \"%Конфет%\""
        )
        result = query.Execute().Unload()
        log(lines, "Orgs: " + str(result.Count()))
        for row in result:
            log(lines, "  org: " + str(row.Наименование))

        query2 = conn.NewObject("Query")
        query2.Text = (
            "ВЫБРАТЬ Код, Наименование, Количественный, Валютный, Забалансовый "
            "ИЗ ПланСчетов.Хозрасчетный "
            "ГДЕ Код ПОДОБНО \"41%\""
        )
        result2 = query2.Execute().Unload()
        log(lines, "Accounts 41*: " + str(result2.Count()))
        for row in result2:
            log(lines, "  acc: " + str(row.Код) + " " + str(row.Наименование)
                       + " qty=" + str(row.Количественный) + " cur=" + str(row.Валютный))

        # extensions
        try:
            exts = conn.ConfigurationExtensions.Get()
            log(lines, "Extensions: " + str(exts.Count()))
            for ext in exts:
                log(lines, "  ext: " + str(ext.Name) + " active=" + str(ext.Active))
        except Exception as e:
            log(lines, "Extensions error: " + str(e)[:300])

    except Exception:
        log(lines, traceback.format_exc())
    finally:
        pythoncom.CoUninitialize()

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
