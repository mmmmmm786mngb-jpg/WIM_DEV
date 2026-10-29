# -*- coding: utf-8 -*-
"""Проверка версий 1.19 (ОРИГИНАЛ) и 1.20 (ОПТИМИЗИРОВАНО) обработки внЗагрузкаДепозитовИзВнешнихИсточников на dev ФО.

    python test_retail_switch.py

Обычная база: заголовок dev ФО как есть (без RETAIL). Розница: на время проверки заголовок системы dev ФО дополняется
текстом RETAIL, исходное значение возвращается в блоке finally. Источники: ПИФ - сервис dev ПИФ, ДУ - заведомо
недоступный адрес (вызов дал бы ошибку и время ожидания), Calipso в обычной базе не вызывается (его сервер задан в коде
обработки). Отчет - reports/test_retail_switch_<время>.txt.
"""
import datetime
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
STAND = os.path.join(os.path.dirname(TASK), "IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО",
                     "Тестирование", "Стенд_МО_ФО")
sys.path.insert(0, STAND)
import stand_common  # noqa: E402

EPF = {"1.19": os.path.join(TASK, "ОРИГИНАЛ", "внЗагрузкаДепозитовИзВнешнихИсточников_1_19.epf"),
       "1.20": os.path.join(TASK, "ОПТИМИЗИРОВАНО", "внЗагрузкаДепозитовИзВнешнихИсточников_1_20.epf")}
PIF_WSDL = "http://localhost/wim_pif/ws/deposits?wsdl"
DEAD_WSDL = "http://127.0.0.1:9/nowhere/ws/DU.1cws?wsdl"
LINES = []


def out(text=""):
    print(text)
    LINES.append(text)


def create(fo, version):
    protection = fo.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    return fo.ВнешниеОбработки.Создать(EPF[version], False, protection)


def setup(fo, obj, du=""):
    pif = stand_common._registry_db("wim_pif")
    obj.ВебСервисДУ = du
    obj.ВебСервисПИФ = PIF_WSDL
    obj.Логин = pif["user"]
    obj.Пароль = pif.get("password", "")
    obj.ДатаЗапроса = stand_common.date_1c(fo, datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))


def table_rows(tab):
    cols = [tab.Выгрузить().Колонки.Получить(i).Имя for i in range(tab.Выгрузить().Колонки.Количество())]
    rows = []
    data = tab.Выгрузить()
    for i in range(data.Количество()):
        row = data.Получить(i)
        rows.append(tuple(str(row.Получить(j)) for j in range(len(cols))))
    return sorted(rows)


def run(label, fn):
    started = time.perf_counter()
    error = ""
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001 - результат проверки фиксируется в отчете
        result = None
        error = str(exc)[:300]
    return result, round((time.perf_counter() - started) * 1000), error


def log_items(log):
    if log is None:
        return []
    return [str(log.Получить(i)) for i in range(log.Количество())]


def positions_count(fo):
    q = fo.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Записей ИЗ РегистрСведений.ВТБ_ФактическаяПозицияДепозитов КАК Позиции"
    s = q.Выполнить().Выбрать()
    s.Следующий()
    return int(s.Записей)


def journal_records(fo, since):
    table = fo.NewObject("ТаблицаЗначений")
    selection = fo.NewObject("Структура")
    selection.Вставить("ДатаНачала", since)
    selection.Вставить("СобытиеЖурналаРегистрации", "ЗагрузкаДепозитов")
    fo.ВыгрузитьЖурналРегистрации(table, selection)
    return [str(table.Получить(i).Комментарий) for i in range(table.Количество())]


def ok(flag):
    return "ДА" if flag else "НЕТ"


