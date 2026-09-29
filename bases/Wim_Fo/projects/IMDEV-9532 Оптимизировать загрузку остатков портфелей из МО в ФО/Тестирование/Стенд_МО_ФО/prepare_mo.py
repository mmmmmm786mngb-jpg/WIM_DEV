# -*- coding: utf-8 -*-
"""Подготовка тестовых данных МО (WIM_MO) для стенда выгрузки остатков МО -> ФО.

Создает, если еще нет:
- элемент справочника «Внешние информационные базы» с адресом публикации ФО стенда
  (МО-обработка 1.42 берет адрес веб-сервиса ФО из этого справочника);
- места хранения T9532_DEPO (счет депо) и T9532_BANK (банковский счет в рублях);
- ЦБ T9532_SH1..SH3 (структурные ноты) и активы к ним;
- мандаты T9532_0001..T9532_NNNN типа R (не ПИФ, поэтому в 872 уходит 3 флага на портфель);
- по два счета на мандат: депозитарный <код>_D и банковский <код>_B.

Объекты пишутся в режиме загрузки (ОбменДанными.Загрузка) и с дополнительным свойством
ОтключитьМеханизмРегистрацииОбъектов: тестовым справочникам не нужны прикладные обработчики записи, они не
должны попадать в обмены, а часть обработчиков МО (правила регистрации через ОписаниеОбменов, история
объектов) во внешнем соединении не работает. Повторный запуск ничего не дублирует.
"""
import time

from stand_common import (PREFIX, N_PORTFOLIOS, SHARES, WS_BASE, WS_NAME, EXTERNAL_IB_NAME, connect, query,
                          mandate_code, account_code, share_code)


def find_ref(conn, text_, params=None):
    rows = query(conn, text_, params)
    return rows[0]["Ссылка"] if rows else None


def write(obj):
    obj.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def ensure_external_ib(mo):
    ref = find_ref(mo, "ВЫБРАТЬ Сп.Ссылка КАК Ссылка ИЗ Справочник.ВнешниеИнформационныеБазы КАК Сп "
                       "ГДЕ Сп.Наименование = &Имя", {"Имя": EXTERNAL_IB_NAME})
    obj = ref.ПолучитьОбъект() if ref is not None else mo.Справочники.ВнешниеИнформационныеБазы.СоздатьЭлемент()
    obj.Наименование = EXTERNAL_IB_NAME
    obj.АдресWebСервиса = WS_BASE
    obj.ИмяWebСервиса = WS_NAME
    obj.ИмяПользователя = ""
    obj.ПарольПользователя = ""
    ref = write(obj)
    print(f"  внешняя ИБ «{EXTERNAL_IB_NAME}»: {WS_BASE}/ws/{WS_NAME}.1cws")
    return ref


def ensure_place(mo, catalog, code, name, extra):
    ref = find_ref(mo, f"ВЫБРАТЬ Сп.Ссылка КАК Ссылка ИЗ Справочник.{catalog} КАК Сп ГДЕ Сп.КодМестаХранения = &Код",
                   {"Код": code})
    if ref is not None:
        return ref
    obj = getattr(mo.Справочники, catalog).СоздатьЭлемент()
    obj.Наименование = name
    obj.КодМестаХранения = code
    for attr, value in extra.items():
        setattr(obj, attr, value)
    print(f"  создано место хранения {catalog} {code}")
    return write(obj)


