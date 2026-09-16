#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COM-proverka vseh rezhimov formy: 4 formata fayla i 3 flaga.
"""

import datetime
import json
import os
import sys

import pythoncom
import win32com.client

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPF = os.path.join(PROJECT_DIR, "build", "NomineeOwnersLoad.epf")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
SEED_JSON = os.path.join(REPORT_DIR, "form_modes_seed.json")
RESULT_JSON = os.path.join(REPORT_DIR, "form_modes_com.json")
RUN_ID = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
PREFIX = "MODE_%s_" % RUN_ID
ADDRESS = "- 614007,Permskiy kray,g Perm,ul Testovaya,d 7,kv 3"
CONN = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"


def ascii_only(text):
    return str(text).encode("ascii", "replace").decode("ascii")


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(ascii_only(text))


def com_err(exc):
    desc = str(exc)
    try:
        desc = str(exc.args[2][2])
    except Exception:
        pass
    return ascii_only("%s: %s" % (type(exc).__name__, desc))


def is_filled(ref):
    try:
        return not ref.Пустая()
    except Exception:
        return False


def date1c(conn, year, month, day):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d) КАК ЗначениеДаты" % (year, month, day)
    return query.Выполнить().Выгрузить()[0].ЗначениеДаты


def find_by_name(conn, catalog, name, is_folder=None):
    query = conn.NewObject("Запрос")
    if is_folder is True:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И ЭтоГруппа"
        ) % catalog
    elif is_folder is False:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И НЕ ЭтоГруппа"
        ) % catalog
    else:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s ГДЕ Наименование = &Наименование"
        ) % catalog
    query.УстановитьПараметр("Наименование", name)
    result = query.Выполнить()
    if result.Пустой():
        return None
    return result.Выгрузить()[0].Ссылка


def add_case(cases, name, ok, details="", error=""):
    item = {"name": name, "ok": bool(ok), "details": details or "", "error": error or ""}
    cases.append(item)
    safe_print("%s  %s" % ("OK" if ok else "FAIL", name))
    if details:
        safe_print("    %s" % ascii_only(details))
    if error:
        safe_print("    ERR: %s" % ascii_only(error))
    return bool(ok)


def write_xlsx(conn, path, cells_by_row):
    tab = conn.NewObject("ТабличныйДокумент")
    for row_num, cells in cells_by_row.items():
        for col, value in cells.items():
            tab.Область(int(row_num), int(col)).Текст = str(value)
    tab.Записать(path, conn.ТипФайлаТабличногоДокумента.XLSX)
    return path


def make_xml(path, account_code, owners):
    parts = []
    for owner in owners:
        parts.append(
            "<Пайщик>"
            "<ЗЛ_НомерСчета>%s</ЗЛ_НомерСчета>"
            "<ЗЛ_Наименование>%s</ЗЛ_Наименование>"
            "<ЗЛ_ДатаРождения>%s</ЗЛ_ДатаРождения>"
            "<ЗЛ_ЮрАдрес>%s</ЗЛ_ЮрАдрес>"
            "<ЗЛ_ПочтовыйАдрес>%s</ЗЛ_ПочтовыйАдрес>"
            "<ЗЛ_ИНН></ЗЛ_ИНН>"
            "<ЗЛ_КоличествоПаев>%s</ЗЛ_КоличествоПаев>"
            "<ЗЛ_Тип>ФЛ</ЗЛ_Тип>"
            "</Пайщик>"
            % (
                account_code,
                owner["fio"],
                owner["dob"],
                owner.get("addr", ADDRESS),
                owner.get("addr", ADDRESS),
                owner.get("shares", "5"),
            )
        )
    body = '<?xml version="1.0" encoding="UTF-8"?><Файл>' + "".join(parts) + "</Файл>"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def first_row(table):
    if table.Количество() < 1:
        return None
    return table[0]


def unique_ls(table):
    values = []
    details = []
    for i in range(table.Количество()):
        row = table[i]
        if is_filled(row.ЛицевойСчет):
            try:
                key = str(row.ЛицевойСчет.УникальныйИдентификатор())
            except Exception:
                key = str(row.ЛицевойСчет)
            details.append(key)
            if key not in values:
                values.append(key)
    return values, details


def main():
    os.makedirs(FIXTURES, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    cases = []
    pythoncom.CoInitialize()
    seed = {}
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect(CONN)
        add_case(cases, "COM connect", True, CONN)

        protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
        protection.ПредупреждатьОбОпасныхДействиях = False
        proc = conn.ВнешниеОбработки.Создать(EPF, False, protection)
        add_case(cases, "Open processing", True, "version via Svedeniya")

        period = date1c(conn, 2026, 8, 31)
        birth = date1c(conn, 1955, 3, 24)
        prop = proc.ОбеспечитьСвойствоНРДid()

        fund_name = PREFIX + "FUND"
        manager = conn.NewObject("СправочникМенеджер.ПИФ")
        fund_obj = manager.СоздатьЭлемент()
        fund_obj.Наименование = fund_name
        fund_obj.Используется = True
        fund_obj.ОбменДанными.Загрузка = True
        fund_obj.Записать()
        fund = fund_obj.Ссылка

        group_name = PREFIX + "GROUP"
        gman = conn.NewObject("СправочникМенеджер.Контрагенты")
        gobj = gman.СоздатьГруппу()
        gobj.Наименование = group_name
        gobj.ОбменДанными.Загрузка = True
        gobj.Записать()
        group = gobj.Ссылка

        nominee_name = PREFIX + "NOMINEE"
        nobj = gman.СоздатьЭлемент()
        nobj.Наименование = nominee_name
        nobj.НаименованиеПолное = nominee_name
        nobj.Пайщик = True
        nobj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ЮрЛицо
        nobj.ИНН = "7700000088"
        nobj.Родитель = group
        nobj.ОбменДанными.Загрузка = True
        nobj.Записать()
        nominee = nobj.Ссылка

        ls_code = "MODE%s" % RUN_ID[-6:]
        ls = conn.NewObject("СправочникМенеджер.ЛицевыеСчетаПайщиков").СоздатьЭлемент()
        ls.Код = ls_code
        ls.Владелец = fund
        ls.Пайщик = nominee
        ls.ВидЛицевогоСчета = conn.Перечисления.ВидыЛицевыхСчетов.СчетНоминальногоДержателя
        ls.ОбменДанными.Загрузка = True
        ls.Записать()
        ls_nd = ls.Ссылка

        fio = PREFIX + "Ivanov Ivan Ivanovich"
        nrd = "01_%s_MODE" % RUN_ID
        cobj = gman.СоздатьЭлемент()
        cobj.Наименование = fio
        cobj.НаименованиеПолное = fio
        cobj.Пайщик = True
        cobj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ФизЛицо
        cobj.ДатаРождения = birth
        cobj.Родитель = group
        cobj.ОбменДанными.Загрузка = True
        cobj.Записать()
        card = cobj.Ссылка

        rec = conn.РегистрыСведений.ФИОФизЛиц.СоздатьМенеджерЗаписи()
        rec.ФизЛицо = card
        rec.Период = period
        rec.Фамилия = "Ivanov"
        rec.Имя = "Ivan"
        rec.Отчество = "Ivanovich"
        rec.Записать(True)

        recn = conn.РегистрыСведений.ЗначенияСвойствОбъектов.СоздатьМенеджерЗаписи()
        recn.Объект = card
        recn.Свойство = prop
        recn.Значение = nrd
        recn.Записать()

        recp = conn.РегистрыСведений.ПаспортныеДанныеФизЛиц.СоздатьМенеджерЗаписи()
        recp.ФизЛицо = card
        recp.Период = date1c(conn, 2018, 5, 21)
        recp.ДокументВид = conn.Справочники.ДокументыУдостоверяющиеЛичность.ПаспортРФ
        recp.ДокументСерия = "6500"
        recp.ДокументНомер = "111111"
        recp.Записать()

        token = RUN_ID[-6:]
        unk0 = PREFIX + "Uex%s Aex%s Bex%s" % (token, token, token)
        unk1 = PREFIX + "Uxml%s Axml%s Bxml%s" % (token, token, token)
        unk2 = PREFIX + "Ucdf%s Acdf%s Bcdf%s" % (token, token, token)
        unk3 = PREFIX + "Unew%s Anew%s Bnew%s" % (token, token, token)
        unk_flags = PREFIX + "Uflg%s Aflg%s Bflg%s" % (token, token, token)
        unk_cp_only = PREFIX + "Ucpo%s Acpo%s Bcpo%s" % (token, token, token)
        addr0 = "addr-ex-%s" % RUN_ID
        addr1 = "addr-xml-%s" % RUN_ID
        addr2 = "addr-cdf-%s" % RUN_ID
        addr3 = "addr-new-%s" % RUN_ID
        addr_flags = "addr-flg-%s" % RUN_ID
        addr_cp = "addr-cpo-%s" % RUN_ID

        fio_dup_off = PREFIX + "Doff%s Eoff%s Foff%s" % (token, token, token)
        fio_dup_on = PREFIX + "Don%s Eon%s Fon%s" % (token, token, token)
        nrd_dup_off = "01_%s_DOFF" % RUN_ID
        nrd_dup_on = "01_%s_DON" % RUN_ID
        birth_dup = date1c(conn, 1966, 7, 7)

        def make_person(full_name, nrd_value):
            obj = gman.СоздатьЭлемент()
            obj.Наименование = full_name
            obj.НаименованиеПолное = full_name
            obj.Пайщик = True
            obj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ФизЛицо
            obj.ДатаРождения = birth_dup
            obj.Родитель = group
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
            ref = obj.Ссылка
            recf = conn.РегистрыСведений.ФИОФизЛиц.СоздатьМенеджерЗаписи()
            recf.ФизЛицо = ref
            recf.Период = period
            parts = full_name.split(" ")
            recf.Фамилия = parts[-3] if len(parts) >= 3 else parts[0]
            recf.Имя = parts[-2] if len(parts) >= 2 else "I"
            recf.Отчество = parts[-1]
            recf.Записать(True)
            recn2 = conn.РегистрыСведений.ЗначенияСвойствОбъектов.СоздатьМенеджерЗаписи()
            recn2.Объект = ref
            recn2.Свойство = prop
            recn2.Значение = nrd_value
            recn2.Записать()
            recp2 = conn.РегистрыСведений.ПаспортныеДанныеФизЛиц.СоздатьМенеджерЗаписи()
            recp2.ФизЛицо = ref
            recp2.Период = date1c(conn, 2018, 5, 21)
            recp2.ДокументВид = conn.Справочники.ДокументыУдостоверяющиеЛичность.ПаспортРФ
            recp2.ДокументСерия = "6500"
            recp2.ДокументНомер = "222222"
            recp2.Записать()
            return ref

        make_person(fio_dup_off, nrd_dup_off)
        make_person(fio_dup_on, nrd_dup_on)

        path0 = os.path.join(FIXTURES, "mode_garant.xlsx")
        path2 = os.path.join(FIXTURES, "mode_cdf.xlsx")
        path3 = os.path.join(FIXTURES, "mode_garant_new.xlsx")
        path1 = os.path.join(FIXTURES, "mode_vtb.xml")
        path_flags = os.path.join(FIXTURES, "mode_flags.xlsx")

        write_xlsx(
            conn,
            path0,
            {
                3: {
                    5: ADDRESS,
                    6: fio,
                    7: "10",
                    8: ADDRESS,
                    9: "24.03.1955",
                    16: "111111",
                    17: "6500",
                    19: nrd,
                },
                4: {
                    5: addr0,
                    6: unk0,
                    7: "2",
                    8: addr0,
                    9: "11.11.1991",
                    16: "000011",
                    17: "6500",
                    19: "01_%s_NONE0" % RUN_ID,
                },
            },
        )
        make_xml(
            path1,
            ls_code,
            [
                {"fio": fio, "dob": "24.03.1955", "shares": "8", "addr": ADDRESS},
                {"fio": unk1, "dob": "12.12.1992", "shares": "3", "addr": addr1},
            ],
        )
        write_xlsx(
            conn,
            path2,
            {
                2: {
                    3: nrd,
                    5: fio,
                    7: "24.03.1955",
                    9: "6500",
                    10: "111111",
                    13: ADDRESS,
                    14: ADDRESS,
                    19: "",
                    20: "12",
                    24: "24.03.1955",
                },
                3: {
                    3: "01_%s_NONE2" % RUN_ID,
                    5: unk2,
                    7: "13.03.1993",
                    10: "000022",
                    13: addr2,
                    14: addr2,
                    20: "4",
                    24: "13.03.1993",
                },
            },
        )
        write_xlsx(
            conn,
            path3,
            {
                3: {
                    1: fio,
                    5: "7",
                    6: ADDRESS,
                    14: "111111",
                    16: "6500",
                    19: "24.03.1955",
                },
                4: {
                    1: unk3,
                    5: "1",
                    6: addr3,
                    14: "000033",
                    16: "6500",
                    19: "14.04.1994",
                },
            },
        )
        write_xlsx(
            conn,
            path_flags,
            {
                3: {
                    5: addr_flags,
                    6: unk_flags,
                    7: "1",
                    8: addr_flags,
                    9: "15.05.1995",
                    16: "000044",
                    17: "6500",
                    19: "01_%s_NONEF" % RUN_ID,
                }
            },
        )
        path_mult_off = os.path.join(FIXTURES, "mode_multiply_off.xlsx")
        path_mult_on = os.path.join(FIXTURES, "mode_multiply_on.xlsx")
        write_xlsx(
            conn,
            path_mult_off,
            {
                3: {
                    5: ADDRESS,
                    6: fio_dup_off,
                    7: "3",
                    8: ADDRESS,
                    9: "07.07.1966",
                    16: "222222",
                    17: "6500",
                    19: nrd_dup_off,
                },
                4: {
                    5: ADDRESS,
                    6: fio_dup_off,
                    7: "4",
                    8: ADDRESS,
                    9: "07.07.1966",
                    16: "222222",
                    17: "6500",
                    19: nrd_dup_off,
                },
            },
        )
        write_xlsx(
            conn,
            path_mult_on,
            {
                3: {
                    5: ADDRESS,
                    6: fio_dup_on,
                    7: "3",
                    8: ADDRESS,
                    9: "07.07.1966",
                    16: "222222",
                    17: "6500",
                    19: nrd_dup_on,
                },
                4: {
                    5: ADDRESS,
                    6: fio_dup_on,
                    7: "4",
                    8: ADDRESS,
                    9: "07.07.1966",
                    16: "222222",
                    17: "6500",
                    19: nrd_dup_on,
                },
            },
        )

        params = proc.НовыйПараметрыНачитки()
        params.Фонд = fund
        params.НоминальныйДержатель = nominee
        params.ЛицевойСчет = ls_nd
        params.ГруппаКонтрагентов = group
        params.ДатаИсторическихЗначений = period
        params.ДатаОткрытияСчета = period
        params.ДатаДок = period
        params.ФлСоздаватьКонтрагентов = False
        params.ФлСоздаватьЛицевыеСчета = False
        params.МножитьЛицСчета = False

        defaults_ok = (
            bool(params.ФлСоздаватьКонтрагентов) is False
            and bool(params.ФлСоздаватьЛицевыеСчета) is False
            and bool(params.МножитьЛицСчета) is False
            and int(params.ФорматФайла) == 0
        )
        add_case(
            cases,
            "Default flags like empty form",
            defaults_ok,
            "createCP=%s createLS=%s multiply=%s format=%s"
            % (
                params.ФлСоздаватьКонтрагентов,
                params.ФлСоздаватьЛицевыеСчета,
                params.МножитьЛицСчета,
                params.ФорматФайла,
            ),
        )

        # Format 0
        params.ФорматФайла = 0
        t0 = proc.ПрочитатьФайлВТаблицу(path0, params)
        r0 = first_row(t0)
        add_case(
            cases,
            "Format 0 Garant Excel: read 2 rows",
            t0.Количество() == 2 and r0 is not None and str(r0.НРДid) == nrd,
            "rows=%s fio=%s nrd=%s shares=%s"
            % (
                t0.Количество(),
                getattr(r0, "ФИО", ""),
                getattr(r0, "НРДid", ""),
                getattr(r0, "КоличествоПаев", ""),
            ),
        )

        m0 = proc.СопоставитьСтрокиФайла(t0, params)
        ways = []
        empty_card = 0
        for i in range(m0.ТаблицаСтрок.Количество()):
            row = m0.ТаблицаСтрок[i]
            ways.append(str(row.СпособСопоставления))
            if not is_filled(row.Контрагент):
                empty_card += 1
        add_case(
            cases,
            "Format 0: match NRD + not found",
            "НРДid" in ways and empty_card == 1,
            "ways=%s empty=%s totals=%s" % (",".join(ways), empty_card, m0.ТекстИтогов),
        )

        # Format 1 XML
        params.ФорматФайла = 1
        t1 = proc.ПрочитатьФайлВТаблицу(path1, params)
        r1 = first_row(t1)
        add_case(
            cases,
            "Format 1 XML VTB SD: read by ND account",
            t1.Количество() == 2 and r1 is not None and "Ivanov" in str(r1.ФИО),
            "rows=%s fio=%s shares=%s dob=%s"
            % (
                t1.Количество(),
                getattr(r1, "ФИО", ""),
                getattr(r1, "КоличествоПаев", ""),
                getattr(r1, "ДатаРождения", ""),
            ),
        )
        m1 = proc.СопоставитьСтрокиФайла(t1, params)
        ways1 = [str(m1.ТаблицаСтрок[i].СпособСопоставления) for i in range(m1.ТаблицаСтрок.Количество())]
        add_case(
            cases,
            "Format 1: match by FIO+DOB (XML has no NRD id)",
            any("ФИО" in w for w in ways1),
            "ways=%s" % ",".join(ways1),
        )

        # XML filter: other account -> 0 rows
        xml_other = os.path.join(FIXTURES, "mode_vtb_other.xml")
        make_xml(xml_other, "OTHER999", [{"fio": fio, "dob": "24.03.1955", "shares": "1"}])
        t1f = proc.ПрочитатьФайлВТаблицу(xml_other, params)
        add_case(
            cases,
            "Format 1: skip other ND account",
            t1f.Количество() == 0,
            "rows=%s filter=%s" % (t1f.Количество(), ls_code),
        )

        # Format 2 CDF
        params.ФорматФайла = 2
        t2 = proc.ПрочитатьФайлВТаблицу(path2, params)
        r2 = first_row(t2)
        add_case(
            cases,
            "Format 2 CDF: NRD in column 3",
            t2.Количество() == 2 and r2 is not None and str(r2.НРДid) == nrd,
            "rows=%s fio=%s nrd=%s shares=%s"
            % (
                t2.Количество(),
                getattr(r2, "ФИО", ""),
                getattr(r2, "НРДid", ""),
                getattr(r2, "КоличествоПаев", ""),
            ),
        )
        m2 = proc.СопоставитьСтрокиФайла(t2, params)
        ways2 = [str(m2.ТаблицаСтрок[i].СпособСопоставления) for i in range(m2.ТаблицаСтрок.Количество())]
        add_case(
            cases,
            "Format 2: match by NRD id",
            "НРДid" in ways2,
            "ways=%s" % ",".join(ways2),
        )

        # Format 3 Garant NEW (no NRD column)
        params.ФорматФайла = 3
        t3 = proc.ПрочитатьФайлВТаблицу(path3, params)
        r3 = first_row(t3)
        add_case(
            cases,
            "Format 3 Garant Excel NEW: FIO in column 1",
            t3.Количество() == 2 and r3 is not None and "Ivanov" in str(r3.ФИО),
            "rows=%s fio=%s shares=%s nrd='%s'"
            % (
                t3.Количество(),
                getattr(r3, "ФИО", ""),
                getattr(r3, "КоличествоПаев", ""),
                getattr(r3, "НРДid", ""),
            ),
        )
        m3 = proc.СопоставитьСтрокиФайла(t3, params)
        ways3 = [str(m3.ТаблицаСтрок[i].СпособСопоставления) for i in range(m3.ТаблицаСтрок.Количество())]
        add_case(
            cases,
            "Format 3: match by FIO+DOB from registration text",
            any("ФИО" in w for w in ways3),
            "ways=%s" % ",".join(ways3),
        )

        # Flags: both off
        params.ФорматФайла = 0
        params.ФлСоздаватьКонтрагентов = False
        params.ФлСоздаватьЛицевыеСчета = False
        params.МножитьЛицСчета = False
        tf = proc.ПрочитатьФайлВТаблицу(path_flags, params)
        mf = proc.СопоставитьСтрокиФайла(tf, params)
        created_off = proc.СоздатьНедостающихПоСтрокам(mf.ТаблицаСтрок, params)
        add_case(
            cases,
            "Flags off: do not create counterparty or LS",
            int(created_off.СозданоКонтрагентов) == 0 and int(created_off.СозданоЛицевыхСчетов) == 0,
            "cp=%s ls=%s"
            % (created_off.СозданоКонтрагентов, created_off.СозданоЛицевыхСчетов),
        )

        # Flags: CP only
        path_cp = os.path.join(FIXTURES, "mode_cp_only.xlsx")
        write_xlsx(
            conn,
            path_cp,
            {
                3: {
                    5: addr_cp,
                    6: unk_cp_only,
                    7: "1",
                    8: addr_cp,
                    9: "16.06.1996",
                    16: "000055",
                    17: "6500",
                    19: "01_%s_NONEC" % RUN_ID,
                }
            },
        )
        params.ФлСоздаватьКонтрагентов = True
        params.ФлСоздаватьЛицевыеСчета = False
        tc = proc.ПрочитатьФайлВТаблицу(path_cp, params)
        mc = proc.СопоставитьСтрокиФайла(tc, params)
        created_cp = proc.СоздатьНедостающихПоСтрокам(mc.ТаблицаСтрок, params)
        add_case(
            cases,
            "Flag create counterparties ON, LS OFF",
            int(created_cp.СозданоКонтрагентов) == 1 and int(created_cp.СозданоЛицевыхСчетов) == 0,
            "cp=%s ls=%s"
            % (created_cp.СозданоКонтрагентов, created_cp.СозданоЛицевыхСчетов),
        )

        # Flags: both ON on remaining empty from format 0 table copy
        params.ФлСоздаватьКонтрагентов = True
        params.ФлСоздаватьЛицевыеСчета = True
        created_on = proc.СоздатьНедостающихПоСтрокам(m0.ТаблицаСтрок, params)
        add_case(
            cases,
            "Flags create counterparties and LS ON",
            int(created_on.СозданоКонтрагентов) >= 1 and int(created_on.СозданоЛицевыхСчетов) >= 1,
            "cp=%s ls=%s"
            % (created_on.СозданоКонтрагентов, created_on.СозданоЛицевыхСчетов),
        )

        # Multiply OFF: two file rows of same person -> one LS
        params.ФорматФайла = 0
        params.ФлСоздаватьКонтрагентов = False
        params.ФлСоздаватьЛицевыеСчета = True
        params.МножитьЛицСчета = False
        tm = proc.ПрочитатьФайлВТаблицу(path_mult_off, params)
        mm = proc.СопоставитьСтрокиФайла(tm, params)
        created_m_off = proc.СоздатьНедостающихПоСтрокам(mm.ТаблицаСтрок, params)
        uniq_off, keys_off = unique_ls(created_m_off.ТаблицаСтрок)
        add_case(
            cases,
            "Multiply LS OFF: same person twice -> one LS",
            len(uniq_off) == 1,
            "unique_ls=%s created_counter=%s keys=%s" % (len(uniq_off), created_m_off.СозданоЛицевыхСчетов, ",".join(keys_off)),
        )

        # Multiply ON: two file rows of another person -> two technical LS
        params.МножитьЛицСчета = True
        tm2 = proc.ПрочитатьФайлВТаблицу(path_mult_on, params)
        mm2 = proc.СопоставитьСтрокиФайла(tm2, params)
        created_m_on = proc.СоздатьНедостающихПоСтрокам(mm2.ТаблицаСтрок, params)
        uniq_on, keys_on = unique_ls(created_m_on.ТаблицаСтрок)
        qls2 = conn.NewObject("Запрос")
        qls2.Текст = (
            "ВЫБРАТЬ КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Ссылка) КАК Количество "
            "ИЗ Справочник.ЛицевыеСчетаПайщиков "
            "ГДЕ Пайщик.Наименование = &Имя И Владелец = &Фонд И НЕ ПометкаУдаления"
        )
        qls2.УстановитьПараметр("Имя", fio_dup_on)
        qls2.УстановитьПараметр("Фонд", fund)
        ls_in_ib = int(qls2.Выполнить().Выгрузить()[0].Количество)
        multiply_works = len(uniq_on) >= 2 or ls_in_ib >= 2
        add_case(
            cases,
            "Multiply LS ON: same person twice -> second technical LS",
            multiply_works,
            "unique_ls=%s created_counter=%s flag=%s ib_ls=%s keys=%s"
            % (len(uniq_on), created_m_on.СозданоЛицевыхСчетов, params.МножитьЛицСчета, ls_in_ib, ",".join(keys_on)),
            error="" if multiply_works else "Flag MnogitLitsScheta did not create a second LS",
        )

        seed = {
            "runId": RUN_ID,
            "prefix": PREFIX,
            "fund": fund_name,
            "group": group_name,
            "nominee": nominee_name,
            "fio": fio,
            "nrd": nrd,
            "lsCode": ls_code,
            "epf": EPF,
            "xlsx0": path0,
            "xml1": path1,
            "xlsx2": path2,
            "xlsx3": path3,
            "xlsxFlags": path_flags,
            "xlsxMult": path_mult_on,
            "unk0": unk0,
            "unk1": unk1,
            "unk2": unk2,
            "unk3": unk3,
        }
        with open(SEED_JSON, "w", encoding="utf-8") as f:
            json.dump(seed, f, ensure_ascii=False, indent=2)

        ok_count = sum(1 for c in cases if c["ok"])
        result = {
            "ok": ok_count,
            "total": len(cases),
            "cases": cases,
            "seed": seed,
            "multiplyImplemented": multiply_works,
        }
        with open(RESULT_JSON, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        safe_print("COM_MODES %s/%s" % (ok_count, len(cases)))
        return 0 if ok_count == len(cases) else 1
    except Exception as exc:
        add_case(cases, "COM modes aborted", False, error=com_err(exc))
        with open(RESULT_JSON, "w", encoding="utf-8") as f:
            json.dump({"ok": 0, "total": len(cases), "cases": cases, "seed": seed}, f, ensure_ascii=False, indent=2)
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