def main():
    fo = stand_common.connect("wim_fo")
    title = fo.Константы.ЗаголовокСистемы.Получить()
    out(f"Проверка обработки загрузки депозитов 1.19 и 1.20 на dev ФО, {datetime.datetime.now():%d.%m.%Y %H:%M}")
    out(f"Заголовок системы dev ФО: {title}")
    results = []

    out("")
    out("1. Обычная база (заголовок без RETAIL): кнопка 'из Аванкора' (ДУ не задан, ПИФ - dev)")
    lists = {}
    for version in ("1.19", "1.20"):
        obj = create(fo, version)
        setup(fo, obj)
        log = fo.NewObject("Массив")
        _, ms, error = run(version, lambda: obj.ЗаполнитьДепозитыАванкор(log))
        lists[version] = table_rows(obj.СписокДепозитовПИФ)
        out(f"   {version}: {ms} мс, депозитов ПИФ {len(lists[version])}, лог {log_items(log)}, ошибка '{error}'")
    same = lists["1.19"] == lists["1.20"] and len(lists["1.19"]) > 0
    out(f"   Список депозитов ПИФ в 1.20 совпадает с 1.19 построчно и не пуст: {ok(same)}")
    results.append(("Обычная база: источники вызываются, результат как в 1.19", same))

    since = fo.ТекущаяДатаСеанса()
    fo.Константы.ЗаголовокСистемы.Установить(f"{title} RETAIL")
    try:
        out("")
        out(f"2. Розница (заголовок на время проверки: '{fo.Константы.ЗаголовокСистемы.Получить()}')")
        obj = create(fo, "1.19")
        setup(fo, obj)
        log = fo.NewObject("Массив")
        _, ms, error = run("1.19", lambda: obj.ЗаполнитьДепозитыАванкор(log))
        control = len(table_rows(obj.СписокДепозитовПИФ))
        out(f"   Контроль, 1.19 'из Аванкора': {ms} мс, депозитов ПИФ {control} - оригинал вызывает источники и в рознице")
        results.append(("Контроль: 1.19 в рознице вызывает источники", control > 0))

        obj = create(fo, "1.20")
        setup(fo, obj, DEAD_WSDL)
        log = fo.NewObject("Массив")
        _, ms, error = run("1.20", lambda: obj.ЗаполнитьДепозитыАванкор(log))
        cnt = len(table_rows(obj.СписокДепозитовПИФ))
        passed = cnt == 0 and not log_items(log) and not error and ms < 2000
        out(f"   1.20 'из Аванкора': {ms} мс, депозитов ПИФ {cnt}, лог {log_items(log)}, ошибка '{error}' - {ok(passed)}")
        results.append(("Розница, 1.20 'из Аванкора': источники не вызываются", passed))

        obj = create(fo, "1.20")
        setup(fo, obj, DEAD_WSDL)
        log = fo.NewObject("Массив")
        _, ms, error = run("1.20", lambda: obj.ЗаполнитьДепозиты(log))
        cnt = len(table_rows(obj.СписокДепозитовПИФ)) + len(table_rows(obj.СписокДепозитовCalipso))
        passed = cnt == 0 and not log_items(log) and not error and ms < 2000
        out(f"   1.20 'из всех источников': {ms} мс, депозитов {cnt}, лог {log_items(log)}, ошибка '{error}' - {ok(passed)}")
        results.append(("Розница, 1.20 'из всех источников': ДУ, ПИФ и Calipso не вызываются", passed))

        obj = create(fo, "1.20")
        log = fo.NewObject("Массив")
        _, ms, error = run("1.20", lambda: obj.ЗаполнитьДепозитыКалипсоМодуль(log))
        cnt = len(table_rows(obj.СписокДепозитовCalipso))
        passed = cnt == 0 and not error and ms < 2000
        out(f"   1.20 'из Calipso': {ms} мс, депозитов Calipso {cnt}, ошибка '{error}' - {ok(passed)}")
        results.append(("Розница, 1.20 'из Calipso': Calipso не вызывается", passed))

        before = positions_count(fo)
        obj = create(fo, "1.20")
        params = fo.NewObject("Структура")
        _, ms, error = run("1.20", lambda: obj.ВыполнитьКоманду("ФоновоеВыполнение", params))
        after = positions_count(fo)
        records = journal_records(fo, since)
        passed = not error and ms < 2000 and before == after and any("База розницы" in r for r in records)
        out(f"   1.20 команда ФоновоеВыполнение: {ms} мс, ошибка '{error}', записей позиции депозитов {before} -> {after}, "
            f"журнал: {records} - {ok(passed)}")
        results.append(("Розница, 1.20 ФоновоеВыполнение: сразу выходит, регистр не меняется, запись в журнале", passed))
    finally:
        fo.Константы.ЗаголовокСистемы.Установить(title)
        out("")
        out(f"Заголовок системы dev ФО восстановлен: {fo.Константы.ЗаголовокСистемы.Получить()}")

    out("")
    out("Итог")
    for name, flag in results:
        out(f"   {ok(flag):3} {name}")
    out(f"Пройдено {sum(1 for _, f in results if f)} из {len(results)}")
    path = os.path.join(HERE, "reports", "test_retail_switch_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(LINES) + "\n")
    print("Отчет:", path)


if __name__ == "__main__":
    main()
