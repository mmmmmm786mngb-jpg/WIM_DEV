# -*- coding: utf-8 -*-
"""Регресс 1.21 (по ревью 1.20: один запуск за раз, время цены, итог с ошибками) против 1.16 на dev ФО, стакан 1 с.

Эталон 1.16 берется из прогона 1.20 (reports/run_1_20.json каталога 1_20): исходное состояние готовится теми же
сценариями обвязки. Для пути формы дополнительно сверяется время цены (ВремяЦены) с журналом заглушки стакана.

Варианты, каждый на одинаковом исходном состоянии (ОчиститьСделки, ПропорцииПрод, ПозицияНаВчера):
  1.16                 - обвязка T9530_ТестРОСТ: Покупка.Команда, Продажа.Команда, Реинвест.Потоки (базовая линия);
  1.20 / 60 обвязка    - те же сценарии обвязки: команда регламентного задания и потоки без показа цен;
  1.20 / 60 форма      - путь кнопок формы: фоновые задания ПокупкаИзФормы и ПродажаИзФормы, 10 потоков
                         РеинвестСоздатьОрдера с ПоказыватьЦеныВРаботе и отправка пачки, как делает форма;
  1.20 / 0 форма       - то же с выключенным кешем: цены идут с биржи на каждое поручение, проверка интервала
                         сообщений.
Для путей формы каждое сообщение прогресса фонового задания читается и разбирается: этапы, цены, возраст,
источник, число сообщений.

Тестовая сборка 1.20-тест включает тестовый режим и имитацию стакана 1 с по умолчанию (фоновое задание формы
создает свой экземпляр обработки). Заглушка стакана stakan_mock.py (порт 18541) должна быть запущена.
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import time
import traceback

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TESTS, "1_18"))
sys.path.insert(0, os.path.join(TESTS, "1_19"))
sys.path.insert(0, os.path.join(TESTS, "1_20"))
import run_1_18_tests as base  # noqa: E402
import run_1_19_tests as v19  # noqa: E402

stage4 = base.stage4
BUILD_DIR = os.path.join(TESTS, "1_18", "сборки")
EPF_116 = os.path.join(BUILD_DIR, "1.16-тест", "внСозданиеТорговыхПорученийРОСТ.epf")
EPF_121 = os.path.join(BUILD_DIR, "1.21-тест", "внСозданиеТорговыхПорученийРОСТ.epf")
EPF_120 = EPF_121
OUT = os.path.join(HERE, "reports", "run_1_21.json")
BASELINE = os.path.join(TESTS, "1_20", "reports", "run_1_20.json")
PROGRESS_PREFIX = "{СтандартныеПодсистемы.ДлительныеОперации}"
VARIANTS = [
    ("1.16", "обвязка", EPF_116, None),
    ("1.21 / 60 обвязка", "обвязка", EPF_121, 60),
    ("1.21 / 60 форма", "форма", EPF_121, 60),
    ("1.21 / 0 форма", "форма", EPF_121, 0),
]


def struct(fo, **values):
    result = fo.NewObject("Структура")
    for key, value in values.items():
        result.Вставить(key, value)
    return result


def prop(value, name, default=None):
    try:
        return getattr(value, name)
    except Exception:  # noqa: BLE001 - нет свойства у структуры 1С
        return default


def rost_object(fo, rost_ref):
    """Экземпляр обработки из зарегистрированной сборки, как у формы: настройки из справочника."""
    tmp = os.path.join(tempfile.gettempdir(), "T9531_120_" + str(os.getpid()) + ".epf")
    shutil.copyfile(EPF_120, tmp)
    obj = fo.ВнешниеОбработки.Создать(tmp, False)
    obj.УстановитьНастройки(struct(fo, ДополнительнаяОбработкаСсылка=rost_ref))
    return obj


def start_job(fo, rost_ref, method, params, name):
    exec_params = fo.ДлительныеОперации.ПараметрыВыполненияВФоне(fo.NewObject("УникальныйИдентификатор"))
    exec_params.НаименованиеФоновогоЗадания = name
    exec_params.ЗапуститьВФоне = True
    task = struct(fo, ИмяОбработки="ВнешняяОбработка.СозданиеТорговыхПорученийРОСТ", ИмяМетода=method,
                  ПараметрыВыполнения=params, ЭтоВнешняяОбработка=True, ДополнительнаяОбработкаСсылка=rost_ref)
    return fo.ДлительныеОперации.ВыполнитьВФоне("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", task,
                                                 exec_params)


def parse_progress(fo, text, started):
    data = fo.ОбщегоНазначения.ЗначениеИзСтрокиXML(text[len(PROGRESS_PREFIX):])
    extra = prop(data, "ДополнительныеПараметры")
    if extra is None:
        return None
    prices = []
    items = extra.Цены
    for i in range(items.Количество()):
        item = items.Получить(i)
        prices.append({"бумага": fo.String(item.Актив), "направление": fo.String(item.Направление),
                       "цена": float(item.Цена), "источник": item.Источник, "возраст_с": int(item.ВозрастСек),
                       "время": fo.XMLСтрока(item.ВремяЦены),
                       "поручений_по_цене": int(item.ПорученийПоЦене), "поручений": int(item.Поручений)})
    return {"t": round(time.time() - started, 1), "поток": int(extra.НомерПотока), "этап": extra.Этап, "цены": prices}


def wait_jobs(fo, jobs, timeout=3600):
    """Ждет фоновые задания, читая все сообщения: прогресс разбирается, остальные сохраняются текстом."""
    started = time.time()
    state = {num: {"сообщений_прогресса": 0, "снимки": [], "прочие_сообщения": [], "завершено": False}
             for num in jobs}
    while True:
        active = 0
        for num, op in jobs.items():
            info = state[num]
            if info["завершено"]:
                continue
            job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(op.ИдентификаторЗадания)
            finished = job is None or job.Состояние != fo.СостояниеФоновогоЗадания.Активно
            messages = job.ПолучитьСообщенияПользователю(True) if job is not None else None
            for i in range(messages.Количество() if messages is not None else 0):
                text = messages.Получить(i).Текст
                if text.startswith(PROGRESS_PREFIX):
                    info["сообщений_прогресса"] += 1
                    snap = parse_progress(fo, text, started)
                    # Форма видит только последнее сообщение прогресса: важно, чье оно в конце задания.
                    info["последнее_сообщение_с_ценами"] = snap is not None
                    if snap is not None:
                        info["снимки"].append(snap)
                    else:
                        info["сообщений_конфигурации"] = info.get("сообщений_конфигурации", 0) + 1
                else:
                    info["прочие_сообщения"].append(text[:300])
            if finished:
                info["завершено"] = True
                info["длительность_с"] = round(time.time() - started, 1)
                info["состояние"] = fo.String(job.Состояние) if job is not None else "нет задания"
                info["ошибка"] = (fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
                                  if job is not None and job.ИнформацияОбОшибке is not None else "")
            else:
                active += 1
        if not active or time.time() - started > timeout:
            break
        time.sleep(1)
    return state


def price_time_check(snaps):
    """Время цены "биржа" против конца запросов заглушки стакана (время локальное, допуск 1 с)."""
    calls = json.loads(base.mock("/calls"))
    ends = [datetime.datetime.fromtimestamp(c["end"]) for c in calls]
    times = sorted({p["время"] for s in snaps for p in s["цены"] if p["источник"] == "биржа"})
    result = []
    for value in times:
        moment = datetime.datetime.fromisoformat(value)
        nearest = min((abs((moment - end).total_seconds()) for end in ends), default=None)
        result.append({"время_цены": value, "до_ближайшего_ответа_с": None if nearest is None else round(nearest, 2)})
    return {"цен_с_биржи": len(times), "в_допуске_1с": sum(1 for x in result if x["до_ближайшего_ответа_с"] is not None
                                                          and x["до_ближайшего_ответа_с"] <= 1.0), "детали": result}


def summary(info):
    snaps = info["снимки"]
    stages = []
    for snap in snaps:
        if not stages or stages[-1] != snap["этап"]:
            stages.append(snap["этап"])
    last = snaps[-1]["цены"] if snaps else []
    sources = sorted({p["источник"] for s in snaps for p in s["цены"]})
    gaps = [round(b["t"] - a["t"], 1) for a, b in zip(snaps, snaps[1:])]
    return {
        "длительность_с": info.get("длительность_с"), "состояние": info.get("состояние"),
        "ошибка": (info.get("ошибка") or "")[:500], "сообщений_прогресса": info["сообщений_прогресса"],
        "сообщений_конфигурации": info.get("сообщений_конфигурации", 0),
        "последнее_сообщение_с_ценами": info.get("последнее_сообщение_с_ценами"),
        "этапы": stages, "источники": sources, "последние_цены": last,
        "поручений_в_последнем_снимке": sum(p["поручений"] for p in last),
        "макс_возраст_с": max([p["возраст_с"] for s in snaps for p in s["цены"]] or [0]),
        "мин_интервал_с": min(gaps) if gaps else None, "прочие_сообщения": info["прочие_сообщения"][:20],
    }


def form_single(fo, rost_ref, method, params, title):
    base.mock("/reset")
    op = start_job(fo, rost_ref, method, params, "T9531 1.20 " + title)
    if op.Статус == "Ошибка":
        return {"шаг": title, "ошибка": op.ПодробноеПредставлениеОшибки}
    info = wait_jobs(fo, {0: op})[0]
    result = fo.ПолучитьИзВременногоХранилища(op.АдресРезультата)
    step = {"шаг": title, **summary(info), "запросов_стакана": base.mock_count(), "снимки": info["снимки"],
            "сверка_времени": price_time_check(info["снимки"])}
    if result is not None:
        step["важность"] = int(result.ВажностьОшибки)
        step["строк_списка_после"] = int(result.СписокПортфелей.Количество())
        step["лог_хвост"] = (result.Лог or "")[-400:]
    return step


def form_threads(fo, rost_ref, obj, title):
    """Кнопка "Создать поручения в потоке": 200 портфелей в 10 потоках, затем отправка пачки, как в форме."""
    base.mock("/reset")
    obj.РеинвестОбновитьСписокПотфелей(stage4.date_1c(fo, v19.COUPON_DATE), True, 0, 0, "", 0)
    rows = obj.СписокПортфелейРеинвестирование
    rows.Сортировать("Портфель")
    lists = {n: fo.NewObject("Массив") for n in range(1, 11)}
    marked, thread = 0, 1
    for i in range(rows.Количество()):
        row = rows.Получить(i)
        if fo.String(row.Поручение) or float(row.СуммаРеинвестирования) <= 0 or marked >= 200:
            continue
        item = struct(fo, Портфель=row.Портфель, СубПортфель=row.СубПортфель, Актив=row.Актив,
                      СуммаРеинвестирования=row.СуммаРеинвестирования, Поручение=row.Поручение)
        lists[thread].Добавить(item)
        marked += 1
        thread = 1 if thread == 10 else thread + 1
    jobs = {}
    started = time.time()
    for num, items in lists.items():
        if not items.Количество():
            continue
        params = struct(fo, ПортфелиСписок=fo.NewObject("ФиксированныйМассив", items), НомерПотока=num,
                        ОбработкаСсылка=rost_ref, ПортфелейВПакете=marked, ПоказыватьЦеныВРаботе=True)
        jobs[num] = start_job(fo, rost_ref, "РеинвестСоздатьОрдера", params, "T9531 1.20 поток " + str(num))
    state = wait_jobs(fo, jobs)
    orders = fo.NewObject("Массив")
    errors = []
    for num, op in jobs.items():
        result = fo.ПолучитьИзВременногоХранилища(op.АдресРезультата)
        if result is None:
            errors.append(num)
            continue
        refs = result.ПорученияНаОтправку
        for i in range(refs.Количество()):
            orders.Добавить(refs.Получить(i))
    created = round(time.time() - started, 1)
    # Форма отправляет пачку серверным вызовом; во внешнем соединении модуль Распорядители не инициализируется,
    # поэтому отправка - фоновым заданием тестовой процедуры ОтправитьПачкуВФоне.
    send = start_job(fo, rost_ref, "ОтправитьПачкуВФоне", struct(fo, Поручения=orders), "T9531 1.20 отправка пачки")
    sent = wait_jobs(fo, {0: send})[0]
    threads = {str(num): summary(info) for num, info in state.items()}
    return {"шаг": title, "портфелей": marked, "потоков": len(jobs), "поручений": int(orders.Количество()),
            "потоки_без_результата": errors, "создание_с": created,
            "отправка": {"состояние": sent.get("состояние"), "ошибка": (sent.get("ошибка") or "")[:500]},
            "длительность_с": round(time.time() - started, 1), "запросов_стакана": base.mock_count(),
            "сообщений_прогресса": sum(t["сообщений_прогресса"] for t in threads.values()),
            "поручений_в_последних_снимках": sum(t["поручений_в_последнем_снимке"] for t in threads.values()),
            "потоки": threads}


def form_variant(label, path, seconds):
    fo = stage4.connect("wim_fo")
    test_ref = base.harness_ref(fo)
    prepare = [base.service(fo, test_ref, name, name + " " + label)
               for name in ("ОчиститьСделки", "ПропорцииПрод", "ПозицияНаВчера")]
    rost_ref = v19.register(fo, path, seconds)
    started = stage4.now_iso(fo)
    obj = rost_object(fo, rost_ref)
    steps = []
    try:
        obj.ОбновитьСписокПортфелейПокупка("", 0)
        params = struct(fo, ОбработкаСсылка=rost_ref, ПоказыватьЦеныВРаботе=True,
                        СписокПортфелей=obj.СписокПортфелейПокупка.Выгрузить())
        steps.append(form_single(fo, rost_ref, "ПокупкаИзФормы", params, "Покупка.ФормаФон"))
        stage4.log("done", label, steps[-1]["шаг"], steps[-1].get("длительность_с"), steps[-1].get("ошибка", "")[:200])

        obj.ЗаполнитьСписокПродажаАктивов(True, "", 0)
        params = struct(fo, ОбработкаСсылка=rost_ref, ПоказыватьЦеныВРаботе=True, НеПоказыватьПортфелиСПоручениями=True,
                        СписокПортфелей=obj.СписокПортфелейПродажа.Выгрузить())
        steps.append(form_single(fo, rost_ref, "ПродажаИзФормы", params, "Продажа.ФормаФон"))
        stage4.log("done", label, steps[-1]["шаг"], steps[-1].get("длительность_с"), steps[-1].get("ошибка", "")[:200])

        steps.append(form_threads(fo, rost_ref, obj, "Реинвест.ПотокиФормы"))
        stage4.log("done", label, steps[-1]["шаг"], steps[-1].get("длительность_с"))
    except Exception:
        steps.append({"шаг": "ошибка прогона", "ошибка": traceback.format_exc()[-1500:]})
        stage4.log("ERROR", label, steps[-1]["ошибка"])
    fo = stage4.connect("wim_fo")
    return {"вариант": label, "срок_кеша": seconds, "подготовка": prepare, "шаги": steps,
            "поручения": base.orders(fo), "статусы": base.statuses(fo), "замеры": stage4.measurements(fo, started)}


def main():
    base.mock("/stats")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    report = {"дата": datetime.datetime.now().isoformat(timespec="seconds"), "варианты": []}
    if os.path.exists(OUT):
        report = json.load(open(OUT, encoding="utf-8"))
    else:
        base_variant = [v for v in json.load(open(BASELINE, encoding="utf-8"))["варианты"] if v["вариант"] == "1.16"][0]
        report["варианты"].append(base_variant)
    done = {item["вариант"] for item in report["варианты"]}
    for label, kind, path, seconds in VARIANTS:
        if label in done:
            continue
        if kind == "обвязка":
            item = v19.run_variant(label, path, seconds)
        else:
            item = form_variant(label, path, seconds)
        report["варианты"].append(item)
        with open(OUT, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    by_label = {item["вариант"]: item for item in report["варианты"]}
    old = by_label["1.16"]
    report["сверки"] = {}
    for label, _, _, _ in VARIANTS[1:]:
        new = by_label[label]
        report["сверки"][label] = {"поручения": base.compare(old["поручения"], new["поручения"]),
                                   "статусы_совпадают": old["статусы"] == new["статусы"]}
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    for label, check in report["сверки"].items():
        c = check["поручения"]
        stage4.log("compare", label, "same", c["совпало"], "diff", len(c["расхождения"]), "only16",
                   len(c["только_1_16"]), "only_new", len(c["только_1_18"]), "statuses", check["статусы_совпадают"])
    stage4.log("DONE", OUT)



if __name__ == "__main__":
    main()
