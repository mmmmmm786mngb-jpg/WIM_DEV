# -*- coding: utf-8 -*-
"""Прогон тестовой выгрузки остатков МО -> ФО на стенде с замером времени каждого вызова на ФО.

1. Создает МО-обработку внВыгрузкаОстатковМО_ФО (версия из выгрузки ПРОД) из собранного файла.
2. Заполняет ее табличные части тестовыми строками: на мандат 1 строка денег (рубли, банковский счет),
   3 строки ЦБ (T9532_SH1..3, счет депо) и 1 строка СЧА/РСА - в среднем 4 строки позиции на портфель, как в ПРОД.
3. Вызывает штатный Опубликовать против публикации ФО: пакеты по 45 портфелей с вызовами 754/768/872,
   удалением блокировок и запуском перерасчета РСА.
   С --threads N мандаты делятся на N непересекающихся частей и выгружаются N параллельными сеансами МО
   с общим идентификатором сеанса обмена - так же, как пачечный режим в ПРОД (5 потоков).
4. Ждет завершения фоновых заданий перерасчета на ФО.
5. По логу веб-сервиса ФО считает длительность каждого вызова (от записи запроса в лог до записи ответа),
   сохраняет вызовы, сводку, лог МО-обработки и снимок данных ФО (snapshot.json) в results/<время>_<сценарий>/.

Аргументы: --scenario <метка>  --count <портфелей, по умолчанию все тестовые>  --threads <потоков, по умолчанию 1>
           --no-recalc - на время прогона очистить константу «Операции после обмена»: 4-й вызов ничего не
           запускает, и снимок фиксирует состояние флагов сразу после вызова 872 (для сверки записи флагов).
"""
import argparse
import csv
import html
import json
import multiprocessing
import os
import re
import shutil
import tempfile
import time
import uuid

import snapshot
from diag_mode import versions_count
from stand_common import (PREFIX, N_PORTFOLIOS, PACKET_SIZE, TEST_DATE, MO_EPF, RESULTS_DIR, FLAG_POSITION,
                          EXTERNAL_IB_NAME, connect, query, query_table, to_array, date_1c, mandate_code, now_stamp)

KIND_ORDER = ["754: флаг до позиции", "768: позиция", "872: флаги после позиции", "удаление блокировок",
              "4-й: запуск перерасчета РСА", "рассылка перерасчета", "прочее"]


def classify(xml):
    comment = re.search(r"<Комментарий>(.*?)</Комментарий>", xml, re.S)
    if comment:
        text_ = html.unescape(comment.group(1))
        if "ТребуетсяУдалениеБлокировок" in text_:
            return "удаление блокировок"
        if "ТребуетсяПерерасчетРСАВыполнитьРассылку" in text_:
            return "рассылка перерасчета"
        if "ТребуетсяПерерасчетРСА" in text_:
            return "4-й: запуск перерасчета РСА"
        return "прочее"
    if "<ФактическаяПозиция>" in xml:
        return "768: позиция"
    if "<ДополнительныеСведения>" in xml:
        return "872: флаги после позиции" if "требуется_перерасчет_РСА" in xml else "754: флаг до позиции"
    return "прочее"


def fill_epf(mo, epf, codes_list):
    codes = to_array(mo, codes_list)
    rub = query(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = \"643\"")[0]["Ссылка"]
    params = {"Коды": codes, "Валюта": rub, "Дата": date_1c(mo, TEST_DATE),
              "МаскаБанк": PREFIX + "%_B", "МаскаДепо": PREFIX + "%_D", "МаскаЦБ": PREFIX + "_SH%"}
    money = query_table(mo, """
        ВЫБРАТЬ
            С.Владелец КАК Мандат, С.Ссылка КАК СчетМандата, &Валюта КАК Валюта,
            1000000 КАК Количество, 1000000 КАК Стоимость, 0 КАК Задолженность, ЛОЖЬ КАК ДоходыКПолучению
        ИЗ Справочник.СчетаМандатов КАК С
        ГДЕ С.КодСчета ПОДОБНО &МаскаБанк И С.Владелец.КодМандата В (&Коды)""", params)
    securities = query_table(mo, """
        ВЫБРАТЬ
            С.Владелец КАК Мандат, С.Ссылка КАК СчетМандата, Ак.Ссылка КАК Актив,
            10 КАК Количество, 10000 КАК Стоимость, 0 КАК СуммаНКД, 0 КАК Задолженность
        ИЗ Справочник.СчетаМандатов КАК С, Справочник.Активы КАК Ак
        ГДЕ С.КодСчета ПОДОБНО &МаскаДепо И С.Владелец.КодМандата В (&Коды) И Ак.ВнешнийКод ПОДОБНО &МаскаЦБ""", params)
    nav = query_table(mo, """
        ВЫБРАТЬ &Дата КАК Период, М.Ссылка КАК Мандат, 1030000 КАК СЧА, 1030000 КАК РСА
        ИЗ Справочник.Мандаты КАК М
        ГДЕ М.КодМандата В (&Коды)""", params)
    epf.ДенежныеСредства.Загрузить(money)
    epf.ЦенныеБумаги.Загрузить(securities)
    epf.СЧА_РСА.Загрузить(nav)
    return {"мандатов": nav.Количество(), "строк_денег": money.Количество(), "строк_цб": securities.Количество()}


