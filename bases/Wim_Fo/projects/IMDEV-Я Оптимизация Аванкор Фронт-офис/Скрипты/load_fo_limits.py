#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузка ночных лимитов обычного фронт-офиса в разработческую базу.

Берется набор "ДУ 482п" без активов в РЕПО из выгрузки 24 сентября:
структура и состав. К ним создаются портфели FO_FO, бумаги по видам
активов из отборов, расчетные и депозитные счета, позиция и РСА.
Пороги в выгрузке не хранятся, поэтому для структурных лимитов
ставится тестовый порог.
"""

import json
import os
import traceback
from datetime import datetime

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXPORT = os.path.join(ROOT, "Лимиты_и_справочная информация", "FO_обычное", "limits")
REPORT = os.path.join(ROOT, "Тестирование", "reports", "fo_limits_load.txt")
DATASET_MARK = "репо отключен 21.09.26"
GROUP_NAME = "482-п ДУ"
DATASET_NAME = "FO 482 набор"
SOURCE_NAME = "FO 482 источник"
VARIANT_NAME = "FO 482 процент от РСА"
PORTFOLIO_COUNT = 50
MARK = "FO_FO"


def safe_print(text):
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"), flush=True)


def connect():
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN)


def type_of(conn, name):
    return conn.NewObject("ОписаниеТипов", name).Типы().Get(0)


def query_one(conn, text, params=None):
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for key, value in params.items():
            query.УстановитьПараметр(key, value)
    selection = query.Выполнить().Выбрать()
    if not selection.Следующий():
        return None
    return selection


def query_date(conn, year, month, day):
    row = query_one(conn, "ВЫБРАТЬ ДАТАВРЕМЯ(%s, %s, %s) КАК D" % (year, month, day))
    return row.D


def filled(ref):
    return ref is not None and not ref.Пустая()


def find_by_name(conn, catalog, name):
    if not name:
        return None
    ref = getattr(conn.Справочники, catalog).НайтиПоНаименованию(name, True)
    if not filled(ref):
        return None
    return ref


def find_kind(conn, name):
    if not name:
        return None
    ref = conn.ПланыВидовХарактеристик.ВидыАктивов.НайтиПоНаименованию(name, True)
    if not filled(ref):
        return None
    return ref


COMPARISONS = {
    "Равно": "Равно",
    "Не равно": "НеРавно",
    "В группе": "ВИерархии",
    "Не в группе": "НеВИерархии",
    "В списке": "ВСписке",
    "Не в списке": "НеВСписке",
    "В группе из списка": "ВСпискеПоИерархии",
    "Не в группе из списка": "НеВСпискеПоИерархии",
    "Содержит": "Содержит",
    "Не содержит": "НеСодержит",
    "Больше": "Больше",
    "Меньше": "Меньше",
    "Больше или равно": "БольшеИлиРавно",
    "Меньше или равно": "МеньшеИлиРавно",
    "Заполнено": "Заполнено",
    "Не заполнено": "НеЗаполнено",
}

GROUPS = {
    "Группа И": "ГруппаИ",
    "Группа Или": "ГруппаИли",
    "Группа ИЛИ": "ГруппаИли",
    "Группа Не": "ГруппаНе",
}


class Resolver:
    """Ищет ссылки выгрузки в базе и запоминает, чего не нашлось."""

    def __init__(self, conn):
        self.conn = conn
        self.misses = []
        self.kinds = {}
        self.isins = []

    def remember(self, field, value):
        if field == "ВидАктива" and value is not None and not isinstance(value, (bool, int, float, str)):
            self.kinds[self.conn.String(value)] = value
        if field == "ISIN" and isinstance(value, str) and value and len(self.isins) < 30:
            if value not in self.isins:
                self.isins.append(value)

    def ensure_simple(self, catalog, name):
        item = getattr(self.conn.Справочники, catalog).СоздатьЭлемент()
        item.Наименование = name[:150]
        if catalog == "Валюты":
            item.Код = name[:3]
        item.Записать()
        return item.Ссылка

    def resolve(self, raw, field=""):
        if raw is None or isinstance(raw, (bool, int, float, str)):
            self.remember(field, raw)
            return raw
        if isinstance(raw, list):
            values = self.conn.NewObject("СписокЗначений")
            added = 0
            for item in raw:
                payload = item.get("Значение") if isinstance(item, dict) else item
                resolved = self.resolve(payload, field)
                if resolved is None:
                    continue
                values.Добавить(resolved)
                added += 1
            if added == 0:
                return None
            return values
        if not isinstance(raw, dict):
            return None
        if raw.get("Пустая"):
            return None
        kind = raw.get("Тип") or ""
        name = raw.get("Представление") or ""
        enum_name = raw.get("Имя") or ""
        if kind.startswith("Перечисление."):
            enum_type = kind.split(".", 1)[1]
            try:
                return getattr(getattr(self.conn.Перечисления, enum_type), enum_name)
            except Exception:
                self.misses.append("enum %s.%s" % (enum_type, enum_name))
                return None
        if kind.startswith("Справочник."):
            catalog = kind.split(".", 1)[1]
            found = find_by_name(self.conn, catalog, name)
            if found is None and catalog in ("Валюты", "Контрагенты", "СтраныМира"):
                try:
                    found = self.ensure_simple(catalog, name)
                except Exception:
                    found = None
            if found is None:
                self.misses.append("catalog %s / %s" % (catalog, name[:80]))
                return None
            self.remember(field, found)
            return found
        if kind.startswith("ПланВидовХарактеристик."):
            chart = kind.split(".", 1)[1]
            try:
                found = getattr(self.conn.ПланыВидовХарактеристик, chart).НайтиПоНаименованию(name, True)
            except Exception:
                found = None
            if not filled(found):
                self.misses.append("chart %s / %s" % (chart, name[:80]))
                return None
            self.remember(field, found)
            return found
        self.misses.append("type %s" % kind)
        return None


def add_filter(conn, resolver, elements, items, warnings):
    comparisons = conn.ВидСравненияКомпоновкиДанных
    groups = conn.ТипГруппыЭлементовОтбораКомпоновкиДанных
    added = 0
    for item in items or []:
        if not item.get("Использование", True):
            continue
        if item.get("Вид") == "Группа":
            group_name = GROUPS.get(item.get("ТипГруппы") or "", "ГруппаИ")
            group = elements.Добавить(type_of(conn, "ГруппаЭлементовОтбораКомпоновкиДанных"))
            group.Использование = True
            group.ТипГруппы = getattr(groups, group_name)
            nested = add_filter(conn, resolver, group.Элементы, item.get("Элементы"), warnings)
            if nested == 0:
                elements.Удалить(group)
                continue
            added += 1
            continue
        left = item.get("ЛевоеЗначение")
        if isinstance(left, dict):
            left = left.get("Представление") or left.get("Имя") or ""
        left = str(left or "")
        if len(left) > 40 and any(symbol.isdigit() for symbol in left[-8:]):
            warnings.append("drop extra %s" % left[:60])
            continue
        compare_name = COMPARISONS.get(item.get("ВидСравнения") or "")
        if not left or not compare_name:
            warnings.append("skip compare %s %s" % (left, item.get("ВидСравнения")))
            continue
        right = resolver.resolve(item.get("ПравоеЗначение"), left)
        if right is None and compare_name not in ("Заполнено", "НеЗаполнено"):
            warnings.append("skip empty %s" % left)
            continue
        element = elements.Добавить(type_of(conn, "ЭлементОтбораКомпоновкиДанных"))
        element.Использование = True
        element.ЛевоеЗначение = conn.NewObject("ПолеКомпоновкиДанных", left)
        element.ВидСравнения = getattr(comparisons, compare_name)
        if compare_name not in ("Заполнено", "НеЗаполнено"):
            element.ПравоеЗначение = right
        added += 1
    return added


def pack_settings(conn, resolver, otbor, warnings):
    settings = conn.NewObject("НастройкиКомпоновкиДанных")
    count = add_filter(conn, resolver, settings.Отбор.Элементы, otbor, warnings)
    if count == 0:
        return ""
    storage = conn.NewObject("ХранилищеЗначения", settings)
    return conn.ЗначениеВСтрокуВнутр(storage)


def settings_of(raw):
    if not isinstance(raw, dict):
        return []
    value = raw.get("Значение") or {}
    return value.get("Отбор") or []


def load_cards():
    cards = []
    for name in os.listdir(EXPORT):
        if not name.endswith(".json"):
            continue
        data = json.load(open(os.path.join(EXPORT, name), encoding="utf-8"))
        if data.get("ЭтоГруппа") or data.get("ПометкаУдаления"):
            continue
        req = data.get("Реквизиты") or {}
        if req.get("Тестовый"):
            continue
        dataset = ((req.get("НаборДанныхДляПроверкиЛимитов") or {}) or {}).get("Представление") or ""
        if DATASET_MARK not in dataset:
            continue
        kind = ((req.get("ВидЛимита") or {}) or {}).get("Имя")
        if kind not in ("Структура", "Состав"):
            continue
        cards.append(data)
    cards.sort(key=lambda item: item.get("Код") or "")
    return cards


def ensure_group(conn):
    row = query_one(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка КАК Ссылка ИЗ Справочник.Лимиты "
        "ГДЕ ЭтоГруппа И Наименование = &Имя",
        {"Имя": GROUP_NAME},
    )
    if row is not None:
        return row.Ссылка
    item = conn.Справочники.Лимиты.СоздатьГруппу()
    item.Наименование = GROUP_NAME
    item.Записать()
    return item.Ссылка


def ensure_class(conn):
    found = find_by_name(conn, "КлассыЛимитов", "Compliance")
    if found is not None:
        return found
    item = conn.Справочники.КлассыЛимитов.СоздатьЭлемент()
    item.Наименование = "Compliance"
    item.Записать()
    return item.Ссылка


def ensure_source(conn, limit_class):
    for name in ("Основной (Compliance)", "FO_SHAPE источник позиции", SOURCE_NAME):
        found = find_by_name(conn, "ИсточникиДанныхДляПроверкиЛимитов", name)
        if found is not None:
            return found
    item = conn.Справочники.ИсточникиДанныхДляПроверкиЛимитов.СоздатьЭлемент()
    item.Наименование = SOURCE_NAME
    item.ВидИсточника = conn.Перечисления.ВидыОсновныхИсточниковДанных.ТекущаяПозиция
    item.КлассЛимита = limit_class
    item.Записать()
    return item.Ссылка


def ensure_dataset(conn, source, limit_class):
    found = find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", DATASET_NAME)
    item = conn.Справочники.НаборыДанныхДляПроверкиЛимитов.СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
    item.Наименование = DATASET_NAME
    item.ИсточникДанных = source
    item.КлассЛимита = limit_class
    item.ИспользоватьРепрайсинг = False
    item.ИспользоватьСвойДеноминатор = False
    item.ИспользоватьУКР = False
    item.ПриводитьКВалютеПорогов = False
    item.ОграничиватьПлановуюПозициюПоДатеРасчетов = True
    item.ВсегдаИспользоватьСоставПозицииИзНабораДанных = True
    item.СоставПозиции.Очистить()
    kinds = conn.Перечисления.ВидыПозицийПортфеля
    for kind in (kinds.Плановая, kinds.Прогнозная, kinds.ПрогнознаяАктивыВОбратномРЕПО, kinds.Фактическая):
        row = item.СоставПозиции.Добавить()
        row.ВидПозиции = kind
    item.Записать()
    return item.Ссылка


def ensure_variant(conn):
    found = find_by_name(conn, "ВариантыПроверкиПороговЛимитов", VARIANT_NAME)
    item = conn.Справочники.ВариантыПроверкиПороговЛимитов.СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
    item.Наименование = VARIANT_NAME
    item.Вариант = conn.Перечисления.ВариантыПроверкиПороговЛимитов.ПроцентОтРСА
    item.ФункцияПроверкиПорога = conn.Перечисления.ВидыФункцийПроверкиПороговЛимитов.ПоОбщемуИтогу
    item.Записать()
    return item.Ссылка


def save_limit(conn, card, parent, dataset, limit_class, variant, resolver):
    name = (card.get("Наименование") or "")[:150]
    code = card.get("Код") or ""
    req = card.get("Реквизиты") or {}
    kind_name = req["ВидЛимита"]["Имя"]
    kind = getattr(conn.Перечисления.ВидыЛимитов, kind_name)
    warnings = []
    packed = pack_settings(conn, resolver, settings_of(req.get("НастройкиПодготовкиСпискаАктивов")), warnings)
    found = find_by_name(conn, "Лимиты", name)
    item = conn.Справочники.Лимиты.СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
    if found is None and code:
        taken = query_one(
            conn,
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка КАК Ссылка ИЗ Справочник.Лимиты ГДЕ Код = &Код",
            {"Код": code},
        )
        if taken is None:
            item.Код = code
    item.Родитель = parent
    item.Наименование = name
    item.Описание = (req.get("Описание") or name)[:150]
    item.СпособНастройкиЛимита = conn.Перечисления.СпособыНастройкиЛимита.Внутренний
    item.ВидЛимита = kind
    item.НаборДанныхДляПроверкиЛимитов = dataset
    item.КлассЛимита = limit_class
    item.Тестовый = False
    item.Подтвержден = False
    item.ПакетныйРежим = False
    item.ИспользоватьПулДанныхИзМодификатора = False
    if kind_name == "Структура":
        item.ВариантПроверкиПорога = variant
    item.НастройкиПодготовкиСпискаАктивов = packed
    item.Квалификаторы.Очистить()
    if kind_name == "Состав":
        for row_data in (card.get("ТабличныеЧасти") or {}).get("Квалификаторы") or []:
            qualifier_packed = pack_settings(
                conn, resolver, settings_of(row_data.get("Квалификатор")), warnings)
            if not qualifier_packed:
                continue
            row = item.Квалификаторы.Добавить()
            row.Описание = (row_data.get("Описание") or name)[:150]
            row.Квалификатор = qualifier_packed
    item.Записать()
    return item.Ссылка, kind_name, warnings


def ensure_issuer(conn, name, nonresident):
    found = find_by_name(conn, "Контрагенты", name)
    if found is not None:
        return found
    item = conn.Справочники.Контрагенты.СоздатьЭлемент()
    item.Наименование = name
    try:
        item.НеРезидент = nonresident
    except Exception:
        pass
    item.Записать()
    return item.Ссылка


def ensure_security(conn, catalog, name, kind, currency, issuer, maturity):
    found = find_by_name(conn, catalog, name)
    if found is not None:
        return found
    item = getattr(conn.Справочники, catalog).СоздатьЭлемент()
    item.Наименование = name
    item.ВидАктива = kind
    item.ВалютаНоминальнойСтоимости = currency
    item.Эмитент = issuer
    if catalog == "Облигации":
        item.НоминальнаяСтоимость = 1000
        item.ДатаПогашения = maturity
    item.Записать()
    return item.Ссылка


def ensure_asset(conn, name, kind, currency, issuer, obj, isin=""):
    found = find_by_name(conn, "Активы", name)
    if found is not None:
        return found
    item = conn.Справочники.Активы.СоздатьЭлемент()
    item.Наименование = name
    item.ВидАктива = kind
    item.ВалютаНоминальнойСтоимости = currency
    item.Эмитент = issuer
    item.Объект = obj
    if isin:
        item.ISIN = isin[:20]
    item.Записать()
    return item.Ссылка


def catalog_for_kind(conn, kind):
    text = conn.String(kind).lower()
    if "паи" in text or "фонд" in text:
        return "ПаиПИФ"
    if "акци" in text or "расписк" in text:
        return "Акции"
    return "Облигации"


def ensure_place(conn, issuer, currency, account_kind, title):
    account_name = "FO_FO %s" % title
    account = find_by_name(conn, "БанковскиеСчета", account_name)
    if account is None:
        item = conn.Справочники.БанковскиеСчета.СоздатьЭлемент()
        item.Владелец = issuer
        item.Наименование = account_name
        item.ВалютаДенежныхСредств = currency
        item.ВидСчета = account_kind
        item.Записать()
        account = item.Ссылка
    place_name = "FO_FO место %s" % title
    place = find_by_name(conn, "МестаХранения", place_name)
    if place is None:
        item = conn.Справочники.МестаХранения.СоздатьЭлемент()
        item.Наименование = place_name
        item.ВидМестаХранения = conn.ПланыВидовХарактеристик.ВидыМестХранения.БанковскиеСчета
        item.Объект = account
        item.Записать()
        place = item.Ссылка
    return place


def ensure_portfolios(conn, currency):
    refs = []
    for index in range(1, PORTFOLIO_COUNT + 1):
        name = "%s %03d" % (MARK, index)
        found = find_by_name(conn, "Портфели", name)
        if found is None:
            item = conn.Справочники.Портфели.СоздатьЭлемент()
            item.Наименование = name
            item.Валюта = currency
            item.Записать()
            found = item.Ссылка
        refs.append(found)
    return refs


def write_rsa(conn, portfolios):
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    register = conn.РегистрыСведений.РегистрРСА_СЧА
    for portfolio in portfolios:
        record = register.СоздатьМенеджерЗаписи()
        record.Период = day
        record.Портфель = portfolio
        record.РСА = 1000
        record.СЧА = 1000
        record.СА = 1000
        record.Записать()


def write_positions(conn, portfolios, rows):
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    empty = query_date(conn, 1, 1, 1)
    position = conn.РегистрыСведений.ФактическаяПозиция
    actual = conn.РегистрыСведений.ДатаАктуальностиФактическойПозиции
    empty_place = conn.Справочники.МестаХранения.ПустаяСсылка()
    sub = conn.Справочники.Субпортфели.ПустаяСсылка()
    account = conn.Справочники.СчетаУчетаЕПС.ПустаяСсылка()
    model = conn.Перечисления.ТипыПортфелей.ПустаяСсылка()
    for index, portfolio in enumerate(portfolios, start=1):
        mark = actual.СоздатьМенеджерЗаписи()
        mark.Портфель = portfolio
        mark.Дата = day
        mark.Записать()
        record_set = position.СоздатьНаборЗаписей()
        record_set.Отбор.Портфель.Установить(portfolio)
        record_set.Отбор.Дата.Установить(day)
        record_set.Прочитать()
        record_set.Очистить()
        for asset, place, base_cost in rows:
            cost = base_cost if index <= 40 else base_cost * 4
            if cost == 0:
                continue
            row = record_set.Добавить()
            row.Период = day
            row.Дата = day
            row.Портфель = portfolio
            row.Актив = asset
            row.МестоХранения = place if place is not None else empty_place
            row.Субпортфель = sub
            row.ДатаПартии = empty
            row.ТипПортфеля = model
            row.СчетУчета = account
            row.Количество = 10
            row.Стоимость = cost
            row.АмортизированнаяСтоимость = cost
            row.НКД = 0
            row.Задолженность = 0
            row.СуммаДенежныхСредствСЗадолженностью = 0
            row.ПервоначальнаяСтоимость = cost
        record_set.Записать()


def ensure_thresholds(conn, limits):
    manager = conn.Справочники.НастройкиПороговДляПроверкиЛимитов
    register = conn.РегистрыСведений.ПорогиЛимитов
    empty_portfolio = conn.Справочники.Портфели.ПустаяСсылка()
    period = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cache = {}
    written = 0
    for limit_ref, kind_name, name in limits:
        if kind_name != "Структура":
            continue
        threshold = 0.01 if "0%" in name else 80
        setting = cache.get(threshold)
        if setting is None:
            setting_name = "FO_FO порог %s" % threshold
            found = find_by_name(conn, "НастройкиПороговДляПроверкиЛимитов", setting_name)
            item = manager.СоздатьЭлемент() if found is None else found.ПолучитьОбъект()
            item.Наименование = setting_name
            item.ИспользоватьРасширеннуюУстановкуПорогов = False
            item.СложныеПороги.Очистить()
            row = item.СложныеПороги.Добавить()
            row.ПоУмолчанию = True
            row.МаксДоляЖелтаяЗона = 0.01 if threshold < 1 else 75
            row.МаксДоляКраснаяЗона = threshold
            item.Записать()
            setting = item.Ссылка
            cache[threshold] = setting
        record = register.СоздатьМенеджерЗаписи()
        record.Период = period
        record.Лимит = limit_ref
        record.Портфель = empty_portfolio
        record.НастройкаПороговДляПроверкиЛимитов = setting
        record.Записать()
        written += 1
    return written


def install(conn, portfolios, limits, limit_class):
    posted = 0
    limit_refs = [item[0] for item in limits]
    for portfolio in portfolios:
        existing = query_one(
            conn,
            "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов КАК Т "
            "ГДЕ Т.Проведен И Т.ОбъектНазначения = &Портфель И НЕ Т.ПометкаУдаления",
            {"Портфель": portfolio},
        )
        if existing is not None:
            doc = existing.Ссылка.ПолучитьОбъект()
        else:
            doc = conn.Документы.УстановкаЛимитов.СоздатьДокумент()
            doc.Дата = datetime.now().replace(microsecond=0)
            doc.ВидОперации = conn.Перечисления.ВидыОперацийУстановкиЛимитов.ПоПортфелю
            doc.ОбъектНазначения = portfolio
            doc.КлассЛимита = limit_class
            doc.Подтвержден = False
        present = {}
        for index in range(doc.Лимиты.Количество()):
            line = doc.Лимиты.Получить(index)
            present[conn.String(line.Лимит)] = True
        changed = False
        for limit_ref in limit_refs:
            if conn.String(limit_ref) not in present:
                line = doc.Лимиты.Добавить()
                line.Лимит = limit_ref
                changed = True
        if doc.Лимиты.Количество() > 0 and (changed or not doc.Проведен):
            doc.Записать(conn.РежимЗаписиДокумента.Проведение)
            posted += 1
        if posted and posted % 10 == 0:
            safe_print("installations " + str(posted))
    return posted


def build_assets(conn, resolver, rub, usd, resident, foreign, maturity):
    rows = []
    errors = []
    index = 0
    for kind in resolver.kinds.values():
        index += 1
        title = conn.String(kind)[:40]
        foreign_kind = "иностран" in title.lower()
        currency = usd if foreign_kind else rub
        issuer = foreign if foreign_kind else resident
        catalog = catalog_for_kind(conn, kind)
        name = "FO_FO %03d %s" % (index, title)
        name = name[:150]
        try:
            security = ensure_security(conn, catalog, name, kind, currency, issuer, maturity)
            asset = ensure_asset(conn, name, kind, currency, issuer, security)
            rows.append((asset, None, 50))
        except Exception as error:
            errors.append("%s: %s" % (name, str(error)[:160]))
    for isin in resolver.isins:
        name = "FO_FO ISIN %s" % isin
        kind = find_kind(conn, "Облигации")
        if kind is None and resolver.kinds:
            kind = next(iter(resolver.kinds.values()))
        if kind is None:
            break
        try:
            security = ensure_security(conn, "Облигации", name[:150], kind, rub, resident, maturity)
            asset = ensure_asset(conn, name[:150], kind, rub, resident, security, isin)
            rows.append((asset, None, 20))
        except Exception as error:
            errors.append("%s: %s" % (name, str(error)[:160]))
    return rows, errors


def run_check(conn):
    """Один пост-контроль по загруженным лимитам и портфелям FO_FO."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pack_base", os.path.join(os.path.dirname(__file__), "run_pack_baseline.py"))
    pack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pack)
    portfolios = []
    selection = query_one(conn, "ВЫБРАТЬ 1 КАК N")
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Портфели "
        "ГДЕ Наименование ПОДОБНО &Маска УПОРЯДОЧИТЬ ПО Наименование"
    )
    query.УстановитьПараметр("Маска", MARK + " %")
    selection = query.Выполнить().Выбрать()
    while selection.Следующий():
        portfolios.append(selection.Ссылка)
    query.Текст = (
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты "
        "ГДЕ НЕ ЭтоГруппа И Родитель.Наименование = &Группа"
    )
    query.УстановитьПараметр("Группа", GROUP_NAME)
    selection = query.Выполнить().Выбрать()
    limits = []
    while selection.Следующий():
        limits.append(selection.Ссылка)
    safe_print("check portfolios %s limits %s" % (len(portfolios), len(limits)))
    elapsed, result, container = pack.run_post(conn, portfolios, limits)
    lines = [
        "check_seconds %.3f" % elapsed,
        "check_refusal %s" % result.Отказ,
        "check_description %s" % str(result.Описание).replace("\n", " ")[:300],
    ]
    zone_query = conn.NewObject("Запрос")
    zone_query.Текст = (
        "ВЫБРАТЬ К.Зона КАК Зона, КОЛИЧЕСТВО(*) КАК N "
        "ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Вместилище = &Вместилище "
        "СГРУППИРОВАТЬ ПО К.Зона"
    )
    zone_query.УстановитьПараметр("Вместилище", container)
    selection = zone_query.Выполнить().Выбрать()
    while selection.Следующий():
        lines.append("zone %s %s" % (conn.String(selection.Зона), selection.N))
    sample = conn.NewObject("Запрос")
    sample.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 8 К.Лимит.Наименование КАК Лимит, К.Описание КАК Описание "
        "ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Вместилище = &Вместилище И К.Описание ПОДОБНО \"%Ошиб%\" "
    )
    sample.УстановитьПараметр("Вместилище", container)
    selection = sample.Выполнить().Выбрать()
    while selection.Следующий():
        lines.append("error_row %s | %s" % (
            conn.String(selection.Лимит)[:80],
            conn.String(selection.Описание).replace("\n", " ")[:180],
        ))
    safe_print("check done %.1f" % elapsed)
    return lines