def ensure_share(mo, k, rub):
    """Тестовая ЦБ МО. Создается структурной нотой: акции в МО охвачены подпиской истории объектов, которая
    во внешнем соединении не работает. ФО ищет актив позиции только по внешнему коду, вид ЦБ не важен."""
    code = share_code(k)
    security = find_ref(mo, "ВЫБРАТЬ Сн.Ссылка КАК Ссылка ИЗ Справочник.СтруктурныеНоты КАК Сн ГДЕ Сн.ВнешнийКод = &Код",
                        {"Код": code})
    if security is None:
        obj = mo.Справочники.СтруктурныеНоты.СоздатьЭлемент()
        obj.Наименование = f"{PREFIX} ЦБ {k}"
        obj.НаименованиеПолное = f"{PREFIX} ЦБ {k}"
        obj.ВнешнийКод = code
        obj.ВалютаНоминальнойСтоимости = rub
        security = write(obj)
        print(f"  создана ЦБ {code}")
    asset = find_ref(mo, "ВЫБРАТЬ Ак.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК Ак ГДЕ Ак.Объект = &Объект",
                     {"Объект": security})
    if asset is None:
        obj = mo.Справочники.Активы.СоздатьЭлемент()
        obj.Наименование = f"{PREFIX} ЦБ {k}"
        obj.Объект = security
        obj.ВнешнийКод = code
        asset = write(obj)
        print(f"  создан актив {code}")
    return asset


def ensure_mandates(mo, rub, depo, bank):
    mandates = {r["Код"]: r["Ссылка"] for r in query(
        mo, "ВЫБРАТЬ М.КодМандата КАК Код, М.Ссылка КАК Ссылка ИЗ Справочник.Мандаты КАК М ГДЕ М.КодМандата ПОДОБНО &Маска",
        {"Маска": PREFIX + "%"})}
    accounts = {r["Код"] for r in query(
        mo, "ВЫБРАТЬ С.КодСчета КАК Код ИЗ Справочник.СчетаМандатов КАК С ГДЕ С.КодСчета ПОДОБНО &Маска",
        {"Маска": PREFIX + "%"})}
    kinds = mo.ПланыВидовХарактеристик.ВидыСчетаМандата
    account_kinds = {"D": (kinds.Депозитарный, depo), "B": (kinds.Банковский, bank)}
    created_mandates = created_accounts = 0
    started = time.perf_counter()
    for i in range(1, N_PORTFOLIOS + 1):
        code = mandate_code(i)
        ref = mandates.get(code)
        if ref is None:
            obj = mo.Справочники.Мандаты.СоздатьЭлемент()
            obj.Наименование = f"{PREFIX} Мандат {i:04d}"
            obj.КодМандата = code
            obj.ТипМандата = mo.Перечисления.ТипыМандата.R
            obj.ВалютаМандата = rub
            ref = write(obj)
            created_mandates += 1
        for kind, (account_kind, place) in account_kinds.items():
            acc_code = account_code(i, kind)
            if acc_code in accounts:
                continue
            obj = mo.Справочники.СчетаМандатов.СоздатьЭлемент()
            obj.Владелец = ref
            obj.Наименование = acc_code
            obj.КодСчета = acc_code
            obj.ВидСчетаМандата = account_kind
            obj.МестоХранения = place
            write(obj)
            created_accounts += 1
        if i % 50 == 0:
            print(f"  мандатов обработано {i}/{N_PORTFOLIOS}, {time.perf_counter() - started:.0f} с")
    print(f"  создано мандатов {created_mandates}, счетов {created_accounts}")


def main():
    mo = connect("wim_mo")
    rub = find_ref(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = &Код", {"Код": "643"})
    if rub is None:
        raise SystemExit("В МО нет валюты с кодом 643")
    print("МО: подключение к ФО")
    ensure_external_ib(mo)
    print("МО: места хранения")
    depo = ensure_place(mo, "СчетаДЕПО", f"{PREFIX}_DEPO", f"{PREFIX} Счет депо", {})
    bank = ensure_place(mo, "БанковскиеСчета", f"{PREFIX}_BANK", f"{PREFIX} Банковский счет", {"Валюта": rub})
    print("МО: ЦБ")
    for k in range(1, SHARES + 1):
        ensure_share(mo, k, rub)
    print("МО: мандаты и счета")
    ensure_mandates(mo, rub, depo, bank)
    print("МО: готово")


if __name__ == "__main__":
    main()
