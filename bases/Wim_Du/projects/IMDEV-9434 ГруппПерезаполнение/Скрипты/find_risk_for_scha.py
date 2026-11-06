#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ищет расчет СЧА по номеру и связанные документы контроля риска."""

import sys
import traceback


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    import pythoncom
    import win32com.client

    out_path = sys.argv[1]
    pythoncom.CoInitialize()
    lines = []
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;")
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ\n"
            "    Док.Ссылка КАК Ссылка,\n"
            "    Док.Номер КАК Номер,\n"
            "    Док.Дата КАК Дата,\n"
            "    Док.ДоговорДУ КАК ДоговорДУ,\n"
            "    Док.ПометкаУдаления КАК ПометкаУдаления,\n"
            "    Док.Проведен КАК Проведен\n"
            "ИЗ\n"
            "    Документ.РасчетСЧА_РСА КАК Док\n"
            "ГДЕ\n"
            "    Док.Номер ПОДОБНО \"%3566548%\""
        )
        selection = query.Выполнить().Выбрать()
        scha = []
        while selection.Следующий():
            scha.append(selection.Ссылка)
            lines.append(
                "SCHA number=" + str(selection.Номер)
                + " date=" + str(selection.Дата)
                + " contract=" + str(selection.ДоговорДУ)
                + " deleted=" + str(selection.ПометкаУдаления)
                + " posted=" + str(selection.Проведен)
            )
        if not scha:
            lines.append("SCHA not found")
        else:
            query2 = conn.NewObject("Запрос")
            query2.Текст = (
                "ВЫБРАТЬ\n"
                "    Риск.Ссылка КАК Ссылка,\n"
                "    Риск.Номер КАК Номер,\n"
                "    Риск.Дата КАК Дата,\n"
                "    Риск.ДоговорДУ КАК ДоговорДУ,\n"
                "    Риск.ДокументОснование КАК ДокументОснование,\n"
                "    Риск.ПометкаУдаления КАК ПометкаУдаления,\n"
                "    Риск.Проведен КАК Проведен\n"
                "ИЗ\n"
                "    Документ.КонтрольДопустимогоУровняРиска КАК Риск\n"
                "ГДЕ\n"
                "    Риск.ДокументОснование В (&Ссылки)\n"
                "    ИЛИ Риск.ДоговорДУ В\n"
                "        (ВЫБРАТЬ\n"
                "            Док.ДоговорДУ\n"
                "        ИЗ\n"
                "            Документ.РасчетСЧА_РСА КАК Док\n"
                "        ГДЕ\n"
                "            Док.Ссылка В (&Ссылки))\n"
                "УПОРЯДОЧИТЬ ПО\n"
                "    Риск.Дата"
            )
            refs = conn.NewObject("Массив")
            for ref in scha:
                refs.Add(ref)
            query2.УстановитьПараметр("Ссылки", refs)
            risk = query2.Выполнить().Выбрать()
            found = 0
            while risk.Следующий():
                found = found + 1
                lines.append(
                    "RISK number=" + str(risk.Номер)
                    + " date=" + str(risk.Дата)
                    + " contract=" + str(risk.ДоговорДУ)
                    + " basis=" + str(risk.ДокументОснование)
                    + " deleted=" + str(risk.ПометкаУдаления)
                    + " posted=" + str(risk.Проведен)
                )
            lines.append("risk rows=" + str(found))
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        safe_print("rows=" + str(len(lines)))
        return 0
    except Exception as exc:
        safe_print("ERROR: " + str(exc))
        safe_print(traceback.format_exc())
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
