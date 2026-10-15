# -*- coding: utf-8 -*-
"""Стенд проверки CR IMDEV-8856 (списание ВУК) на dev-базе WIM_DU (localhost).

Строка соединения берется из переменной окружения WIM_DU_CONN (в файл не пишется).

Команды:
  python stand.py prepare            - тестовые УК, банк, пул, счета, 130 договоров с аналитикой, карточки обработок
  python stand.py acc928 <0|1>       - есть ли в справочнике счет 40702810116000014928 (счет получателя строки ВУК)
  python stand.py info               - что создано на стенде
  python stand.py cleanup            - удалить все объекты стенда T8856 (непосредственно, без пометки)
Все тестовые объекты помечены текстом T8856 в наименовании или комментарии.
COM-скрипты завершаются os._exit: процесс с V83.COMConnector может зависнуть на выходе.
"""
import datetime as dt
import os
import sys

import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
EPF_DIR = os.path.join(TASK, "Обработки")
EPF_118 = os.path.join(EPF_DIR, "внПоступленияНаРасчетныйСчет_РозничноеДУ_1_18.epf")
EPF_609 = os.path.join(EPF_DIR, "внЗагрузкаВыписокДУ_6_09.epf")
RES = os.path.join(TASK, "Тестирование", "Результаты")
# T8856_VARIANT: orig - 1.18 и 6.09; fix - копии с правками CR; new - 1.19 и 6.10; v20 - 1.20 и 6.11
VARIANT = os.environ.get("T8856_VARIANT", "orig")
if VARIANT == "fix":
    EPF_118 = os.path.join(TASK, "Тестирование", "Обработки", "T8856_Поступления_1_18_fix.epf")
    EPF_609 = os.path.join(TASK, "Тестирование", "Обработки", "T8856_ЗагрузкаВыписок_6_09_fix.epf")
elif VARIANT == "new":
    EPF_118 = os.path.join(EPF_DIR, "внПоступленияНаРасчетныйСчет_РозничноеДУ_1_19.epf")
    EPF_609 = os.path.join(EPF_DIR, "внЗагрузкаВыписокДУ_6_10.epf")
elif VARIANT == "v20":
    EPF_118 = os.path.join(EPF_DIR, "внПоступленияНаРасчетныйСчет_РозничноеДУ_1_20.epf")
    EPF_609 = os.path.join(EPF_DIR, "внЗагрузкаВыписокДУ_6_11.epf")

TAG = "T8856"
ACC_ERS = "40701810000030000413"
ACC_UK = "40702810116000014928"
ACC_BROKER = "30601810100012100828"
ACC_PERSONAL = "40817810000000008856"
N_CONTRACTS = int(os.environ.get("T8856_CONTRACTS", "130"))
CARD_118 = "T8856 Поступления на р/с Розничное ДУ 1.18 (стенд)"
CARD_609 = "T8856 Загрузка выписок ДУ 6.09 (стенд)"


def connect():
    conn_str = os.environ.get("WIM_DU_CONN")
    if not conn_str:
        raise SystemExit("нет переменной окружения WIM_DU_CONN")
    return win32com.client.Dispatch("V83.COMConnector").Connect(conn_str)


def query(c, text, **params):
    q = c.NewObject("Запрос")
    q.Текст = text
    for k, v in params.items():
        q.УстановитьПараметр(k, v)
    return q.Выполнить().Выгрузить()


def rows(c, table):
    cols = [table.Колонки.Получить(i).Имя for i in range(table.Колонки.Количество())]
    return [{k: getattr(table.Получить(i), k) for k in cols} for i in range(table.Количество())]


def date_1c(c, value):
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        value = dt.datetime(value.year, value.month, value.day)
    date_type = c.NewObject("ОписаниеТипов", "Дата").Типы().Получить(0)
    return c.XMLЗначение(date_type, value.strftime("%Y-%m-%dT%H:%M:%S"))


