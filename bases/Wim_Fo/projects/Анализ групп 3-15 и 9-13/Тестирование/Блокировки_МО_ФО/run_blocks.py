# -*- coding: utf-8 -*-
"""Прогон выгрузки остатков МО -> ФО с блокировками ДС на стенде IMDEV-9532 (dev WIM_MO -> WIN_FO_server).

Стенд и его функции берутся из каталога стенда IMDEV-9532 (450 тестовых мандатов T9532, пакеты по 45). Сверх
штатного прогона стенда табличная часть Блокировки обработки МО заполняется по одной строке на мандат (рублевый
банковский счет, сумма 10 000), как блокировки "Вознаграждение" в рознице. Внешний код поручения-блокировки
строится так же, как в МО: "LOCK:" + код счета + ":" + дата выгрузки.

    python run_blocks.py --variant 1_42|1_43 [--threads 5] [--no-blocks] [--scenario метка]

Варианты: 1_42 - обработка из выгрузки МО, 1_43 - тестовая версия с отправкой блокировок пакета одним вызовом.
После прогона: время Опубликовать по потокам, вызовы ФО по видам (блокировки DownloadOrders отдельно), состояние
поручений-блокировок T9532 в ФО (число, проведены, помечены на удаление, сумма). Результаты - results/<время>_<метка>/.
"""
import argparse
import json
import multiprocessing
import os
import shutil
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
STAND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                     "IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО", "Тестирование", "Стенд_МО_ФО")
sys.path.insert(0, STAND)

import run_export as stand  # noqa: E402
from stand_common import (PREFIX, N_PORTFOLIOS, PACKET_SIZE, TEST_DATE, EXTERNAL_IB_NAME,  # noqa: E402
                          connect, query, query_table, date_1c, mandate_code, now_stamp)

EPF = {"1_42": os.path.join(HERE, "epf", "внВыгрузкаОстатковМО_ФО_1_42.epf"),
       "1_43": os.path.join(HERE, "epf", "внВыгрузкаОстатковМО_ФО_1_43.epf")}
RESULTS = os.path.join(HERE, "results")
BLOCK_SUM = 10000
LOCK_MASK = "LOCK:" + PREFIX + "%"


def fill_blocks(mo, epf, codes_list, series, bad_mandate="", long_code_date=""):
    """Одна блокировка на мандат: рублевый банковский счет мандата, внешний код как в МО. series - метка серии
    в конце кода: тестовые поручения в ФО через внешнее соединение не удалить, новая серия дает новые поручения."""
    codes = stand.to_array(mo, codes_list)
    rub = query(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = \"643\"")[0]["Ссылка"]
    rows = query_table(mo, """
        ВЫБРАТЬ
            &Дата КАК Период, С.Владелец КАК Мандат, С.Ссылка КАК СчетМандата, &Валюта КАК Валюта,
            "LOCK:" + С.КодСчета + ":" + &Суффикс КАК ОперацияВнешнийКод,
            &Сумма КАК Количество, &Сумма КАК Стоимость
        ИЗ Справочник.СчетаМандатов КАК С
        ГДЕ С.КодСчета ПОДОБНО &МаскаБанк И С.Владелец.КодМандата В (&Коды)""",
                       {"Коды": codes, "Валюта": rub, "Дата": date_1c(mo, TEST_DATE), "Сумма": BLOCK_SUM,
                        "Суффикс": TEST_DATE.strftime("%Y%m%d%H%M%S") + series, "МаскаБанк": PREFIX + "%_B"})
    epf.Блокировки.Загрузить(rows)
    if long_code_date:
        # Код счета дополняется до 25 символов (длина кода счета в МО): код блокировки длиннее 36 символов
        # реквизита ВнешнийКод поручения в ФО, проверка, что дата в конце кода обрезается.
        for i in range(epf.Блокировки.Количество()):
            row = epf.Блокировки.Получить(i)
            account = str(row.СчетМандата.КодСчета)
            row.ОперацияВнешнийКод = "LOCK:" + (account + "_ДЛИННЫЙКОДСЧЕТА")[:25] + ":" + long_code_date
    if bad_mandate:
        # Проверка ветки ошибки: у одного мандата блокировка на счете чужого мандата МО, которого нет в ФО.
        foreign = query(mo, "ВЫБРАТЬ ПЕРВЫЕ 1 С.Ссылка КАК Ссылка ИЗ Справочник.СчетаМандатов КАК С "
                            "ГДЕ НЕ С.КодСчета ПОДОБНО &Маска И С.КодСчета <> \"\" УПОРЯДОЧИТЬ ПО С.КодСчета",
                        {"Маска": PREFIX + "%"})[0]["Ссылка"]
        for i in range(epf.Блокировки.Количество()):
            row = epf.Блокировки.Получить(i)
            if row.Мандат.КодМандата == bad_mandate:
                row.СчетМандата = foreign
    return rows.Количество()


