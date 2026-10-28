#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый стенд депозитов ПИФ.

Создает помеченные объекты TESTKURSORA и проводки регистра Управленческий,
чтобы сравнить исходный пакет getDeposits и ускоренный вариант.
"""

import json
import os
import sys
import time
import traceback

import pythoncom
import win32com.client


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_PATH = os.path.join(ROOT, "seed_log.txt")
MANIFEST_PATH = os.path.join(ROOT, "stand_manifest.json")
CONNECT = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
MARKER = "TESTKURSORA"

DEPOSIT_COUNT = 16
CASH_NOISE_ON_DEPOSITS = 5000
CASH_NOISE_BEFORE = 5000
INTEREST_NOISE_BEFORE = 5000
BATCH = 1000


def log(text):
    line = "%s %s" % (time.strftime("%H:%M:%S"), text)
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def regulated_currency(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ\n"
        "    ВЫБОР\n"
        "        КОГДА Константы.ВалютаРегламентированногоУчета = ЗНАЧЕНИЕ(Справочник.Валюты.ПустаяСсылка)\n"
        "            ТОГДА ЗНАЧЕНИЕ(Справочник.Валюты.RUB)\n"
        "        ИНАЧЕ Константы.ВалютаРегламентированногоУчета\n"
        "    КОНЕЦ КАК Валюта\n"
        "ИЗ\n"
        "    Константы КАК Константы"
    )
    return query.Выполнить().Выгрузить()[0].Валюта


def make_date(conn, year, month, day):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d) КАК Д" % (year, month, day)
    return query.Выполнить().Выгрузить()[0].Д


def find_by_name(conn, catalog_name, name):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s ГДЕ Наименование = &Имя" % catalog_name
    )
    query.УстановитьПараметр("Имя", name)
    table = query.Выполнить().Выгрузить()
    if table.Количество() == 0:
        return None
    return table[0].Ссылка


def ensure_catalog(conn, catalog_name, name, filler):
    found = find_by_name(conn, catalog_name, name)
    if found is not None:
        return found
    manager = conn.NewObject("СправочникМенеджер." + catalog_name)
    item = manager.СоздатьЭлемент()
    item.Наименование = name
    filler(item)
    item.Записать()
    return item.Ссылка


def new_document(conn, moment):
    manager = conn.NewObject("ДокументМенеджер.КорректировкаЗаписейРегистров")
    document = manager.СоздатьДокумент()
    document.Дата = moment
    document.Комментарий = MARKER
    document.ОтключитьСинхронизациюСтоимостиАктивов = True
    document.Записать()
    return document.Ссылка


def new_record_set(conn, registrar):
    record_set = conn.РегистрыБухгалтерии.Управленческий.СоздатьНаборЗаписей()
    record_set.Отбор.Регистратор.Установить(registrar)
    exchange = record_set.ОбменДанными
    exchange.Загрузка = True
    return record_set


def set_subconto(row, side, value, kind):
    collection = getattr(row, "Субконто" + side)
    collection.Вставить(kind, value)


def add_entry(record_set, period, fund, debit, credit, amount, kind, debit_sub=None, credit_sub=None,
              currency=None, currency_amount=None):
    row = record_set.Добавить()
    row.Период = period
    row.ПИФ = fund
    row.СчетДт = debit
    row.СчетКт = credit
    row.Сумма = amount
    row.Содержание = MARKER
    row.Активность = True
    if debit_sub is not None:
        set_subconto(row, "Дт", debit_sub, kind)
    if credit_sub is not None:
        set_subconto(row, "Кт", credit_sub, kind)
    if currency is not None:
        row.ВалютаДт = currency
        row.ВалютнаяСуммаДт = amount if currency_amount is None else currency_amount
    return row


def write_batches(conn, period, fund, count, builder, label):
    written = 0
    while written < count:
        portion = min(BATCH, count - written)
        registrar = new_document(conn, period)
        record_set = new_record_set(conn, registrar)
        for index in range(portion):
            builder(record_set, written + index)
        started = time.perf_counter()
        record_set.Записать()
        written += portion
        log("%s %s/%s batch_sec=%.2f" % (label, written, count, time.perf_counter() - started))
    return written


def main():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)
    pythoncom.CoInitialize()
    try:
        log("connect")
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONNECT)
        open_date = make_date(conn, 2024, 1, 15)
        noise_after = make_date(conn, 2025, 3, 1)
        noise_before = make_date(conn, 2012, 1, 1)
        interest_1 = make_date(conn, 2025, 1, 15)
        interest_2 = make_date(conn, 2025, 6, 15)
        interest_day = make_date(conn, 2026, 10, 28)
        query_date = make_date(conn, 2026, 10, 28)

        rub = regulated_currency(conn)
        usd = conn.Справочники.Валюты.USD
        account_51 = conn.ПланыСчетов.Управленческий.РасчетныеСчета
        account_52 = conn.ПланыСчетов.Управленческий.ВалютныеСчета
        account_76 = conn.ПланыСчетов.Управленческий.РасчетыПроцентыБанковскийДепозит
        account_91 = conn.ПланыСчетов.Управленческий.ПроцентыДепозиты
        account_000 = conn.ПланыСчетов.Управленческий.Вспомогательный

        bank = ensure_catalog(conn, "Банки", MARKER + " BANK", lambda item: None)
        fund = ensure_catalog(conn, "ПИФ", MARKER + " PIF", lambda item: setattr(item, "Префикс", "001"))
        log("refs ready")

        deposits = []
        for index in range(DEPOSIT_COUNT):
            currency_account = index >= 12
            name = "%s DEP %02d" % (MARKER, index + 1)
            nominal = 1000000 + index * 1000
            rate = 8 + index * 0.25

            def filler(item, currency_account=currency_account, nominal=nominal, rate=rate, index=index):
                item.Владелец = fund
                item.Банк = bank
                item.НомерСчета = "40702810%012d" % (index + 1)
                item.НачислениеПроцентов = True
                item.ДатаОткрытия = open_date
                item.НоминалДепозита = nominal
                item.ГодоваяПроцентнаяСтавка = rate
                item.ВалютаДенежныхСредств = usd if currency_account else rub
                item.ВидСчета = conn.Перечисления.ВидБанковскогоСчета.Депозитный

            account = ensure_catalog(conn, "БанковскиеСчета", name, filler)
            deposits.append({
                "name": name,
                "ref": account,
                "nominal": nominal,
                "currency_account": currency_account,
                "with_algorithm": index != 15,
            })
        def fill_noise(item):
            item.Владелец = fund
            item.Банк = bank
            item.НомерСчета = "40702810000000000099"
            item.НачислениеПроцентов = False
            item.ВалютаДенежныхСредств = rub
            item.ВидСчета = conn.Перечисления.ВидБанковскогоСчета.Расчетный

        noise_account = ensure_catalog(conn, "БанковскиеСчета", MARKER + " NOISE", fill_noise)
        log("accounts %s" % len(deposits))
        kind = conn.ПланыВидовХарактеристик.ВидыСубконто.БанковскиеСчета

        # Пилот: одна выдача и проверка, что субконто и итоги читаются.
        pilot = deposits[0]
        registrar = new_document(conn, open_date)
        record_set = new_record_set(conn, registrar)
        add_entry(record_set, open_date, fund, account_51, account_000, pilot["nominal"], kind,
                  debit_sub=pilot["ref"])
        record_set.Записать()
        check = conn.NewObject("Запрос")
        check.Текст = (
            "ВЫБРАТЬ\n"
            "    КОЛИЧЕСТВО(*) КАК Движений,\n"
            "    СУММА(Движения.Сумма) КАК Сумма\n"
            "ИЗ\n"
            "    РегистрБухгалтерии.Управленческий.ДвиженияССубконто(, , СубконтоДт1 = &Счет) КАК Движения"
        )
        check.УстановитьПараметр("Счет", pilot["ref"])
        row = check.Выполнить().Выгрузить()[0]
        log("pilot movements=%s sum=%s" % (row.Движений, row.Сумма))
        if int(row.Движений) < 1:
            raise RuntimeError("pilot movement was not readable")

        balance = conn.NewObject("Запрос")
        balance.Текст = (
            "ВЫБРАТЬ\n"
            "    УправленческийОстатки.СуммаОстатокДт КАК Остаток\n"
            "ИЗ\n"
            "    РегистрБухгалтерии.Управленческий.Остатки(\n"
            "        &Дата,\n"
            "        Счет = &Счет51,\n"
            "        ,\n"
            "        Субконто1 = &БанковскийСчет) КАК УправленческийОстатки"
        )
        balance.УстановитьПараметр("Дата", query_date)
        balance.УстановитьПараметр("Счет51", account_51)
        balance.УстановитьПараметр("БанковскийСчет", pilot["ref"])
        balance_table = balance.Выполнить().Выгрузить()
        balance_value = balance_table[0].Остаток if balance_table.Количество() else None
        log("pilot balance=%s" % balance_value)

        for index, deposit in enumerate(deposits):
            if index == 0:
                continue
            debit = account_52 if deposit["currency_account"] else account_51
            currency = usd if deposit["currency_account"] else None
            registrar = new_document(conn, open_date)
            record_set = new_record_set(conn, registrar)
            add_entry(
                record_set, open_date, fund, debit, account_000, deposit["nominal"], kind,
                debit_sub=deposit["ref"], currency=currency,
            )
            record_set.Записать()
        log("issuance written")

        registrar = new_document(conn, interest_1)
        record_set = new_record_set(conn, registrar)
        for deposit in deposits:
            currency = usd if deposit["currency_account"] else rub
            for moment, amount in ((interest_1, 100), (interest_2, 200), (interest_day, 50)):
                add_entry(
                    record_set, moment, fund, account_76, account_91, amount, kind,
                    credit_sub=deposit["ref"], currency=currency,
                )
        record_set.Записать()
        log("interest written")

        for deposit in deposits:
            if not deposit["with_algorithm"]:
                continue
            manager = conn.РегистрыСведений.АлгоритмыРасчетаПроцентов.СоздатьМенеджерЗаписи()
            manager.Период = open_date
            manager.Объект = deposit["ref"]
            manager.Записать()
        log("algorithms written")

        def cash_on_deposits(record_set, index):
            deposit = deposits[index % DEPOSIT_COUNT]
            debit = account_52 if deposit["currency_account"] else account_51
            currency = usd if deposit["currency_account"] else None
            add_entry(
                record_set, noise_after, fund, debit, account_000, 1, kind,
                debit_sub=deposit["ref"], currency=currency,
            )

        def cash_before(record_set, index):
            add_entry(
                record_set, noise_before, fund, account_51, account_000, 1, kind,
                debit_sub=noise_account,
            )

        def interest_before(record_set, index):
            add_entry(
                record_set, noise_before, fund, account_76, account_91, 1, kind,
                credit_sub=noise_account, currency=rub,
            )

        write_batches(conn, noise_after, fund, CASH_NOISE_ON_DEPOSITS, cash_on_deposits, "cash_after")
        write_batches(conn, noise_before, fund, CASH_NOISE_BEFORE, cash_before, "cash_before")
        write_batches(conn, noise_before, fund, INTEREST_NOISE_BEFORE, interest_before, "interest_before")

        total = conn.NewObject("Запрос")
        total.Текст = "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Движений ИЗ РегистрБухгалтерии.Управленческий КАК Движения"
        total_row = total.Выполнить().Выгрузить()[0]
        manifest = {
            "marker": MARKER,
            "deposits": DEPOSIT_COUNT,
            "cash_noise_on_deposits": CASH_NOISE_ON_DEPOSITS,
            "cash_noise_before": CASH_NOISE_BEFORE,
            "interest_noise_before": INTEREST_NOISE_BEFORE,
            "movements": int(total_row.Движений),
            "query_date": "2026-10-28",
            "open_date": "2024-01-15",
            "pilot_balance": None if balance_value is None else float(balance_value),
            "account_without_algorithm": deposits[15]["name"],
        }
        with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
        log("SEED_DONE movements=%s" % manifest["movements"])
    except Exception:
        log("SEED_ERROR")
        log(traceback.format_exc())
        return 1
    finally:
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
