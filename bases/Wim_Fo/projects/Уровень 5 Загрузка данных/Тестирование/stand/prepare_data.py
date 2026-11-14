#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подготовка малого набора данных стенда уровня 5.

Префикс T5L5. Повторный запуск не создает дубликаты.
Чужой элемент с тем же префиксом останавливает подготовку.
"""

import sys

from stand_common import PREFIX, connect, load_state, query_rows, save_state

sys.stdout.reconfigure(encoding="utf-8")

INN = "7705123452"
SHARE_CODES = ("T5L5Q01", "T5L5Q02")
INDEX_CODES = ("T5L5IX1", "T5L5IX2")
MANDATE_COUNT = 3
COUNTERPARTY_NAME = PREFIX + " Kontragent"


def log(text):
    print(text)


def find_rows(conn, text, params=None):
    return query_rows(conn, text, params)


def find_one(conn, text, params=None):
    rows = find_rows(conn, text, params)
    if not rows:
        return None
    return rows[0]["Ссылка"]


def expected_names():
    names = {COUNTERPARTY_NAME}
    for code in SHARE_CODES:
        names.add("%s Akciya %s" % (PREFIX, code))
    for index, code in enumerate(INDEX_CODES, 1):
        names.add("%s Indeks %s" % (PREFIX, code))
    return names


def stop_on_foreign(conn, text, params, allowed):
    rows = find_rows(conn, text, params)
    foreign = []
    for row in rows:
        name = str(row["Имя"])
        if name not in allowed:
            foreign.append(name)
    if foreign:
        log("FAIL foreign prefix items: %s" % ", ".join(foreign))
        raise SystemExit(1)
    return len(rows)


def ensure_counterparty(fo):
    ref = find_one(
        fo,
        "ВЫБРАТЬ К.Ссылка КАК Ссылка ИЗ Справочник.Контрагенты КАК К ГДЕ К.Наименование = &Имя",
        {"Имя": COUNTERPARTY_NAME},
    )
    if ref is not None:
        log("FO counterparty exists")
        return False
    obj = fo.Справочники.Контрагенты.СоздатьЭлемент()
    obj.Наименование = COUNTERPARTY_NAME
    obj.НаименованиеПолное = COUNTERPARTY_NAME
    obj.ИНН = INN
    obj.Записать()
    log("FO counterparty created")
    return True


def ensure_tcris(fo):
    rows = find_rows(
        fo,
        "ВЫБРАТЬ Св.Ссылка КАК Ссылка ИЗ ПланВидовХарактеристик.ДополнительныеРеквизитыИСведения КАК Св "
        "ГДЕ Св.Наименование = &Имя",
        {"Имя": "TCRIS"},
    )
    if len(rows) > 1:
        log("FAIL more than one TCRIS property")
        raise SystemExit(1)
    if rows:
        log("TCRIS property exists")
        return False
    obj = fo.ПланыВидовХарактеристик.ДополнительныеРеквизитыИСведения.СоздатьЭлемент()
    obj.Наименование = "TCRIS"
    obj.Заголовок = "TCRIS"
    obj.Имя = "TCRIS"
    obj.ТипЗначения = fo.NewObject("ОписаниеТипов", "Число")
    obj.ЭтоДополнительноеСведение = True
    obj.Доступен = True
    obj.Виден = True
    obj.Записать()
    log("TCRIS property created")
    return True


def ensure_shares(fo):
    sample = find_one(
        fo,
        "ВЫБРАТЬ ПЕРВЫЕ 1 А.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК А "
        "ГДЕ НЕ А.ПометкаУдаления И А.Эмитент <> ЗНАЧЕНИЕ(Справочник.Контрагенты.ПустаяСсылка) "
        "И НЕ А.Наименование ПОДОБНО &Маска УПОРЯДОЧИТЬ ПО А.Наименование",
        {"Маска": PREFIX + "%"},
    )
    if sample is None:
        log("FAIL no sample share on FO")
        raise SystemExit(1)
    mmvb = fo.Справочники.Биржи.ММВБ
    created = 0
    for code in SHARE_CODES:
        name = "%s Akciya %s" % (PREFIX, code)
        ref = find_one(
            fo,
            "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК А ГДЕ А.Наименование = &Имя",
            {"Имя": name},
        )
        if ref is None:
            obj = sample.Скопировать()
            obj.Наименование = name
            obj.НаименованиеПолное = name
            obj.КраткоеНаименование = code
            obj.ВнешнийКод = code
            obj.ISIN = ""
            obj.НомерГосРегистрацииВыпуска = ""
            obj.СобиратьНаименованиеАвтоматически = False
            obj.БиржиЛистинга.Очистить()
            row = obj.БиржиЛистинга.Добавить()
            row.Биржа = mmvb
            row.Тикер = code
            obj.Записать()
            ref = obj.Ссылка
            created += 1
            log("FO share created %s" % code)
        asset = find_one(
            fo,
            "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А ГДЕ А.Объект = &Объект",
            {"Объект": ref},
        )
        if asset is None:
            asset_obj = fo.Справочники.Активы.СоздатьЭлемент()
            asset_obj.Объект = ref
            asset_obj.ВидАктива = ref.ВидАктива
            asset_obj.Эмитент = ref.Эмитент
            asset_obj.ВалютаНоминальнойСтоимости = ref.ВалютаНоминальнойСтоимости
            asset_obj.Наименование = name
            asset_obj.ВнешнийКод = code
            asset_obj.Записать()
            log("FO asset created %s" % code)
    return created


def ensure_indexes(fo):
    rub = fo.Справочники.Валюты.НайтиПоНаименованию("RUB")
    created = 0
    for code in INDEX_CODES:
        name = "%s Indeks %s" % (PREFIX, code)
        ref = find_one(
            fo,
            "ВЫБРАТЬ Инд.Ссылка КАК Ссылка ИЗ Справочник.Индексы КАК Инд ГДЕ Инд.КодИндекса = &Код",
            {"Код": code},
        )
        if ref is None:
            obj = fo.Справочники.Индексы.СоздатьЭлемент()
            obj.Наименование = name
            obj.КодИндекса = code
            obj.ВнешнийКод = code
            obj.Валюта = rub
            obj.Биржа = fo.Справочники.Биржи.ММВБ
            obj.Записать()
            created += 1
            log("FO index created %s" % code)
    return created


def write_loaded(obj):
    # Как в стенде остатков: иначе подписка регистрации обмена во внешнем соединении срывает запись.
    obj.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def ensure_place(mo, catalog, code, name, extra):
    ref = find_one(
        mo,
        "ВЫБРАТЬ Сп.Ссылка КАК Ссылка ИЗ Справочник.%s КАК Сп ГДЕ Сп.КодМестаХранения = &Код" % catalog,
        {"Код": code},
    )
    if ref is not None:
        return ref
    obj = getattr(mo.Справочники, catalog).СоздатьЭлемент()
    obj.Наименование = name
    obj.КодМестаХранения = code
    for attr, value in extra.items():
        setattr(obj, attr, value)
    log("MO place created %s" % code)
    return write_loaded(obj)


def ensure_mandates(mo):
    rub = find_one(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = &Код", {"Код": "643"})
    if rub is None:
        log("FAIL no currency 643 on MO")
        raise SystemExit(1)
    depo = ensure_place(mo, "СчетаДЕПО", PREFIX + "_DEPO", PREFIX + " Depo", {})
    bank = ensure_place(
        mo,
        "БанковскиеСчета",
        PREFIX + "_BANK",
        PREFIX + " Bank",
        {"Валюта": rub, "НомерСчета": PREFIX + "BANK"},
    )
    kinds = mo.ПланыВидовХарактеристик.ВидыСчетаМандата
    account_kinds = {"D": (kinds.Депозитарный, depo), "B": (kinds.Банковский, bank)}
    created = 0
    for index in range(1, MANDATE_COUNT + 1):
        code = "%s_%04d" % (PREFIX, index)
        ref = find_one(
            mo,
            "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.Мандаты КАК М ГДЕ М.КодМандата = &Код",
            {"Код": code},
        )
        if ref is None:
            obj = mo.Справочники.Мандаты.СоздатьЭлемент()
            obj.Наименование = "%s Mandat %04d" % (PREFIX, index)
            obj.КодМандата = code
            obj.ТипМандата = mo.Перечисления.ТипыМандата.R
            obj.ВалютаМандата = rub
            ref = write_loaded(obj)
            created += 1
            log("MO mandate created %s" % code)
        for kind, (account_kind, place) in account_kinds.items():
            acc_code = "%s_%s" % (code, kind)
            exists = find_one(
                mo,
                "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Справочник.СчетаМандатов КАК С ГДЕ С.КодСчета = &Код",
                {"Код": acc_code},
            )
            if exists is not None:
                continue
            acc = mo.Справочники.СчетаМандатов.СоздатьЭлемент()
            acc.Владелец = ref
            acc.Наименование = acc_code
            acc.КодСчета = acc_code
            acc.ВидСчетаМандата = account_kind
            acc.МестоХранения = place
            write_loaded(acc)
            log("MO account created %s" % acc_code)
    return created


def main():
    fo = connect("wim_fo")
    allowed = expected_names()
    stop_on_foreign(
        fo,
        "ВЫБРАТЬ К.Наименование КАК Имя ИЗ Справочник.Контрагенты КАК К ГДЕ К.Наименование ПОДОБНО &Маска",
        {"Маска": PREFIX + "%"},
        allowed,
    )
    stop_on_foreign(
        fo,
        "ВЫБРАТЬ А.Наименование КАК Имя ИЗ Справочник.Акции КАК А ГДЕ А.Наименование ПОДОБНО &Маска",
        {"Маска": PREFIX + "%"},
        allowed,
    )
    stop_on_foreign(
        fo,
        "ВЫБРАТЬ Инд.Наименование КАК Имя ИЗ Справочник.Индексы КАК Инд ГДЕ Инд.Наименование ПОДОБНО &Маска",
        {"Маска": PREFIX + "%"},
        allowed,
    )
    created_counterparty = ensure_counterparty(fo)
    created_property = ensure_tcris(fo)
    ensure_shares(fo)
    ensure_indexes(fo)

    mo = connect("wim_mo")
    allowed_codes = {"%s_%04d" % (PREFIX, i) for i in range(1, MANDATE_COUNT + 1)}
    allowed_codes.update({PREFIX + "_DEPO", PREFIX + "_BANK"})
    for index in range(1, MANDATE_COUNT + 1):
        code = "%s_%04d" % (PREFIX, index)
        allowed_codes.add(code + "_D")
        allowed_codes.add(code + "_B")
    stop_on_foreign(
        mo,
        "ВЫБРАТЬ М.КодМандата КАК Имя ИЗ Справочник.Мандаты КАК М ГДЕ М.КодМандата ПОДОБНО &Маска",
        {"Маска": PREFIX + "%"},
        allowed_codes,
    )
    ensure_mandates(mo)

    state = load_state()
    state["data"] = {
        "prefix": PREFIX,
        "inn": INN,
        "counterparty": COUNTERPARTY_NAME,
        "shares": list(SHARE_CODES),
        "indexes": list(INDEX_CODES),
        "mandates": MANDATE_COUNT,
        "tcris_created": created_property,
        "counterparty_created": created_counterparty,
    }
    save_state(state)
    log("OK prepare")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
