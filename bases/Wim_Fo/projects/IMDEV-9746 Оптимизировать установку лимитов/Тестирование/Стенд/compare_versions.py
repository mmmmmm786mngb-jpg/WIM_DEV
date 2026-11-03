# -*- coding: utf-8 -*-
"""IMDEV-9746. Сравнение версий 1.16 (ОРИГИНАЛ_1_16) и 1.17 (УСКОРЕНО_1_17) на стенде разработческой ФО.

Версии по очереди загружаются в рабочий элемент справочника дополнительных обработок ("Распространение правил с одного
клиента на список клиентов" - его по наименованию находят подписки ВТБ_Прод) с настройками стенда. Распространение
вызывает тестовая обработка T9530_ТестРОСТ (сценарий "Распространение") так же, как обработка "Операции после обмена".
Перед прогоном: python run_stand.py subs on, заглушка почты mock_smtp.py. После: run_stand.py subs off, restore, а
рабочему элементу - исходная обработка: python compare_versions.py restore.

    python compare_versions.py run <o|r> <1.16|1.17> <запусков>   прогон, результаты в results/compare.jsonl
    python compare_versions.py report                             сводка и сверка версий -> results/compare_summary.json
    python compare_versions.py restore                            исходная обработка и настройки рабочего элемента
"""
import datetime
import glob
import json
import os
import statistics as st
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import run_stand as rs  # noqa: E402
sys.path.insert(0, glob.glob(r"C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9530*\Тестирование\Стенд_замеры")[0])
import run_stage4_tests as s4  # noqa: E402

NAME = "внРаспространениеПравилСОдногоКлиентаНаСписокКлиентов"
VERSIONS = {"1.16": os.path.join(TASK, "ОРИГИНАЛ_1_16", NAME + ".epf"),
            "1.17": os.path.join(TASK, "УСКОРЕНО_1_17", NAME + ".epf")}
OUT = os.path.join(rs.RESULTS, "compare.jsonl")
MAIL_DIR = os.path.join(HERE, "results", "mail")
log = rs.log


def load_version(fo, version, settings):
    state = rs.load_state()
    item = rs.work_item(fo).ПолучитьОбъект()
    if "рабочий_элемент" not in state:
        state["рабочий_элемент"] = {"обработка": fo.XMLСтрока(item.ХранилищеОбработки),
                                    "настройки": fo.XMLСтрока(item.ХранилищеНастроек), "версия": item.Версия}
        rs.save_state(state)
    item.ХранилищеОбработки = fo.NewObject("ХранилищеЗначения", fo.NewObject("ДвоичныеДанные", VERSIONS[version]))
    item.Версия = version
    item.ХранилищеНастроек = fo.NewObject("ХранилищеЗначения", settings)
    item.ОбменДанными.Загрузка = True
    item.Записать()
    return item.Ссылка


def restore(fo):
    state = rs.load_state()
    saved = state.get("рабочий_элемент")
    if not saved:
        log("исходная обработка рабочего элемента не сохранялась")
        return
    storage = fo.NewObject("ОписаниеТипов", "ХранилищеЗначения").Типы().Получить(0)
    item = rs.work_item(fo).ПолучитьОбъект()
    item.ХранилищеОбработки = fo.XMLЗначение(storage, saved["обработка"])
    item.ХранилищеНастроек = fo.XMLЗначение(storage, saved["настройки"])
    item.Версия = saved["версия"]
    item.ОбменДанными.Загрузка = True
    item.Записать()
    del state["рабочий_элемент"]
    rs.save_state(state)
    log(f"рабочему элементу возвращены обработка {saved['версия']} и настройки")


def temp_xls(fo):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "ВременныеФайлы")
    return int(rs.checked(rs.scenario(fo, p, "временные файлы", retry=True))["данные"].ФайловXLS)


def measurements(fo, since):
    rows = rs.query(fo, """ВЫБРАТЬ З.КлючеваяОперация.Имя КАК Ключ, З.ВремяВыполнения КАК Время, З.Комментарий КАК Комментарий
        ИЗ РегистрСведений.ЗамерыВремени КАК З
        ГДЕ З.ДатаЗаписиЛокальная >= &Начало И З.КлючеваяОперация.Имя ПОДОБНО "РаспространениеПравилЛимитов%"
        УПОРЯДОЧИТЬ ПО З.ДатаНачалаЗамера""", {"Начало": since})
    return [{"ключ": r["Ключ"], "с": float(r["Время"]), "комментарий": r["Комментарий"] or ""} for r in rows]


