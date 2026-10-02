# -*- coding: utf-8 -*-
"""Тестовые сделки для проверки замера исполнения сделок (IMDEV-9530, этап 3) на разработческой ФО.

В разработческой базе нет сделок с остатками плановой позиции, поэтому сделки загружаются штатно: пакетом с
разделом Документы.СделкаСЦеннымиБумагами через веб-сервис ФО (операция DownloadPosition, как у выгрузок МО).
ФО создает и проводит документы Сделка, проведение пишет приход в ПлановаяПозиция по бумаге и по деньгам.

Набор сделок: 4 сделки покупки по 3 тестовым портфелям T9532 (портфель 0002 - две сделки), бумаги T9532_SH1..3,
дата сделки и дата поставки - одна дата. Внебиржевая = Ложь, поручения нет: такие сделки отбирает групповое
исполнение. Места хранения - тестовые элементы стенда IMDEV-9532 "T9532 Банковский счет" (деньги) и
"T9532 Счет депо" (бумаги): загрузка ищет место хранения по внешнему коду, поэтому на время теста им присваиваются
коды T9530_BANK и T9530_DEPO (команда restore возвращает пустые коды).

    python prepare_deals.py <ГГГГ-ММ-ДД> <серия>   - загрузить набор сделок на дату; серия различает наборы
    python prepare_deals.py check <ГГГГ-ММ-ДД>      - сделки T9530 на дату и остатки плановой позиции по ним
    python prepare_deals.py restore                 - очистить внешние коды мест хранения после тестов
    python prepare_deals.py affiliates              - пакет Справочники.Контрагенты: 3 тестовых контрагента T9530,
                                                      у первого 2 аффилированных лица (проверка замера
                                                      ОбменБэкОфис.Справочники.АффилированныеЛица)
"""
import datetime
import glob
import sys

