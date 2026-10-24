#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Что зарегистрировано на dev ФО для прогона покупки и продажи РОСТ 1.24.

Печатает версию обработки РОСТ и обвязки T9530_ТестРОСТ, команды, ключевые
настройки (без паролей) и состав выборки T9531PROP. Данные не меняет.

    python check_registered.py
"""
import datetime
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
TASK = os.path.dirname(TESTS)
STAND = os.path.join(os.path.dirname(TASK), "IMDEV-9530  Замеры ФО", "Тестирование", "Стенд_замеры")
sys.path.insert(0, STAND)
import run_stage4_tests as stage4  # noqa: E402
from stand_common import to_array  # noqa: E402

SETTING_KEYS = (
    "СрокКешаЦеныСтаканаСек",
    "ВыключитьПокупки",
    "ВыключитьПродажи",
    "КонтрольПоЦенеЗакрытия",
    "АдресWS",
    "АвторЗаявок",
    "АктивРубли",
    "АктивВимЛиквидность",
    "ДопРеквизитСтатусПортфеля",
    "СтатусДляПоиска",
    "СтатусРасторжениеИнициировано",
)


def text(fo, value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    try:
        return fo.String(value)
    except Exception:
        return str(value)


def setting(storage, key):
    try:
        return getattr(storage, key)
    except Exception:
        return None


def main():
    fo = stage4.connect("wim_fo")
    print("session", text(fo, fo.ТекущаяДатаСеанса()))
    rows = stage4.query(
        fo,
        """ВЫБРАТЬ
            Д.ИмяОбъекта КАК Имя,
            Д.Наименование КАК Наименование,
            Д.Версия КАК Версия,
            Д.ИмяФайла КАК Файл,
            ПРЕДСТАВЛЕНИЕ(Д.Публикация) КАК Публикация,
            Д.ПометкаУдаления КАК Удален
        ИЗ
            Справочник.ДополнительныеОтчетыИОбработки КАК Д
        ГДЕ
            Д.ИмяОбъекта В (&Имена)""",
        {"Имена": to_array(fo, [stage4.ROST_OBJECT, stage4.TEST_OBJECT])},
    )
    for row in rows:
        print("processing", text(fo, row["Имя"]), "version", text(fo, row["Версия"]),
              "file", text(fo, row["Файл"]), "publication", text(fo, row["Публикация"]),
              "deleted", bool(row["Удален"]))

    commands = stage4.query(
        fo,
        """ВЫБРАТЬ
            Д.ИмяОбъекта КАК Имя,
            К.Идентификатор КАК Идентификатор,
            К.Представление КАК Представление,
            ПРЕДСТАВЛЕНИЕ(К.ВариантЗапуска) КАК Вариант,
            К.РегламентноеЗаданиеGUID КАК Задание
        ИЗ
            Справочник.ДополнительныеОтчетыИОбработки.Команды КАК К
                ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.ДополнительныеОтчетыИОбработки КАК Д
                ПО К.Ссылка = Д.Ссылка
        ГДЕ
            Д.ИмяОбъекта = &Имя
            И НЕ Д.ПометкаУдаления""",
        {"Имя": stage4.ROST_OBJECT},
    )
    for row in commands:
        print("command", text(fo, row["Идентификатор"]), "|", text(fo, row["Представление"]),
              "|", text(fo, row["Вариант"]), "| job", text(fo, row["Задание"]))

    ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": stage4.ROST_OBJECT},
    )
    storage = ref.ХранилищеНастроек.Получить()
    print("settings loaded", storage is not None)
    for key in SETTING_KEYS:
        value = setting(storage, key)
        shown = text(fo, value)
        if key == "АдресWS":
            shown = shown[:80]
        print("setting", key, "=", shown)
    strategies = setting(storage, "НастройкаСтратегий")
    print("setting НастройкаСтратегий set", strategies is not None and text(fo, strategies) != "")

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    today_lit = "ДАТАВРЕМЯ(%d, %d, %d)" % (today.year, today.month, today.day)
    yesterday_lit = "ДАТАВРЕМЯ(%d, %d, %d)" % (yesterday.year, yesterday.month, yesterday.day)
    groups = stage4.query(
        fo,
        """ВЫБРАТЬ
            ПОДСТРОКА(П.ВнешнийКод, 11, 1) КАК Группа,
            КОЛИЧЕСТВО(*) КАК Количество
        ИЗ
            Справочник.Портфели КАК П
        ГДЕ
            П.ВнешнийКод ПОДОБНО "T9531PROP_%"
            И НЕ П.ПометкаУдаления
        СГРУППИРОВАТЬ ПО
            ПОДСТРОКА(П.ВнешнийКод, 11, 1)""",
    )
    for row in groups:
        print("portfolios", text(fo, row["Группа"]), int(row["Количество"]))

    deals = stage4.query(
        fo,
        """ВЫБРАТЬ
            КОЛИЧЕСТВО(*) КАК Количество
        ИЗ
            Документ.Поручение КАК П
        ГДЕ
            П.Портфель.ВнешнийКод ПОДОБНО "T9531PROP%"
            И П.Дата >= """ + today_lit + """
            И П.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.Сделка)
            И НЕ П.ПометкаУдаления""",
    )
    print("deals today", int(deals[0]["Количество"]) if deals else 0)

    for label, literal in (("today", today_lit), ("yesterday", yesterday_lit)):
        positions = stage4.query(
            fo,
            """ВЫБРАТЬ
                ПОДСТРОКА(т.Портфель.ВнешнийКод, 11, 1) КАК Группа,
                КОЛИЧЕСТВО(РАЗЛИЧНЫЕ т.Портфель) КАК Портфелей
            ИЗ
                РегистрСведений.ФактическаяПозиция КАК т
            ГДЕ
                т.Дата = """ + literal + """
                И т.Портфель.ВнешнийКод ПОДОБНО "T9531PROP_%"
            СГРУППИРОВАТЬ ПО
                ПОДСТРОКА(т.Портфель.ВнешнийКод, 11, 1)""",
        )
        if not positions:
            print("positions", label, "none")
        for row in positions:
            print("positions", label, text(fo, row["Группа"]), "portfolios", int(row["Портфелей"]))


if __name__ == "__main__":
    main()
