#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe WIM_FIN COM: extensions, counts, accounts, processing attributes."""

import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pythoncom
import win32com.client


def q(conn, text):
    query = conn.NewObject("Запрос")
    query.Текст = text
    result = query.Выполнить().Выгрузить()
    rows = []
    if result.Количество() == 0:
        return rows
    cols = [result.Колонки.Get(i).Имя for i in range(result.Колонки.Количество())]
    for i in range(result.Количество()):
        row = result.Get(i)
        rows.append({c: row.Get(c) for c in cols})
    return rows


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_FIN';App='PyCOM';Locale=ru_RU;")
        print("CONNECTED WIM_FIN")

        print("--- EXTENSIONS ---")
        try:
            exts = conn.РасширенияКонфигурации.Получить()
            print("count", exts.Количество() if hasattr(exts, "Количество") else len(list(exts)))
            for ext in exts:
                name = str(ext.Имя)
                line = name
                for attr in (
                    "Синоним",
                    "Версия",
                    "Активно",
                    "БезопасныйРежим",
                    "Назначение",
                    "ЗащитаОтОпасныхДействий",
                ):
                    try:
                        line += f" | {attr}={getattr(ext, attr)}"
                    except Exception as e:
                        line += f" | {attr}=ERR:{e}"
                print(line)
                if name == "IMDEV9458_EmptyTurnover":
                    try:
                        print("  trying SafeMode off")
                        ext.БезопасныйРежим = False
                        ext.Записать()
                        print("  SafeMode write OK")
                    except Exception as e:
                        print("  SafeMode write FAIL", e)
        except Exception:
            traceback.print_exc()

        print("--- COUNTS ---")
        for text, label in [
            ("ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ Справочник.Контрагенты", "Kontragenty"),
            ("ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ Справочник.Портфели", "Portfeli"),
            ("ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ Документ.ОперацияБух", "OperaciyaBuh"),
            ("ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ Справочник.Периоды", "Periody"),
            ("ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ ПланСчетов.Хозрасчетный", "Accounts"),
        ]:
            try:
                rows = q(conn, text)
                print(label, rows[0]["К"] if rows else "?")
            except Exception as e:
                print(label, "ERR", e)

        print("--- ACCOUNTS 90/91 ---")
        try:
            rows = q(
                conn,
                """
                ВЫБРАТЬ Код, Наименование
                ИЗ ПланСчетов.Хозрасчетный
                ГДЕ Код ПОДОБНО \"90%\" ИЛИ Код ПОДОБНО \"91%\" ИЛИ Код ПОДОБНО \"76%\" ИЛИ Код = \"51\"
                УПОРЯДОЧИТЬ ПО Код
                """,
            )
            print("rows", len(rows))
            for r in rows[:40]:
                print(r["Код"], r["Наименование"])
        except Exception as e:
            print("accounts ERR", e)
            traceback.print_exc()

        print("--- PERIODS 2026 YEAR ---")
        try:
            rows = q(
                conn,
                """
                ВЫБРАТЬ ПЕРВЫЕ 20 Ссылка, Наименование, ДатаНачала, ДатаОкончания, Периодичность
                ИЗ Справочник.Периоды
                ГДЕ ГОД(ДатаНачала) = 2026
                УПОРЯДОЧИТЬ ПО ДатаНачала
                """,
            )
            print("rows", len(rows))
            for r in rows:
                print(r)
        except Exception as e:
            print("periods ERR", e)
            traceback.print_exc()

        print("--- PROCESSING ---")
        try:
            manager = getattr(conn.Обработки, "ФормированиеНачисленийНДФЛ")
            obj = manager.Создать()
            print("created")
            for attr in (
                "НеСоздаватьНДФЛПоКлиентамБезОборотов",
                "СчетаОборотовДляОтбораНДФЛ",
                "ВариантЗаполнения",
                "НалоговыйПериод",
                "УправляющаяКомпания",
                "Клиент",
                "ПоПортфелямСДвижениямиПоНДФЛ",
            ):
                try:
                    print(attr, "=", getattr(obj, attr))
                except Exception as e:
                    print(attr, "ERR", e)
        except Exception:
            traceback.print_exc()

        print("--- DEVOPS ---")
        try:
            vtb = getattr(conn, "ВТБ_DevOps", None)
            print("VTB_DevOps", vtb)
            if vtb:
                vtb.ВыполнитьКод("Сообщить(\"probe-ok\");")
                print("ExecuteCode OK")
        except Exception:
            traceback.print_exc()

        print("--- SCHETAPOSTR ---")
        try:
            psa = conn.ПланыСчетов.Хозрасчетный
            arr = psa.СчетаПоСтроке("90.01, 91.01, 91.03")
            print("count", arr.Количество())
            for i in range(arr.Количество()):
                acc = arr.Get(i)
                print(" ", conn.String(acc), acc.Код)
        except Exception:
            traceback.print_exc()

    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