STAND = glob.glob(r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО')[0]
sys.path.insert(0, STAND)
from stand_common import WS_BASE, WS_NAME, _registry_db, connect, date_1c, query  # noqa: E402

NS = "http://avancore.ru/xsd"
PLACES = {"МестоХранения": ("T9532 Банковский счет", "T9530_BANK"), "МестоХраненияЦБ": ("T9532 Счет депо", "T9530_DEPO")}
DEALS = [  # портфель, бумага, количество, цена
    ("T9532_0001", "T9532_SH1", 10, 100),
    ("T9532_0002", "T9532_SH2", 20, 50),
    ("T9532_0002", "T9532_SH3", 5, 200),
    ("T9532_0003", "T9532_SH1", 15, 100),
]


def set_place_codes(fo, restore=False):
    for name, code in PLACES.values():
        rows = query(fo, "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.МестаХранения КАК М ГДЕ М.Наименование = &Имя",
                     {"Имя": name})
        if len(rows) != 1:
            raise SystemExit(f"место хранения {name}: найдено {len(rows)}")
        # Внешний код места хранения при записи берется из его объекта (счета), поэтому код задается счету.
        account = rows[0]["Ссылка"].Объект.ПолучитьОбъект()
        target = "" if restore else code
        if account.ВнешнийКод != target:
            account.ВнешнийКод = target
            account.Записать()
        saved = query(fo, "ВЫБРАТЬ М.ВнешнийКод КАК Код ИЗ Справочник.МестаХранения КАК М ГДЕ М.Наименование = &Имя",
                      {"Имя": name})[0]["Код"]
        print(f"место хранения {name}: внешний код '{saved}'")
        if saved != target:
            raise SystemExit("внешний код места хранения не установлен")


def proxy(fo):
    db = _registry_db("wim_fo")
    url = f"{WS_BASE}/ws/{WS_NAME}.1cws?wsdl"
    definition = fo.NewObject("WSОпределения", url, db["user"], db.get("password", ""))
    service = definition.Сервисы.Получить(0)
    point = service.ТочкиПодключения.Получить(0)
    ws = fo.NewObject("WSПрокси", definition, service.URIПространстваИмен, service.Имя, point.Имя)
    ws.Пользователь = db["user"]
    ws.Пароль = db.get("password", "")
    return ws


def create(factory, owner, name):
    return factory.Создать(owner.Свойства().Получить(name).Тип)


def build_packet(fo, factory, day, series):
    packet = factory.Создать(factory.Тип(NS, "Пакет"))
    packet.КлючПоискаАктивов = "Упрощенный"
    header = factory.Создать(factory.Тип(NS, "Заголовок"))
    header.УникальныйИдентификатор = fo.String(fo.NewObject("УникальныйИдентификатор"))
    header.ДатаВыполнения = fo.ТекущаяДатаСеанса()
    header.ИдентификаторСистемы = "IMDEV-9530 стенд"
    header.ИмяПользователя = "Сервис"
    header.ДатаВыгрузки = date_1c(fo, day)
    header.Комментарий = f"Тестовые сделки T9530, серия {series}"
    packet.Заголовок = header
    packet.Документы = create(factory, packet, "Документы")
    deal_time = date_1c(fo, day.replace(hour=10))
    for number, (portfolio, share, quantity, price) in enumerate(DEALS, start=1):
        deal = create(factory, packet.Документы, "СделкаСЦеннымиБумагами")
        code = f"T9530_{series}_{number}"
        deal.ВнешнийКод = code
        deal.НомерСделки = code
        deal.Дата = deal_time
        deal.РучнаяКорректировка = False
        deal.Проведен = True
        deal.ПометкаУдаления = False
        deal.Внебиржевая = False
        deal.ВидОперации = "Сделка"
        deal.Направление = "Покупка"
        deal.ДатаПоставки = date_1c(fo, day)
        deal.ДатаОплаты = date_1c(fo, day)
        deal.Цена = price
        deal.Количество = quantity
        deal.Сумма = quantity * price
        deal.СуммаРасчетов = quantity * price
        deal.КомиссияБрокера = 0
        deal.КомиссияБиржи = 0
        asset = create(factory, deal, "Актив")
        asset.ВнешнийКод = share
        deal.Актив = asset
        currency = create(factory, deal, "ВалютаРасчетов")
        currency.Код = "643"
        deal.ВалютаРасчетов = currency
        row = create(factory, deal, "РаспределениеПоПортфелям")
        row_portfolio = create(factory, row, "Портфель")
        row_portfolio.ВнешнийКод = portfolio
        row.Портфель = row_portfolio
        for place_property, (_, place_code) in PLACES.items():
            place = create(factory, row, place_property)
            place.ВнешнийКод = place_code
            setattr(row, place_property, place)
        row.Количество = quantity
        row.Сумма = quantity * price
        row.СуммаРасчетов = quantity * price
        row.СуммаКупона = 0
        row.КомиссияБрокера = 0
        row.КомиссияБиржи = 0
        deal.РаспределениеПоПортфелям.Добавить(row)
        packet.Документы.СделкаСЦеннымиБумагами.Добавить(deal)
    return packet


def build_affiliates_packet(fo, factory):
    packet = factory.Создать(factory.Тип(NS, "Пакет"))
    header = factory.Создать(factory.Тип(NS, "Заголовок"))
    header.УникальныйИдентификатор = fo.String(fo.NewObject("УникальныйИдентификатор"))
    header.ДатаВыполнения = fo.ТекущаяДатаСеанса()
    header.ИдентификаторСистемы = "IMDEV-9530 стенд"
    header.ИмяПользователя = "Сервис"
    header.Комментарий = "Тестовые контрагенты T9530 с аффилированными лицами"
    packet.Заголовок = header
    packet.Справочники = create(factory, packet, "Справочники")
    for number in (1, 2, 3):
        counterparty = create(factory, packet.Справочники, "Контрагенты")
        counterparty.ВнешнийКод = f"T9530_K{number}"
        counterparty.Наименование = f"T9530 Контрагент {number}"
        if number == 1:
            for affiliate_number in (2, 3):
                affiliate = create(factory, counterparty, "АффилированныеЛица")
                search = create(factory, affiliate, "Контрагент")
                search.ВнешнийКод = f"T9530_K{affiliate_number}"
                affiliate.Контрагент = search
                counterparty.АффилированныеЛица.Добавить(affiliate)
        packet.Справочники.Контрагенты.Добавить(counterparty)
    return packet


def xml_text(fo, factory, value):
    writer = fo.NewObject("ЗаписьXML")
    writer.УстановитьСтроку()
    factory.ЗаписатьXML(writer, value)
    return writer.Закрыть()


def check(fo, day):
    start = date_1c(fo, day)
    finish = date_1c(fo, day.replace(hour=23, minute=59, second=59))
    deals = query(fo, """
        ВЫБРАТЬ
            Д.Ссылка КАК Ссылка,
            Д.ВнешнийКод КАК ВнешнийКод,
            Д.Проведен КАК Проведен,
            Д.ДатаПоставки КАК ДатаПоставки
        ИЗ
            Документ.Сделка КАК Д
        ГДЕ
            Д.ВнешнийКод ПОДОБНО "T9530%"
            И Д.Дата МЕЖДУ &Начало И &Конец
        УПОРЯДОЧИТЬ ПО
            Д.ВнешнийКод""", {"Начало": start, "Конец": finish})
    balances = query(fo, """
        ВЫБРАТЬ
            Остатки.Сделка.ВнешнийКод КАК Сделка,
            Остатки.Портфель.ВнешнийКод КАК Портфель,
            ПРЕДСТАВЛЕНИЕ(Остатки.Актив) КАК Актив,
            Остатки.КоличествоОстаток КАК Количество
        ИЗ
            РегистрНакопления.ПлановаяПозиция.Остатки(, Сделка.ВнешнийКод ПОДОБНО "T9530%"
                И Сделка.Дата МЕЖДУ &Начало И &Конец) КАК Остатки""", {"Начало": start, "Конец": finish})
    print(f"Сделок T9530 на {day:%d.%m.%Y}: {len(deals)}, проведено {sum(bool(d['Проведен']) for d in deals)}")
    for d in deals:
        print("   ", d["ВнешнийКод"], "проведен" if d["Проведен"] else "НЕ проведен", fo.String(d["ДатаПоставки"]))
    print(f"Строк остатков плановой позиции: {len(balances)}")
    for b in balances:
        print("   ", b["Сделка"], b["Портфель"], b["Актив"], float(b["Количество"]))
    return deals, balances


def main():
    fo = connect("wim_fo")
    if sys.argv[1] == "check":
        check(fo, datetime.datetime.fromisoformat(sys.argv[2]))
        return
    if sys.argv[1] == "restore":
        set_place_codes(fo, restore=True)
        return
    if sys.argv[1] == "affiliates":
        ws = proxy(fo)
        factory = ws.ФабрикаXDTO
        print(xml_text(fo, factory, ws.DownloadPosition(build_affiliates_packet(fo, factory)))[:3000])
        return
    day = datetime.datetime.fromisoformat(sys.argv[1])
    series = sys.argv[2]
    set_place_codes(fo)
    ws = proxy(fo)
    factory = ws.ФабрикаXDTO
    packet = build_packet(fo, factory, day, series)
    answer = ws.DownloadPosition(packet)
    print(xml_text(fo, factory, answer)[:3000])
    check(fo, day)


if __name__ == "__main__":
    main()