def main():
    lines = []
    conn = connect()
    cards = load_cards()
    safe_print("cards %s" % len(cards))
    limit_class = ensure_class(conn)
    source = ensure_source(conn, limit_class)
    dataset = ensure_dataset(conn, source, limit_class)
    variant = ensure_variant(conn)
    parent = ensure_group(conn)
    resolver = Resolver(conn)
    limits = []
    failed = []
    warning_count = 0
    for index, card in enumerate(cards, start=1):
        try:
            ref, kind_name, warnings = save_limit(
                conn, card, parent, dataset, limit_class, variant, resolver)
            limits.append((ref, kind_name, (card.get("Наименование") or "")[:150]))
            warning_count += len(warnings)
        except Exception as error:
            failed.append("%s %s" % (card.get("Код"), str(error).replace("\n", " ")[:220]))
        if index % 20 == 0:
            safe_print("limits %s failed %s" % (index, len(failed)))
    safe_print("saved %s failed %s" % (len(limits), len(failed)))

    rub = find_by_name(conn, "Валюты", "RUB")
    usd = find_by_name(conn, "Валюты", "USD")
    resident = ensure_issuer(conn, "FO_FO эмитент", False)
    foreign = ensure_issuer(conn, "FO_FO нерезидент", True)
    maturity = query_date(conn, 2030, 12, 31)
    asset_rows, asset_errors = build_assets(conn, resolver, rub, usd, resident, foreign, maturity)
    safe_print("assets %s" % len(asset_rows))

    cash_errors = []
    try:
        rub_asset = find_by_name(conn, "Активы", "RUB")
        usd_asset = find_by_name(conn, "Активы", "USD")
        settlement = conn.Перечисления.ВидБанковскогоСчета.Расчетный
        deposit = conn.Перечисления.ВидБанковскогоСчета.Депозитный
        rub_place = ensure_place(conn, resident, rub, settlement, "расчетный RUB")
        usd_place = ensure_place(conn, resident, usd, settlement, "расчетный USD")
        dep_place = ensure_place(conn, resident, rub, deposit, "депозит RUB")
        dep_fx_place = ensure_place(conn, resident, usd, deposit, "депозит USD")
        if rub_asset is not None:
            asset_rows.append((rub_asset, rub_place, 40))
            asset_rows.append((rub_asset, dep_place, 30))
        if usd_asset is not None:
            asset_rows.append((usd_asset, usd_place, 15))
            asset_rows.append((usd_asset, dep_fx_place, 15))
    except Exception as error:
        cash_errors.append(str(error).replace("\n", " ")[:300])

    portfolios = ensure_portfolios(conn, rub)
    safe_print("portfolios %s" % len(portfolios))
    write_rsa(conn, portfolios)
    write_positions(conn, portfolios, asset_rows)
    safe_print("positions written")
    thresholds = ensure_thresholds(conn, limits)
    posted = install(conn, portfolios, limits, limit_class)
    safe_print("installed %s" % posted)

    lines.append("cards_in_export %s" % len(cards))
    lines.append("limits_saved %s" % len(limits))
    lines.append("limits_failed %s" % len(failed))
    lines.append("filter_warnings %s" % warning_count)
    lines.append("unresolved %s" % len(resolver.misses))
    lines.append("assets %s" % len(asset_rows))
    lines.append("asset_errors %s" % len(asset_errors))
    lines.append("portfolios %s" % len(portfolios))
    lines.append("thresholds %s" % thresholds)
    lines.append("installations %s" % posted)
    lines.append("dataset %s" % DATASET_NAME)
    lines.append("ukr off, thresholds are test values: 0.01 when name has 0%%, else red 80 yellow 75")
    for row in failed[:30]:
        lines.append("FAIL " + row)
    for row in asset_errors[:20]:
        lines.append("ASSET " + row)
    for row in cash_errors:
        lines.append("CASH " + row)
    unique_misses = []
    for row in resolver.misses:
        if row not in unique_misses:
            unique_misses.append(row)
    for row in unique_misses[:40]:
        lines.append("MISS " + row)

    try:
        lines.extend(run_check(conn))
    except Exception as error:
        lines.append("CHECK " + str(error).replace("\n", " ")[:500])

    report_dir = os.path.dirname(REPORT)
    if not os.path.isdir(report_dir):
        os.makedirs(report_dir)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    safe_print("LOAD DONE")
    safe_print("\n".join(lines[:12]))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