def find_one(c, text, **params):
    t = query(c, text, **params)
    return t.Получить(0).Ссылка if t.Количество() else None


def contractor(c):
    return find_one(c, "ВЫБРАТЬ К.Ссылка КАК Ссылка ИЗ Справочник.Контрагенты КАК К ГДЕ К.Наименование = &Н",
                    Н=TAG + " УК тест")


def bank_account(c, number):
    return find_one(c, "ВЫБРАТЬ Б.Ссылка КАК Ссылка ИЗ Справочник.БанковскиеСчета КАК Б ГДЕ Б.НомерСчета = &Н", Н=number)


def test_contracts(c):
    t = query(c, """ВЫБРАТЬ Д.Ссылка КАК Ссылка, Д.Код КАК Код ИЗ Справочник.ДоговорДУ КАК Д
        ГДЕ Д.Наименование ПОДОБНО &Н УПОРЯДОЧИТЬ ПО Д.Наименование""", Н=TAG + " договор%")
    return [(t.Получить(i).Ссылка, t.Получить(i).Код) for i in range(t.Количество())]


def get_or_create(c, manager, name, folder=False):
    ref = manager.НайтиПоНаименованию(name, True)
    if not ref.Пустая():
        return ref.ПолучитьОбъект()
    obj = manager.СоздатьЭлемент()
    obj.Наименование = name
    return obj


def write_load(obj):
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка


def cmd_prepare(c):
    uk = get_or_create(c, c.Справочники.Контрагенты, TAG + " УК тест")
    uk_ref = write_load(uk)

    bank = get_or_create(c, c.Справочники.Банки, TAG + " Банк ВТБ (стенд)")
    bank.Код = "044525187"
    bank.КоррСчет = "30101810700000000187"
    bank_ref = write_load(bank)

    pool = get_or_create(c, c.Справочники.Пул, TAG + " Пул розничного ДУ")
    pool_ref = write_load(pool)

    rub = c.Справочники.Валюты.НайтиПоКоду("643")
    accounts = {}
    for number, name in [(ACC_ERS, "р/с_ВТБ_ДС_RUR_ЕРС"), (ACC_UK, TAG + " р/с УК (получатель ВУК)"),
                         (ACC_PERSONAL, TAG + " индивидуальный р/с договора")]:
        ref = bank_account(c, number)
        obj = ref.ПолучитьОбъект() if ref is not None else c.Справочники.БанковскиеСчета.СоздатьЭлемент()
        obj.Владелец = uk_ref
        obj.Наименование = name
        obj.НомерСчета = number
        obj.Банк = bank_ref
        obj.ВалютаДенежныхСредств = rub
        obj.Комментарий = TAG
        accounts[number] = write_load(obj)

    kind = c.Перечисления.ВидыАналитическогоСчета.Получить(0)
    existing = {code for _, code in test_contracts(c)}
    for i in range(1, N_CONTRACTS + 1):
        code = "МИ26089" if i == 1 else f"МИ9{i:04d}"
        if code in existing:
            continue
        d = c.Справочники.ДоговорДУ.СоздатьЭлемент()
        d.Код = code
        d.Наименование = f"{TAG} договор {i:03d}"
        d.ДатаНачала = date_1c(c, dt.date(2025, 12, 15) if i == 1 else dt.date(2025, 1, 1) + dt.timedelta(days=i))
        d.Пул = pool_ref
        d.УправляющаяКомпания = uk_ref
        d.Клиент = uk_ref
        write_load(d)

    t = query(c, "ВЫБРАТЬ РАЗЛИЧНЫЕ А.ДоговорДУ.Код КАК Код ИЗ Справочник.АналитическиеСчета КАК А ГДЕ А.Комментарий = &Т", Т=TAG)
    with_analytics = {t.Получить(i).Код for i in range(t.Количество())}
    for ref, code in test_contracts(c):
        idx = int(code[3:]) if code != "МИ26089" else 1
        name = "р/с_ВТБ_ДС_RUR_" + code
        if code in with_analytics:
            continue
        # договор 002: только аналитика с местом хранения на индивидуальном счете;
        # договор 003: две аналитики с одним именем - на ЕРС и на индивидуальном счете
        places = [ACC_ERS]
        if idx == 2:
            places = [ACC_PERSONAL]
        elif idx == 3:
            places = [ACC_ERS, ACC_PERSONAL]
        for place in places:
            a = c.Справочники.АналитическиеСчета.СоздатьЭлемент()
            a.Наименование = name
            a.ДоговорДУ = ref
            a.МестоХранения = accounts[place]
            a.СубъектМестаХранения = uk_ref
            a.ВидАналитическогоСчета = kind
            a.Комментарий = TAG
            write_load(a)

    cash_item = find_one(c, "ВЫБРАТЬ ПЕРВЫЕ 1 С.Ссылка КАК Ссылка ИЗ Справочник.СтатьиДвиженияДенежныхСредств КАК С "
                            "ГДЕ НЕ С.ЭтоГруппа УПОРЯДОЧИТЬ ПО С.Код")
    card_118 = register_epf(c, CARD_118, "ПоступленияНаРасчетныйСчет_РозничноеДУ", EPF_118, "1.18")
    settings = c.NewObject("Структура")
    values = c.NewObject("Структура")
    values.Вставить("Пул", pool_ref)
    values.Вставить("КоличествоПотоков", 5)
    values.Вставить("СтатьяДДССписание", cash_item)
    values.Вставить("СтатьяДДС", cash_item)
    values.Вставить("СтатьяДДСВвод", cash_item)
    values.Вставить("ДополнительнаяОбработка", card_118)
    values.Вставить("СчетРасчетов", c.ПланыСчетов.Хозрасчетный.ПрочиеВзаиморасчеты)
    values.Вставить("СчетРасчетовВвод", c.ПланыСчетов.Хозрасчетный.ПрочиеВзаиморасчеты)
    settings.Вставить("Значения", values)
    settings.Вставить("ЗаголовокНастроек", "стенд " + TAG)
    obj = card_118.ПолучитьОбъект()
    obj.ХранилищеНастроек = c.NewObject("ХранилищеЗначения", settings)
    write_load(obj)
    register_epf(c, CARD_609, "ЗагрузкаВыписок", EPF_609, "6.09")
    print("prepare: УК, банк, пул, счета", ", ".join(accounts), "; договоров", len(test_contracts(c)))


def register_epf(c, name, object_name, path, version):
    obj = get_or_create(c, c.Справочники.ДополнительныеОтчетыИОбработки, name)
    obj.ИмяОбъекта = object_name
    obj.ИмяФайла = os.path.basename(path)
    obj.Версия = version
    obj.Вид = c.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
    obj.Публикация = c.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    obj.БезопасныйРежим = False
    obj.ХранилищеОбработки = c.NewObject("ХранилищеЗначения", c.NewObject("ДвоичныеДанные", path))
    return write_load(obj)


def cmd_acc928(c, present):
    ref = find_one(c, "ВЫБРАТЬ Б.Ссылка КАК Ссылка ИЗ Справочник.БанковскиеСчета КАК Б ГДЕ Б.Наименование = &Н",
                   Н=TAG + " р/с УК (получатель ВУК)")
    obj = ref.ПолучитьОбъект()
    obj.НомерСчета = ACC_UK if present == "1" else "X" + ACC_UK[1:]
    write_load(obj)
    print("счет УК", obj.НомерСчета)


