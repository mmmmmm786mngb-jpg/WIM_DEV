# -*- coding: utf-8 -*-
"""Проверка цикла Т-1 на dev ФО: сборки "1.16-т1"/"1.21-т1" и кнопки прогонов служебной обработки T9531_ДанныеТ1.

Запуски с формы РОСТ выполняются вручную в клиенте тестирования; этот скрипт - шаги вокруг них через внешнее
соединение (тем же пользователем admin, что и клиент: прогоны хранятся в хранилище общих настроек пользователя).

    python run_t1_cycle_dev.py register 1.16|1.21|1.21-тест   - загрузить сборку в элемент РОСТ (настройки сохраняются)
    python run_t1_cycle_dev.py cache 60                       - срок кеша цены в настройках элемента РОСТ
    python run_t1_cycle_dev.py fix <метка>                    - "Зафиксировать прогон"
    python run_t1_cycle_dev.py reset                          - "Сброс для повторного прогона"
    python run_t1_cycle_dev.py compare 1.16 1.21              - "Сравнить прогоны", JSON в reports/
    python run_t1_cycle_dev.py check                          - сегодняшние поручения РОСТ: статусы, биржевые заявки
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
TASK = os.path.dirname(TESTS)
sys.path.insert(0, os.path.join(TESTS, "1_18"))
import run_1_18_tests as base  # noqa: E402

stage4 = base.stage4
T1 = os.path.join(TASK, "Т-1")
SERVICE = os.path.join(T1, "T9531_ДанныеТ1.epf")
BUILDS = {"1.16": os.path.join(T1, "РОСТ_1.16-т1.epf"), "1.21": os.path.join(T1, "РОСТ_1.21-т1.epf"),
          "1.21-тест": os.path.join(TESTS, "1_18", "сборки", "1.21-тест", "внСозданиеТорговыхПорученийРОСТ.epf")}


def rost_ref(fo):
    return stage4.find_ref(fo, "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                               "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления", {"Имя": stage4.ROST_OBJECT})


def service(fo):
    return fo.ВнешниеОбработки.Создать(SERVICE, False)


def show(fo, obj, data, name):
    text = obj.ТекстРезультата(data)
    print(text)
    out = os.path.join(HERE, "reports", "cycle_%s.json" % name)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(obj.JSONРезультата(data))
    print("json", out)


def main():
    action = sys.argv[1]
    fo = stage4.connect("wim_fo")
    if action == "register":
        ref = rost_ref(fo)
        settings = ref.ПолучитьОбъект().ХранилищеНастроек.Получить()
        ref = stage4.register_epf(fo, stage4.ROST_OBJECT, BUILDS[sys.argv[2]], settings)
        print("registered", fo.String(ref.Версия))
    elif action == "cache":
        item = rost_ref(fo).ПолучитьОбъект()
        settings = item.ХранилищеНастроек.Получить()
        settings.Вставить("СрокКешаЦеныСтаканаСек", int(sys.argv[2]))
        item.ХранилищеНастроек = fo.NewObject("ХранилищеЗначения", settings)
        item.Записать()
        print("cache", sys.argv[2])
    elif action == "fix":
        obj = service(fo)
        show(fo, obj, obj.ЗафиксироватьПрогон(sys.argv[2]), "fix_" + sys.argv[2])
    elif action == "reset":
        obj = service(fo)
        show(fo, obj, obj.СброситьПрогон(), "reset")
    elif action == "compare":
        obj = service(fo)
        show(fo, obj, obj.СравнитьПрогоны(sys.argv[2], sys.argv[3]), "compare")
    elif action == "check":
        query = fo.NewObject("Запрос", """ВЫБРАТЬ п.Направление КАК Направление, ПРЕДСТАВЛЕНИЕ(с.Статус) КАК Статус,
                КОЛИЧЕСТВО(п.Ссылка) КАК Поручений, СУММА(ВЫБОР КОГДА б.Поручение ЕСТЬ NULL ТОГДА 0 ИНАЧЕ 1 КОНЕЦ) КАК СЗаявкой
            ИЗ Документ.Поручение КАК п
                ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.СтатусыПоручений КАК с ПО с.Поручение = п.Ссылка
                ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.БиржевыеЗаявки КАК б ПО б.Поручение = п.Ссылка
            ГДЕ п.Дата >= &Сегодня И п.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.Сделка)
                И НЕ п.ПометкаУдаления
            СГРУППИРОВАТЬ ПО п.Направление, ПРЕДСТАВЛЕНИЕ(с.Статус)""")
        query.УстановитьПараметр("Сегодня", base.today_start(fo))
        table = query.Выполнить().Выгрузить()
        for i in range(table.Количество()):
            row = table.Получить(i)
            print(fo.String(row.Направление), "|", row.Статус, "| поручений", int(row.Поручений),
                  "| с биржевой заявкой", int(row.СЗаявкой))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