def run_worker(args):
    number, codes_list, session_id, out_dir, epf_path, with_blocks, series, bad_mandate, long_code_date = args
    mo = connect("wim_mo")
    tmp = os.path.join(tempfile.gettempdir(), f"внВыгрузкаОстатковМО_ФО_блокировки_{number}.epf")
    shutil.copyfile(epf_path, tmp)
    protection = mo.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    epf = mo.ВнешниеОбработки.Создать(tmp, False, protection)
    external_ib = query(mo, "ВЫБРАТЬ Сп.Ссылка КАК Ссылка ИЗ Справочник.ВнешниеИнформационныеБазы КАК Сп "
                            "ГДЕ Сп.Наименование = &Имя", {"Имя": EXTERNAL_IB_NAME})[0]["Ссылка"]
    epf.АдресWS = external_ib
    epf.КоличествоПортфелейВПакете = PACKET_SIZE
    epf.КоличествоПотоков = 1
    epf.ОтборМандат = False
    epf.ДатаПоз = date_1c(mo, TEST_DATE)
    epf.ДатаДляФронт = date_1c(mo, TEST_DATE)
    if session_id:
        epf.ИдентификаторСеансаОбмена = session_id
    filled = stand.fill_epf(mo, epf, codes_list)
    filled["блокировок"] = fill_blocks(mo, epf, codes_list, series, bad_mandate, long_code_date) if with_blocks else 0
    started = time.perf_counter()
    error = None
    try:
        epf.Опубликовать(False, False, date_1c(mo, TEST_DATE))
    except Exception as exc:  # noqa: BLE001 - фиксируем и продолжаем сбор замеров
        error = str(exc)[:500]
    publish_s = time.perf_counter() - started
    log_text = epf.ТекстовыйЛог.ПолучитьТекст()
    with open(os.path.join(out_dir, f"mo_log_{number}.txt"), "w", encoding="utf-8") as f:
        f.write(log_text)
    os.remove(tmp)
    return {"поток": number, "заполнено": filled, "опубликовать_с": round(publish_s, 1),
            "есть_ошибки_МО": bool(epf.ЕстьОшибки), "исключение": error,
            "строк_ошибок_блокировок": log_text.count("Ошибка выгрузки блокировк")}


def classify(xml):
    if "<Поручения>" in xml or ":Поручения>" in xml:
        return "блокировки DownloadOrders"
    return stand.classify(xml)


def fo_calls(fo, since):
    """Вызовы веб-сервиса ФО за прогон: по видам число вызовов, сумма и среднее длительности, поручений в вызовах."""
    rows = query(fo, """
        ВЫБРАТЬ С.Тип КАК Тип, С.Идентификатор КАК Ид, С.ИдентификаторСвязи КАК Связь, С.ВремяМС КАК Мс, С.Тело КАК Тело
        ИЗ РегистрСведений.СобытияВнешнихСервисов КАК С
        ГДЕ С.ИмяСервиса = "Avancore" И С.Период >= &С""", {"С": since})
    requests, responses = {}, {}
    for row in rows:
        if row["Тип"] == "Запрос":
            xml = row["Тело"].Получить()
            if not isinstance(xml, str):
                xml = xml.Получить()
            requests[row["Ид"]] = (int(row["Мс"]), xml)
        else:
            responses[row["Связь"]] = int(row["Мс"])
    summary = {}
    for uid, (start_ms, xml) in requests.items():
        kind = classify(xml)
        item = summary.setdefault(kind, {"вызовов": 0, "всего_мс": 0, "поручений": 0})
        item["вызовов"] += 1
        item["поручений"] += xml.count("<ВнешнийКод>LOCK:")
        if uid in responses:
            item["всего_мс"] += responses[uid] - start_ms
    for item in summary.values():
        item["всего_с"] = round(item.pop("всего_мс") / 1000, 1)
        item["среднее_с"] = round(item["всего_с"] / item["вызовов"], 3) if item["вызовов"] else None
    return summary