def cmd_info(c):
    for text in [
        "ВЫБРАТЬ Б.Наименование КАК Н, Б.НомерСчета КАК Номер ИЗ Справочник.БанковскиеСчета КАК Б ГДЕ Б.Комментарий = \"T8856\"",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Договоров ИЗ Справочник.ДоговорДУ КАК Д ГДЕ Д.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Аналитик ИЗ Справочник.АналитическиеСчета КАК А ГДЕ А.Комментарий = \"T8856\"",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Начислений ИЗ Документ.НачислениеВознаграждения КАК Н ГДЕ Н.Комментарий ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Списаний ИЗ Документ.СписаниеСРасчетногоСчета КАК С "
        "ГДЕ С.ДоговорДУ.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ Д.Наименование КАК Н, Д.ИмяОбъекта КАК Имя ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д",
    ]:
        for r in rows(c, query(c, text)):
            print({k: c.String(v) for k, v in r.items()})


def cmd_cleanup(c):
    deleted = 0
    for text in [
        "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Документ.СписаниеСРасчетногоСчета КАК С ГДЕ С.ДоговорДУ.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Документ.ПоступлениеНаРасчетныйСчет КАК С ГДЕ С.ДоговорДУ.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Документ.Поручение КАК С ГДЕ С.ДоговорДУ.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ Н.Ссылка КАК Ссылка ИЗ Документ.НачислениеВознаграждения КАК Н ГДЕ Н.Комментарий ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.АналитическиеСчета КАК А ГДЕ А.Комментарий = \"T8856\"",
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДоговорДУ КАК Д ГДЕ Д.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ Б.Ссылка КАК Ссылка ИЗ Справочник.БанковскиеСчета КАК Б ГДЕ Б.Комментарий = \"T8856\"",
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д ГДЕ Д.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Пул КАК П ГДЕ П.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ Б.Ссылка КАК Ссылка ИЗ Справочник.Банки КАК Б ГДЕ Б.Наименование ПОДОБНО \"T8856%\"",
        "ВЫБРАТЬ К.Ссылка КАК Ссылка ИЗ Справочник.Контрагенты КАК К ГДЕ К.Наименование ПОДОБНО \"T8856%\"",
    ]:
        t = query(c, text)
        for i in range(t.Количество()):
            obj = t.Получить(i).Ссылка.ПолучитьОбъект()
            obj.ОбменДанными.Загрузка = True
            obj.Удалить()
            deleted += 1
    rs = c.РегистрыСведений.ИсторияСтатусовОбъектов
    print("cleanup: удалено объектов", deleted)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    c = connect()
    cmd = sys.argv[1]
    if cmd == "prepare":
        cmd_prepare(c)
    elif cmd == "acc928":
        cmd_acc928(c, sys.argv[2])
    elif cmd == "prefix":
        # как в рабочей базе: префикс номера документов договора задан в реквизите Префикс договора
        n = 0
        for ref, code in test_contracts(c):
            obj = ref.ПолучитьОбъект()
            if obj.Префикс != code:
                obj.Префикс = code
                write_load(obj)
                n += 1
        print("префикс заполнен у договоров:", n)
    elif cmd == "measure":
        c.Константы.ВыполнятьЗамерыПроизводительности.Установить(sys.argv[2] == "1")
        print("ВыполнятьЗамерыПроизводительности =", c.Константы.ВыполнятьЗамерыПроизводительности.Получить())
    elif cmd == "variant":
        versions = {"v20": ("1.20", "6.11"), "new": ("1.19", "6.10")}
        ver_in, ver_st = versions.get(VARIANT, ("1.18", "6.09"))
        register_epf(c, CARD_118, "ПоступленияНаРасчетныйСчет_РозничноеДУ", EPF_118, ver_in)
        register_epf(c, CARD_609, "ЗагрузкаВыписок", EPF_609, ver_st)
        print("карточка поступлений", ver_in, "->", EPF_118)
        print("карточка выписки", ver_st, "->", EPF_609)
    elif cmd == "info":
        cmd_info(c)
    elif cmd == "cleanup":
        cmd_cleanup(c)
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)