def run_worker(args):
    """Один сеанс МО: создать обработку, заполнить своей частью мандатов и вызвать Опубликовать."""
    number, codes_list, session_id, out_dir = args
    mo = connect("wim_mo")
    tmp = os.path.join(tempfile.gettempdir(), f"внВыгрузкаОстатковМО_ФО_стенд_{number}.epf")
    shutil.copyfile(MO_EPF, tmp)
    # Своя обработка стенда: без предупреждения защиты от опасных действий (во внешнем соединении оно - исключение).
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
    filled = fill_epf(mo, epf, codes_list)
    started = time.perf_counter()
    error = None
    try:
        epf.Опубликовать(False, False, date_1c(mo, TEST_DATE))
    except Exception as exc:  # noqa: BLE001 - фиксируем и продолжаем сбор замеров
        error = str(exc)[:500]
    publish_s = time.perf_counter() - started
    with open(os.path.join(out_dir, f"mo_log_{number}.txt"), "w", encoding="utf-8") as f:
        f.write(epf.ТекстовыйЛог.ПолучитьТекст())
    result = {"поток": number, "заполнено": filled, "опубликовать_с": round(publish_s, 1),
              "есть_ошибки_МО": bool(epf.ЕстьОшибки), "исключение": error}
    os.remove(tmp)
    return result


def wait_background(fo, timeout_s=7200):
    started = time.perf_counter()
    while True:
        condition = fo.NewObject("Структура")
        condition.Вставить("Состояние", fo.СостояниеФоновогоЗадания.Активно)
        jobs = fo.ФоновыеЗадания.ПолучитьФоновыеЗадания(condition)
        names = [jobs.Получить(i).Наименование for i in range(jobs.Количество())]
        ours = [n for n in names if n.startswith("Пересчет фактической позиции") or n.startswith("Рассылка после пересчета")]
        if not ours:
            return time.perf_counter() - started
        if time.perf_counter() - started > timeout_s:
            return None
        time.sleep(3)


def recalc_jobs(fo, since):
    """Фоновые задания перерасчета РСА, начатые после since: число, сумма длительностей, окно от первого старта
    до последнего завершения (секунды, точность платформы - 1 с)."""
    condition = fo.NewObject("Структура")
    condition.Вставить("Начало", since)
    jobs = fo.ФоновыеЗадания.ПолучитьФоновыеЗадания(condition)
    items = []
    for i in range(jobs.Количество()):
        job = jobs.Получить(i)
        if str(job.Наименование).startswith("Пересчет фактической позиции") and job.Конец and job.Начало:
            items.append((job.Начало, job.Конец))
    if not items:
        return {"заданий": 0}
    durations = [(end - start).total_seconds() for start, end in items]
    window = (max(end for _, end in items) - min(start for start, _ in items)).total_seconds()
    return {"заданий": len(items), "сумма_с": sum(durations), "среднее_с": round(sum(durations) / len(items), 1),
            "окно_с": window}


def read_calls(fo, since):
    rows = query(fo, """
        ВЫБРАТЬ С.Тип КАК Тип, С.Идентификатор КАК Ид, С.ИдентификаторСвязи КАК Связь, С.ВремяМС КАК Мс,
            С.Код КАК Код, С.Тело КАК Тело
        ИЗ РегистрСведений.СобытияВнешнихСервисов КАК С
        ГДЕ С.ИмяСервиса = "Avancore" И С.Период >= &С""", {"С": since})
    requests = {}
    responses = {}
    for row in rows:
        if row["Тип"] == "Запрос":
            xml = row["Тело"].Получить()
            if not isinstance(xml, str):
                xml = xml.Получить()
            requests[row["Ид"]] = (int(row["Мс"]), xml)
        else:
            responses[row["Связь"]] = (int(row["Мс"]), row["Код"])
    calls = []
    for uid, (start_ms, xml) in requests.items():
        end = responses.get(uid)
        calls.append({
            "вид": classify(xml),
            "начало_мс": start_ms,
            "длительность_мс": (end[0] - start_ms) if end else None,
            "код_ответа": end[1] if end else None,
            "строк_доп_сведений": xml.count("<ДополнительныеСведения>"),
            "строк_фп": xml.count("<ФактическаяПозиция>"),
            "строк_сча": xml.count("<СтоимостьЧистыхАктивов>"),
        })
    calls.sort(key=lambda c: c["начало_мс"])
    return calls