def lock_orders(fo, series=""):
    rows = query(fo, """
        ВЫБРАТЬ
            КОЛИЧЕСТВО(*) КАК Всего,
            СУММА(ВЫБОР КОГДА П.Проведен ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК Проведено,
            СУММА(ВЫБОР КОГДА П.ПометкаУдаления ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК ПомеченоНаУдаление,
            ЕСТЬNULL(СУММА(П.СуммаПоручения), 0) КАК Сумма,
            КОЛИЧЕСТВО(РАЗЛИЧНЫЕ П.Портфель) КАК Портфелей
        ИЗ Документ.Поручение КАК П
        ГДЕ П.ВнешнийКод ПОДОБНО &Маска""", {"Маска": LOCK_MASK + series})[0]
    return {k: (float(v or 0) if k == "Сумма" else int(v or 0)) for k, v in rows.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(EPF), required=True)
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--no-blocks", action="store_true")
    parser.add_argument("--scenario", default="")
    parser.add_argument("--series", default="", help="метка серии внешних кодов блокировок")
    parser.add_argument("--long-code-date", default="", help="длинный код блокировки (45 символов) с этой датой yyyyMMddHHmmss")
    parser.add_argument("--bad-mandate", default="", help="код мандата, которому подставить счет, которого нет в ФО")
    args = parser.parse_args()
    label = args.scenario or (args.variant + ("_без_блокировок" if args.no_blocks else ""))
    out_dir = os.path.join(RESULTS, f"{now_stamp()}_{label}")
    os.makedirs(out_dir, exist_ok=True)

    codes = [mandate_code(i) for i in range(1, N_PORTFOLIOS + 1)]
    parts = [codes[i::args.threads] for i in range(args.threads)]
    session_id = str(uuid.uuid4()) if args.threads > 1 else ""

    fo = connect("wim_fo")
    before = lock_orders(fo, args.series)
    since = fo.ТекущаяДатаСеанса()
    started = time.perf_counter()
    tasks = [(n + 1, part, session_id, out_dir, EPF[args.variant], not args.no_blocks, args.series, args.bad_mandate, args.long_code_date) for n, part in enumerate(parts)]
    if args.threads > 1:
        with multiprocessing.Pool(args.threads) as pool:
            workers = pool.map(run_worker, tasks)
    else:
        workers = [run_worker(tasks[0])]
    total_s = time.perf_counter() - started
    background_s = stand.wait_background(fo)
    after = lock_orders(fo, args.series)
    calls = fo_calls(fo, since)
    error_flags = query(fo, """
        ВЫБРАТЬ ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод КАК Портфель
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ Д.Свойство.Наименование = "Лимиты есть_ошибки_выгрузки_позиции" И Д.Значение = ИСТИНА
            И ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &Маска""", {"Маска": PREFIX + "%"})
    error_portfolios = sorted(r["Портфель"] for r in error_flags)

    result = {"сценарий": label, "серия": args.series, "мандат_с_ошибкой": args.bad_mandate, "вариант": args.variant, "потоков": args.threads, "блокировки": not args.no_blocks,
              "ОбновлятьСправочныеДанныеИзБэкОфиса": bool(fo.Константы.ОбновлятьСправочныеДанныеИзБэкОфиса.Получить()),
              "ВестиУчетПоСубпортфелям": bool(fo.Константы.ВестиУчетПоСубпортфелям.Получить()),
              "выгрузка_всего_с": round(total_s, 1), "фон_после_с": background_s and round(background_s, 1),
              "потоки": workers, "вызовы_ФО": calls, "поручения_LOCK_до": before, "поручения_LOCK_после": after,
              "портфели_с_флагом_ошибки": error_portfolios}
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"{label}: выгрузка {total_s:.1f} с, фон после {result['фон_после_с']} с")
    for w in workers:
        print(f"  поток {w['поток']}: Опубликовать {w['опубликовать_с']} с, блокировок {w['заполнено']['блокировок']}, "
              f"ошибки МО {w['есть_ошибки_МО']}, строк ошибок блокировок {w['строк_ошибок_блокировок']}"
              f"{', исключение: ' + w['исключение'] if w['исключение'] else ''}")
    for kind, s in calls.items():
        print(f"  {kind}: {s['вызовов']} выз., {s['всего_с']} с, среднее {s['среднее_с']} с, поручений {s['поручений']}")
    print(f"  поручения LOCK до: {before}")
    print(f"  поручения LOCK после: {after}")
    print(f"  портфели с флагом ошибки выгрузки в ФО: {error_portfolios}")
    print(f"  результаты: {out_dir}")


if __name__ == "__main__":
    main()