def snapshot(fo, codes, props_names):
    """Данные клиентов: установки (класс, число строк лимитов), число порогов, дополнительные сведения стенда."""
    arr = rs.array(fo, codes)
    data = {c: {"установки": [], "порогов": 0, "сведения": {}} for c in codes}
    for r in rs.query(fo, """ВЫБРАТЬ ВЫРАЗИТЬ(У.ОбъектНазначения КАК Справочник.Портфели).ВнешнийКод КАК Код,
            ПРЕДСТАВЛЕНИЕ(У.КлассЛимита) КАК Класс, КОЛИЧЕСТВО(Л.Лимит) КАК Строк
        ИЗ Документ.УстановкаЛимитов КАК У ЛЕВОЕ СОЕДИНЕНИЕ Документ.УстановкаЛимитов.Лимиты КАК Л ПО Л.Ссылка = У.Ссылка
        ГДЕ У.Проведен И ВЫРАЗИТЬ(У.ОбъектНазначения КАК Справочник.Портфели).ВнешнийКод В (&Коды)
        СГРУППИРОВАТЬ ПО У.Ссылка, У.ОбъектНазначения, У.КлассЛимита""", {"Коды": arr}):
        data[r["Код"]]["установки"].append(f"{r['Класс']}:{int(r['Строк'])}")
    for r in rs.query(fo, """ВЫБРАТЬ П.Портфель.ВнешнийКод КАК Код, КОЛИЧЕСТВО(*) КАК Н ИЗ РегистрСведений.ПорогиЛимитов КАК П
        ГДЕ П.Портфель.ВнешнийКод В (&Коды) СГРУППИРОВАТЬ ПО П.Портфель.ВнешнийКод""", {"Коды": arr}):
        data[r["Код"]]["порогов"] = int(r["Н"])
    for r in rs.query(fo, """ВЫБРАТЬ ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод КАК Код, Д.Свойство.Наименование КАК Свойство,
            Д.Значение КАК Значение ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод В (&Коды) И Д.Свойство.Наименование ПОДОБНО "T9746%" """,
                          {"Коды": arr}):
        value = r["Значение"]
        text = fo.String(value) if not isinstance(value, (str, int, float, bool)) else value
        if isinstance(text, str) and len(text) >= 10 and text[2] == "." and text[5] == ".":
            text = "дата"  # даты сведений сравниваются по факту заполнения
        data[r["Код"]]["сведения"][r["Свойство"]] = str(text)
    for c in data:
        data[c]["установки"].sort()
    return data


def limit_versions(fo, since):
    rows = rs.query(fo, """ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Н ИЗ РегистрСведений.ВерсииОбъектов КАК Версии
        ГДЕ Версии.Объект ССЫЛКА Справочник.Лимиты И Версии.ДатаВерсии >= &Начало
            И ВЫРАЗИТЬ(Версии.Объект КАК Справочник.Лимиты).Наименование ПОДОБНО "T9746%" """, {"Начало": since})
    return int(rows[0]["Н"])


def letters_since(before):
    names = sorted(n for n in os.listdir(MAIL_DIR) if n.endswith(".eml")) if os.path.isdir(MAIL_DIR) else []
    new = [n for n in names if n not in before]
    result = []
    for n in new:
        raw = open(os.path.join(MAIL_DIR, n), "rb").read()
        result.append({"файл": n, "байт": len(raw), "вложение": b".xls" in raw.lower() or b"filename=" in raw.lower()})
    return names, result


def processing_errors(fo, since):
    table = fo.NewObject("ТаблицаЗначений")
    filt = fo.NewObject("Структура")
    filt.Вставить("ДатаНачала", since)
    filt.Вставить("Уровень", fo.УровеньЖурналаРегистрации.Ошибка)
    fo.ВыгрузитьЖурналРегистрации(table, filt)
    return [f"{table.Получить(i).Событие}: {(table.Получить(i).Комментарий or '')[:200]}" for i in range(table.Количество())]