def summarize(calls):
    summary = {}
    for kind in KIND_ORDER:
        items = [c for c in calls if c["вид"] == kind and c["длительность_мс"] is not None]
        if not items:
            continue
        total = sum(c["длительность_мс"] for c in items)
        rows = sum(c["строк_доп_сведений"] if kind.startswith(("754", "872")) else c["строк_фп"] for c in items)
        summary[kind] = {
            "вызовов": len(items),
            "всего_с": round(total / 1000, 1),
            "среднее_с": round(total / 1000 / len(items), 3),
            "строк": rows,
            "мс_на_строку": round(total / rows, 2) if rows else None,
        }
    return summary


def flags_ready(fo):
    rows = query(fo, """
        ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ Д.Свойство.Наименование = &Имя И Д.Значение = ИСТИНА
            И ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &Маска""",
                 {"Имя": FLAG_POSITION, "Маска": PREFIX + "%"})
    return rows[0]["Всего"]


def active_extensions(fo):
    exts = fo.РасширенияКонфигурации.Получить()
    return [exts.Получить(i).Имя for i in range(exts.Количество()) if exts.Получить(i).Активно]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="baseline")
    parser.add_argument("--count", type=int, default=N_PORTFOLIOS)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--no-recalc", action="store_true")
    args = parser.parse_args()

    out_dir = os.path.join(RESULTS_DIR, f"{now_stamp()}_{args.scenario}")
    os.makedirs(out_dir, exist_ok=True)

    codes = [mandate_code(i) for i in range(1, args.count + 1)]
    parts = [codes[i::args.threads] for i in range(args.threads)] if args.threads > 1 else [codes]
    session_id = str(uuid.uuid4()) if args.threads > 1 else ""

    fo = connect("wim_fo")
    versions_before = versions_count(fo)
    after_exchange = fo.Константы.ОперацииПослеОбмена.Получить()
    if args.no_recalc:
        fo.Константы.ОперацииПослеОбмена.Установить(fo.Справочники.ДополнительныеОтчетыИОбработки.ПустаяСсылка())
    since = fo.ТекущаяДатаСеанса()
    started = time.perf_counter()
    try:
        if args.threads > 1:
            with multiprocessing.Pool(args.threads) as pool:
                workers = pool.map(run_worker, [(n + 1, part, session_id, out_dir) for n, part in enumerate(parts)])
        else:
            workers = [run_worker((1, parts[0], session_id, out_dir))]
    finally:
        if args.no_recalc:
            fo.Константы.ОперацииПослеОбмена.Установить(after_exchange)
    total_s = time.perf_counter() - started
    for w in workers:
        print(f"Поток {w['поток']}: портфелей {w['заполнено']['мандатов']}, Опубликовать {w['опубликовать_с']} с, "
              f"ЕстьОшибки = {w['есть_ошибки_МО']}{', исключение: ' + w['исключение'] if w['исключение'] else ''}")
    print(f"Выгрузка всего (до завершения всех потоков): {total_s:.1f} с")

    background_s = wait_background(fo)
    print(f"Фоновый перерасчет на ФО после выгрузки: {background_s if background_s is None else round(background_s, 1)} с")
    ready = flags_ready(fo)
    print(f"Портфелей с позиция_выгружена = Истина: {ready} из {len(codes)}")

    jobs = recalc_jobs(fo, since)
    print(f"Фоновый перерасчет РСА: {jobs}")
    versioning_on = bool(fo.Константы.ИспользоватьВерсионированиеОбъектов.Получить())
    new_versions = versions_count(fo) - versions_before
    print(f"Версионирование портфелей: {'вкл' if versioning_on else 'выкл'}, новых версий (= записей флагов): {new_versions}")

    snap = snapshot.take(fo)
    with open(os.path.join(out_dir, "snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print(f"Снимок ФО: {snapshot.summary(snap)}")

    calls = read_calls(fo, since)
    summary = summarize(calls)
    result = {"сценарий": args.scenario, "портфелей": len(codes), "потоков": args.threads,
              "без_перерасчета": args.no_recalc, "расширения_ФО": active_extensions(fo),
              "версионирование": versioning_on, "новых_версий": new_versions, "перерасчет": jobs,
              "выгрузка_всего_с": round(total_s, 1), "потоки": workers,
              "фон_после_с": background_s and round(background_s, 1), "готово_флагов": ready,
              "вызовов": len(calls), "по_видам": summary, "снимок": snapshot.summary(snap)}
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "calls.csv"), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(calls[0].keys()) if calls else ["вид"], delimiter=";")
        writer.writeheader()
        writer.writerows(calls)

    print(f"Вызовов в логе ФО: {len(calls)}")
    for kind, s in summary.items():
        per_row = f", {s['мс_на_строку']} мс на строку" if s["мс_на_строку"] else ""
        print(f"  {kind}: {s['вызовов']} выз., всего {s['всего_с']} с, среднее {s['среднее_с']} с, строк {s['строк']}{per_row}")
    print(f"Результаты: {out_dir}")


if __name__ == "__main__":
    main()