def run(fo, mode, version, runs):
    state = rs.load_state()
    m = rs.MODES[mode]
    props = rs.properties(fo)
    mail = rs.mailing(fo)
    settings = rs.settings(fo, mode, props, mail)
    rs.ensure_conditions(fo, state)
    ref = load_version(fo, version, settings)  # после ensure_conditions: оба сохраняют состояние стенда
    harness = s4.test_epf(fo)
    client_type = rs.ensure_named(fo, "ТипыКлиентов", "ТипыКлиентов", m["тип"])
    per_run = 1 if mode == "o" else 2
    for _ in range(runs):
        batch = rs.next_clients(fo, mode, per_run)
        codes = [r["Код"] for r in batch]
        rs.set_client_type(fo, [r["Ссылка"] for r in batch], client_type)
        xls_before = temp_xls(fo)
        mail_before, _ = letters_since([])
        since = fo.ТекущаяДатаСеанса()
        p = fo.NewObject("Структура")
        p.Вставить("Сценарий", "Распространение")
        p.Вставить("ОбработкаСсылка", ref)
        out = s4.run_harness(fo, harness, p, f"IMDEV-9746 {version} {m['имя']} {', '.join(codes)}")
        jobs_wait = rs.wait_jobs(fo, "Запись версий лимитов")
        rs.wait_jobs(fo, rs.WORK_NAME)
        time.sleep(1)
        _, letters = letters_since(mail_before)
        record = {"режим": mode, "версия": version, "клиенты": codes, "начало": datetime.datetime.now().isoformat(timespec="seconds"),
                  "ошибка": out.get("ошибка") or out.get("ошибка_задания") or "", "замеры": measurements(fo, since),
                  "данные": snapshot(fo, codes, props), "версий_лимитов": limit_versions(fo, since),
                  "ожидание_задания_версий_с": jobs_wait[0], "письма": letters,
                  "временных_xls_прибавилось": temp_xls(fo) - xls_before, "ошибки_журнала": processing_errors(fo, since),
                  "дублей_установок": rs.duplicates(fo, codes)}
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        total = next((z["с"] for z in record["замеры"] if z["ключ"] == "РаспространениеПравилЛимитов"), None)
        log(f"  {version} {m['имя']} {codes}: запуск {total} с, писем {len(letters)}, версий {record['версий_лимитов']}, "
            f"xls +{record['временных_xls_прибавилось']}, ошибок журнала {len(record['ошибки_журнала'])}, "
            f"дублей {record['дублей_установок']}, {record['ошибка'][:200]}")


def report():
    rows = [json.loads(line) for line in open(OUT, encoding="utf-8")]
    summary = {}
    for mode in ("o", "r"):
        for version in ("1.16", "1.17"):
            items = [r for r in rows if r["режим"] == mode and r["версия"] == version and not r["ошибка"]]
            if not items:
                continue
            totals = [z["с"] for r in items for z in r["замеры"] if z["ключ"] == "РаспространениеПравилЛимитов"]
            create = [z["с"] for r in items for z in r["замеры"] if z["ключ"] == "РаспространениеПравилЛимитов.СозданиеУстановок"]
            summary[f"{mode}:{version}"] = {
                "запусков": len(items), "запуск_мед_с": round(st.median(totals), 2) if totals else None,
                "создание_на_класс_мед_с": round(st.median(create), 2) if create else None,
                "писем_на_запуск": round(st.mean(len(r["письма"]) for r in items), 2),
                "писем_с_вложением_на_запуск": round(st.mean(sum(1 for x in r["письма"] if x["вложение"]) for r in items), 2),
                "версий_лимитов_на_запуск": round(st.mean(r["версий_лимитов"] for r in items), 1),
                "временных_xls_на_запуск": round(st.mean(r["временных_xls_прибавилось"] for r in items), 2),
                "ошибок_журнала": sum(len(r["ошибки_журнала"]) for r in items),
                "дублей": sum(r["дублей_установок"] for r in items),
                "задание_версий_с": round(st.mean(r["ожидание_задания_версий_с"] for r in items), 1)}
            # данные клиента (без кода) - должны совпасть между версиями
            shapes = set()
            for r in items:
                for c, d in r["данные"].items():
                    shapes.add(json.dumps({"установки": d["установки"], "порогов": d["порогов"],
                                           "сведения": dict(sorted(d["сведения"].items()))}, ensure_ascii=False))
            summary[f"{mode}:{version}"]["варианты_данных_клиента"] = sorted(shapes)
    for mode in ("o", "r"):
        a, b = summary.get(f"{mode}:1.16"), summary.get(f"{mode}:1.17")
        if a and b:
            same = a["варианты_данных_клиента"] == b["варианты_данных_клиента"]
            summary[f"{mode}:сверка_данных"] = "совпадают" if same else "РАСХОДЯТСЯ"
            if a["запуск_мед_с"] and b["запуск_мед_с"]:
                summary[f"{mode}:ускорение_запуска"] = round(a["запуск_мед_с"] / b["запуск_мед_с"], 2)
    with open(os.path.join(rs.RESULTS, "compare_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def main():
    cmd = sys.argv[1]
    if cmd == "report":
        report()
        return
    fo = rs.connect("wim_fo")
    if cmd == "run":
        run(fo, sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif cmd == "restore":
        restore(fo)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
