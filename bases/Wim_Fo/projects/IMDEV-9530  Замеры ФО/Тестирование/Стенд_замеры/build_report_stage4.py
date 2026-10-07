# -*- coding: utf-8 -*-
"""HTML-отчет о тестировании замеров этапа 4 (IMDEV-9530) по результатам run_stage4_tests.py (results/stage4_<серия>.json).

Записи регистра ЗамерыВремени относятся к шагам прогона по дате начала замера (ДатаНачалаЗамера - миллисекунды UTC,
шаги - время сеанса ФО, UTC+3): БСП записывает замеры с задержкой, дата записи для этого не годится.

    python build_report_stage4.py [серия]        по умолчанию S3
"""
import base64
import datetime
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(TASK, "Тестирование", "Отчет о тестировании замеров, этап 4.html")
TZ = datetime.timedelta(hours=3)
ROST = "СозданиеТорговыхПорученийРОСТ"


def esc(s):
    return html.escape(str(s if s is not None else ""))


def short(key):
    return key.replace(ROST + ".", "РОСТ.")


def start_local(r):
    return datetime.datetime(1, 1, 1) + datetime.timedelta(milliseconds=r["начало_мс"]) + TZ


def norm_code(code):
    return re.sub(r"_(O|M)_", "_*_", code or "")


def norm_prop(name):
    return (name or "").replace("(ориг)", "(версия)").replace("(замеры)", "(версия)")


def norm_value(v):
    if isinstance(v, str) and re.match(r"^\d\d\.\d\d\.\d{4} \d", v):
        return v[:10]
    return v


# Ожидаемый состав записей версии с замерами по шагам прогона (сверка покрытия).
# ключ -> (вес или None, подстрока комментария или None, признак ошибки или None, число записей)
EXPECT = {
    "Покупка.Команда": {
        "РОСТ.Покупка": (26, "Запуск: регламентное задание; Портфелей: 3; Поручений: 3; Проведений: 9", False, 1),
        "РОСТ.Покупка.ОтборПортфелей": (3, None, None, 1), "РОСТ.Покупка.РасчетПотоковОФЗ": (1, None, None, 1),
        "РОСТ.Покупка.ЗаписьПоручения": (3, None, None, 1), "РОСТ.Покупка.ЦенаИзСтакана": (3, None, None, 1),
        "РОСТ.Покупка.ПроведениеСЦеной": (3, None, None, 1), "РОСТ.Покупка.РасчетКоличестваОФЗ": (3, None, None, 1),
        "РОСТ.Покупка.ПроведениеКоличества": (3, None, None, 1), "РОСТ.Покупка.СтатусПортфеля": (3, None, None, 1),
        "РОСТ.Покупка.ПроверкаИОтправка": (3, None, None, 1), "РОСТ.Покупка.Рассылка": (1, None, None, 1),
        "РОСТ.Покупка.Удельный": (26, None, None, 1)},
    "Покупка.Форма": {
        "РОСТ.Покупка": (56, "Запуск: форма; Портфелей: 6; Поручений: 9; Проведений: 27", False, 1),
        "РОСТ.Покупка.РасчетПотоковОФЗ": (1, None, None, 1), "РОСТ.Покупка.ЗаписьПоручения": (9, None, None, 1),
        "РОСТ.Покупка.ЦенаИзСтакана": (9, None, None, 1), "РОСТ.Покупка.ПроведениеСЦеной": (9, None, None, 1),
        "РОСТ.Покупка.ПроведениеСуммы": (6, None, None, 1), "РОСТ.Покупка.РасчетКоличестваОФЗ": (3, None, None, 1),
        "РОСТ.Покупка.ПроведениеКоличества": (3, None, None, 1), "РОСТ.Покупка.СтатусПортфеля": (6, None, None, 1),
        "РОСТ.Покупка.ПроверкаИОтправка": (9, None, None, 1), "РОСТ.Покупка.Завершение": (1, None, None, 1),
        "РОСТ.Покупка.Удельный": (56, None, None, 1)},
    "Продажа.Команда": {
        "РОСТ.Продажа": (34, "Запуск: регламентное задание; Портфелей: 3; Поручений: 6; Проведений: 12", False, 1),
        "РОСТ.Продажа.ОтборПортфелей": (6, None, None, 1), "РОСТ.Продажа.ЗаписьПоручения": (6, None, None, 1),
        "РОСТ.Продажа.ЦенаИзСтакана": (6, None, None, 1), "РОСТ.Продажа.ПроведениеСЦеной": (6, None, None, 1),
        "РОСТ.Продажа.СтатусПортфеля": (3, None, None, 1), "РОСТ.Продажа.ПроверкаИОтправка": (6, None, None, 1),
        "РОСТ.Продажа.Рассылка": (1, None, None, 1), "РОСТ.Продажа.Удельный": (34, None, None, 1)},
    "Продажа.Форма": {
        "РОСТ.Продажа": (28, "Запуск: форма; Портфелей: 3; Поручений: 6; Проведений: 12", False, 1),
        "РОСТ.Продажа.ЗаписьПоручения": (6, None, None, 1), "РОСТ.Продажа.ЦенаИзСтакана": (6, None, None, 1),
        "РОСТ.Продажа.ПроведениеСЦеной": (6, None, None, 1), "РОСТ.Продажа.СтатусПортфеля": (3, None, None, 1),
        "РОСТ.Продажа.ПроверкаИОтправка": (6, None, None, 1), "РОСТ.Продажа.Завершение": (1, None, None, 1),
        "РОСТ.Продажа.Удельный": (28, None, None, 1)},
    "Реинвест.Форма": {},
    "Реинвест.Потоки": {
        "РОСТ.Реинвестирование": (6, "Портфелей в пакете: 6; Портфелей: 1; Поручений: 1; Проведений: 3", False, 6),
        "РОСТ.Реинвестирование.ЗаписьПоручения": (1, None, None, 6), "РОСТ.Реинвестирование.ЦенаИзСтакана": (1, None, None, 6),
        "РОСТ.Реинвестирование.ПроведениеСЦеной": (1, None, None, 6), "РОСТ.Реинвестирование.ПроведениеСуммы": (1, None, None, 6),
        "РОСТ.Реинвестирование.СтатусПортфеля": (1, None, None, 6), "РОСТ.Реинвестирование.Завершение": (1, None, None, 6),
        "РОСТ.Реинвестирование.Удельный": (6, None, None, 6),
        "РОСТ.ОтправкаПачки": (7, "Запуск: форма; Портфелей: 6; Поручений: 6; Проведений: 0", False, 1),
        "РОСТ.ОтправкаПачки.ПроверкаИОтправка": (6, None, None, 1), "РОСТ.ОтправкаПачки.Завершение": (1, None, None, 1),
        "РОСТ.ОтправкаПачки.Удельный": (7, None, None, 1)},
    "Блокировки.Потоки": {
        "РОСТ.ПродажаПодБлокировки": (6, "Портфелей в пакете: 6; Портфелей: 1; Поручений: 1; Проведений: 3", False, 6),
        "РОСТ.ПродажаПодБлокировки.ЗаписьПоручения": (1, None, None, 6),
        "РОСТ.ПродажаПодБлокировки.ЦенаИзСтакана": (1, None, None, 6),
        "РОСТ.ПродажаПодБлокировки.ПроведениеСЦеной": (1, None, None, 6),
        "РОСТ.ПродажаПодБлокировки.ПроведениеСуммы": (1, None, None, 6),
        "РОСТ.ПродажаПодБлокировки.СтатусПортфеля": (1, None, None, 6),
        "РОСТ.ПродажаПодБлокировки.Завершение": (1, None, None, 6), "РОСТ.ПродажаПодБлокировки.Удельный": (6, None, None, 6),
        "РОСТ.ОтправкаПачки": (7, "Запуск: форма; Портфелей: 6; Поручений: 6; Проведений: 0", False, 1),
        "РОСТ.ОтправкаПачки.ПроверкаИОтправка": (6, None, None, 1), "РОСТ.ОтправкаПачки.Завершение": (1, None, None, 1),
        "РОСТ.ОтправкаПачки.Удельный": (7, None, None, 1)},
    "Покупка.БСП": {
        "РОСТ.Покупка": (None, "Запуск: регламентное задание; Портфелей: 5; Поручений: 0; Проведений: 2", False, 1),
        "РОСТ.Покупка.ОтборПортфелей": (5, None, None, 1), "РОСТ.Покупка.РасчетПотоковОФЗ": (1, None, None, 1),
        "РОСТ.Покупка.ЗаписьПоручения": (2, None, None, 1), "РОСТ.Покупка.ЦенаИзСтакана": (2, None, None, 1),
        "РОСТ.Покупка.РасчетКоличестваОФЗ": (2, None, None, 1), "РОСТ.Покупка.ПроверкаИОтправка": (None, None, None, 1),
        "РОСТ.Покупка.Рассылка": (1, None, None, 1), "РОСТ.Покупка.Удельный": (None, None, None, 1)},
    "Реинвест.ВебКлиент": {
        "РОСТ.Реинвестирование": (3, "Портфелей в пакете: 3; Портфелей: 1; Поручений: 0; Проведений: 1", False, 3),
        "РОСТ.Реинвестирование.ЗаписьПоручения": (1, None, None, 3), "РОСТ.Реинвестирование.ЦенаИзСтакана": (1, None, None, 3),
        "РОСТ.Реинвестирование.Завершение": (1, None, None, 3), "РОСТ.Реинвестирование.Удельный": (3, None, None, 3)},
    "Распространение": {
        "РаспространениеПравилЛимитов": (7, "Классов: 2; Новых клиентов: 12; Распространено: 7; Без автоустановки: 4; "
                                            "Запись версий лимитов в фоне: 7", False, 1),
        "РаспространениеПравилЛимитов.ПоискНовыхКлиентов": (6, "Новых клиентов: 6", False, 2),
        "РаспространениеПравилЛимитов.СозданиеУстановок": (None, "Новых клиентов: 6", False, 2),
        "РаспространениеПравилЛимитов.Рассылка": (1, "Класс: ", False, 2)},
    "Неторговые.Успех": {
        "ЗагрузкаНеторговыхПорученийРОСТ": (3, "Поручений создано: 3", False, 1),
        "ЗагрузкаНеторговыхПорученийРОСТ.СозданиеПоручений": (3, "Поручений создано: 3", False, 1),
        "ЗагрузкаНеторговыхПорученийРОСТ.Рассылка": (1, None, False, 1)},
    "Неторговые.ОтказВызова": {
        "ЗагрузкаНеторговыхПорученийРОСТ": (1, "Поручений создано: 0", True, 1)},
    "Неторговые.СервисНедоступен": {
        "ЗагрузкаНеторговыхПорученийРОСТ": (1, "Поручений создано: 0", True, 1),
        "ЗагрузкаНеторговыхПорученийРОСТ.СозданиеПоручений": (1, "Поручений создано: 0", False, 1),
        "ЗагрузкаНеторговыхПорученийРОСТ.Рассылка": (1, None, False, 1)},
}

SCENARIO_TEXT = {
    "Покупка.Команда": ("Торговые поручения РОСТ", "Команда регламентного задания «Покупка» (ВыполнитьКоманду), тестовый режим",
                        "3 портфеля «Поиск ДС» с вводом ДС: поручения ОФЗ"),
    "Покупка.Форма": ("Торговые поручения РОСТ", "Кнопки формы «Обновить список» и «Создать и отправить поручения»",
                      "3 портфеля второго этапа (ОФЗ исполнено) и 3 портфеля первого этапа"),
    "Продажа.Команда": ("Торговые поручения РОСТ", "Команда регламентного задания «Продажа»",
                        "3 портфеля «Расторжение инициировано», по 2 бумаги"),
    "Продажа.Форма": ("Торговые поручения РОСТ", "Кнопки формы «Получить список» и «Создать поручения продажа»",
                      "3 портфеля, по 2 бумаги"),
    "Реинвест.Форма": ("Торговые поручения РОСТ", "Кнопка формы «Создать и отправить ордера» (реинвестирование без потоков)",
                       "3 отмеченных портфеля с купоном"),
    "Реинвест.Потоки": ("Торговые поручения РОСТ", "Кнопка формы «Создать поручения в потоке» и отправка пачки",
                        "6 портфелей с купоном, 6 фоновых потоков"),
    "Блокировки.Потоки": ("Торговые поручения РОСТ", "Продажи под блокировки: потоки формы и отправка пачки",
                          "6 портфелей с поручением на вывод ДС"),
    "Покупка.БСП": ("Торговые поручения РОСТ", "Команда через БСП ДополнительныеОтчетыИОбработки.ВыполнитьКоманду "
                    "(путь регламентного задания, тестовый режим выключен)", "2 портфеля «Поиск ДС»"),
    "Реинвест.ВебКлиент": ("Торговые поручения РОСТ", "Веб-клиент: форма обработки, «Создать поручения в потоке»",
                           "3 портфеля с купоном, тестовый режим выключен"),
    "Распространение": ("Распространение правил", "ВыполнитьРаспространениеПравилПослеОбмена, как из «Операций после обмена»",
                        "6 новых клиентов, классы «комплаенс» и «риски»"),
    "Неторговые.Успех": ("Неторговые поручения РОСТ", "Команда регламентного задания, сервис 1С:ДО отвечает",
                         "5 портфелей «Поиск ДС»: 3 с суммой, 1 не на брокере, 1 с нулем"),
    "Неторговые.ОтказВызова": ("Неторговые поручения РОСТ", "Команда регламентного задания, вызов сервиса возвращает ошибку",
                               "ошибка SOAP по одному договору"),
    "Неторговые.СервисНедоступен": ("Неторговые поручения РОСТ", "Команда регламентного задания, сервис недоступен",
                                    "адрес сервиса без слушателя"),
}


def load(series):
    with open(os.path.join(HERE, "results", f"stage4_{series}.json"), encoding="utf-8") as f:
        return json.load(f)


def step_windows(state):
    steps = []
    for run in state["runs"]:
        for st in run["шаги"]:
            if "начало" not in st or st.get("шаг") in ("Статусы", "Ready", "Данные"):
                continue
            steps.append({"версия": run["версия"], "обработка": run.get("обработка", "торговые"), "шаг": st["шаг"],
                          "начало": datetime.datetime.fromisoformat(st["начало"]),
                          "конец": datetime.datetime.fromisoformat(st["конец"]), "данные": st, "записи": []})
    return steps


def assign(steps, records):
    """Относит записи к шагам. Шаги идут последовательно, окно шага - от его начала до начала следующего шага (время
    шагов - с точностью до секунды). Записи одного сеанса, идущие подряд с разрывом меньше 20 с, - одно выполнение
    (фоновое задание сценария или его поток): кластер относится к шагу по своей первой записи, чтобы записи конца
    сценария (отправка пачки) не перешли в окно следующего шага. Номера сеансов сервер использует повторно, поэтому
    кластер ограничен разрывом."""
    ordered = sorted(steps, key=lambda s: s["начало"])
    for i, s in enumerate(ordered):
        s["окно_до"] = ordered[i + 1]["начало"] if i + 1 < len(ordered) else s["конец"] + datetime.timedelta(minutes=10)

    def step_of(t):
        for s in ordered:
            if s["начало"] <= t < s["окно_до"]:
                return s
        return None

    unassigned, clusters = [], []
    last = {}
    for r in sorted(records, key=lambda x: x["начало_мс"]):
        t = start_local(r)
        prev = last.get(r["сеанс"])
        if prev is not None and (t - prev["t"]).total_seconds() < 20:
            prev["записи"].append(r)
            prev["t"] = t
        else:
            cluster = {"t": t, "первая": t, "записи": [r]}
            clusters.append(cluster)
            last[r["сеанс"]] = cluster
    for cluster in clusters:
        step = step_of(cluster["первая"])
        if step is None:
            unassigned += cluster["записи"]
        else:
            step["записи"] += cluster["записи"]
    return unassigned


def check_step(step):
    """Сверка записей шага с ожидаемыми: список (ключ, ожидание, факт, итог)."""
    expect = EXPECT.get(step["шаг"], {})
    by_key = defaultdict(list)
    for r in step["записи"]:
        by_key[short(r["ключ"])].append(r)
    rows = []
    for key, (weight, comment, error, count) in expect.items():
        got = by_key.get(key, [])
        problems = []
        if len(got) != count:
            problems.append(f"записей {len(got)} вместо {count}")
        for r in got:
            if weight is not None and r["вес"] != weight:
                problems.append(f"вес {r['вес']:g} вместо {weight}")
            if comment and comment not in (r["комментарий"] or ""):
                problems.append("комментарий не совпадает")
            if error is not None and r["ошибка"] != error:
                problems.append(f"признак ошибки {r['ошибка']}")
        exp_text = f"{count} зап." + (f", вес {weight}" if weight is not None else "") + \
                   (", ошибка" if error else "") + (f"; «{comment}»" if comment else "")
        fact = "; ".join(sorted({f"вес {r['вес']:g}" + (", ошибка" if r["ошибка"] else "") for r in got})) or "нет"
        rows.append((key, exp_text, f"{len(got)} зап.: {fact}", not problems, "; ".join(sorted(set(problems)))))
    extra = sorted(k for k in by_key if k not in expect)
    return rows, extra


def compare_orders(state):
    def key_rows(version):
        groups = defaultdict(list)
        for o in state["orders"][version]:
            code = norm_code(o["Портфель"])
            if "_F" in code:
                continue
            groups[code].append((o["Вид"], o["ВидНеторг"], o["Направление"], o["Актив"], o["Количество"], o["Цена"],
                                 o["Сумма"], o["Проведен"], o["Удален"], o["Статус"]))
        return {k: sorted(v, key=str) for k, v in groups.items()}
    a, b = key_rows("ориг"), key_rows("замеры")
    diffs = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    return a, b, diffs


def compare_dict_rows(rows_a, rows_b, key_fields, value_field=None):
    def norm(rows):
        out = Counter()
        for r in rows:
            k = tuple(norm_code(r[f]) if f == "Портфель" else norm_prop(r[f]) for f in key_fields)
            v = norm_value(r[value_field]) if value_field else None
            out[(k, v)] += 1
        return out
    na, nb = norm(rows_a), norm(rows_b)
    return na, nb, (na - nb) + (nb - na)


def img_tag(path, alt):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f'<img alt="{esc(alt)}" src="data:image/jpeg;base64,{data}">'


def main():
    series = sys.argv[1] if len(sys.argv) > 1 else "S3"
    state = load(series)
    records = state["measurements"]
    steps = step_windows(state)
    unassigned = assign(steps, records)

    # 1. Записи во время прогонов оригинала - их быть не должно.
    orig_steps = [s for s in steps if s["версия"] == "ориг"]
    orig_records = sum(len(s["записи"]) for s in orig_steps)

    # 2. Сверка покрытия по шагам версии с замерами.
    cover_rows, total_checks, ok_checks, extra_keys = [], 0, 0, []
    for s in steps:
        if s["версия"] != "замеры":
            continue
        rows, extra = check_step(s)
        extra_keys += [(s["шаг"], k) for k in extra]
        proc, entry, data = SCENARIO_TEXT.get(s["шаг"], ("", s["шаг"], ""))
        for key, exp, fact, ok, problem in rows:
            total_checks += 1
            ok_checks += ok
            cover_rows.append((s["шаг"], proc, entry, key, exp, fact, ok, problem))
        if not rows:
            cover_rows.append((s["шаг"], proc, entry, "-", "записей нет: точка входа завершается ошибкой оригинала",
                               f"{len(s['записи'])} зап.", len(s["записи"]) == 0, ""))
            total_checks += 1
            ok_checks += len(s["записи"]) == 0

    # 3. Сравнение результата операций.
    oa, ob, order_diffs = compare_orders(state)
    sa = {norm_code(k): v for k, v in state["statuses"]["ориг"].items() if "_F" not in k}
    sb = {norm_code(k): v for k, v in state["statuses"]["замеры"].items() if "_F" not in k}
    status_diffs = [k for k in sorted(set(sa) | set(sb)) if sa.get(k) != sb.get(k)]
    la, lb, limit_doc_diff = compare_dict_rows(state["limits"]["ориг"]["установки"], state["limits"]["замеры"]["установки"],
                                               ["Портфель", "Класс"], "Лимитов")
    pa, pb, limit_prop_diff = compare_dict_rows(state["limits"]["ориг"]["сведения"], state["limits"]["замеры"]["сведения"],
                                                ["Портфель", "Свойство"], "Значение")
    na, nb, nt_diff = compare_dict_rows(state["nontrade"]["ориг"], state["nontrade"]["замеры"], ["Портфель", "Свойство"],
                                        "Значение")
    # Поручения, созданные обработками: сделки и неторговые поручения портфелей группы Н (ввод и вывод групп П, К, Б -
    # подготовка данных).
    made_by = {v: sum(1 for o in state["orders"][v] if "_F" not in o["Портфель"]
                      and (o["Вид"] == "Сделка" or "_N" in o["Портфель"])) for v in ("ориг", "замеры")}
    n_orders_a = sum(len(v) for v in oa.values())
    n_orders_b = sum(len(v) for v in ob.values())
    nt_orders = [o for o in state["orders"]["замеры"] if "_N" in o["Портфель"]]

    compare = [
        ("Поручения (торговые и неторговые) по портфелям, без портфелей проверки веб-клиента",
         f"оригинал {n_orders_a}, с замерами {n_orders_b}; портфелей {len(oa)}", not order_diffs,
         ", ".join(order_diffs) or "актив, количество, цена, сумма, проведение, пометка удаления, статус блоттера совпадают"),
        ("Статусы портфелей обработки торговых поручений", f"портфелей со статусом: {len(sa)} и {len(sb)}", not status_diffs,
         ", ".join(status_diffs) or "совпадают"),
        ("Установки лимитов новых клиентов (класс, проведение, число лимитов)",
         f"{sum(la.values())} и {sum(lb.values())}", not limit_doc_diff, str(dict(limit_doc_diff)) if limit_doc_diff else "совпадают"),
        ("Сведения распространения правил (дата автоустановки, эталон, признаки, внешний код)",
         f"{sum(pa.values())} и {sum(pb.values())}", not limit_prop_diff,
         str(dict(limit_prop_diff)) if limit_prop_diff else "совпадают (даты - по дню)"),
        ("Статусы и признаки неторговых (статус, дата, «позиция выгружена», «дата пересчета РСА»)",
         f"{sum(na.values())} и {sum(nb.values())}", not nt_diff, str(dict(nt_diff)) if nt_diff else "совпадают (даты - по дню)"),
    ]
    compare_ok = all(ok for _, _, ok, _ in compare)

    # Прогон с выключенными замерами (серия S4): записей нет, результат как у оригинала.
    off_path = os.path.join(HERE, "results", "stage4_S4.json")
    off = json.load(open(off_path, encoding="utf-8")).get("замеры_выключены") if os.path.exists(off_path) else None
    off_ok = bool(off) and off["записей"] == 0 and not off.get("ошибка") and off["сравнение"]["совпадает"]         and off["сравнение"]["статусы_совпадают"]
    if off:
        orders_off = "; ".join(f"{p}: {a} {q:g} шт. по {c:g}" for p, a, q, c, *_ in off["сравнение"]["замеры"])
        off_html = (f"<tr class='{'ok' if off_ok else 'bad'}'><td>Покупка, команда регламентного задания, версия 1.16, константа "
                    f"«Выполнять замеры производительности» выключена на время прогона</td><td>записей замеров: {off['записей']}; "
                    f"ошибка точки входа: {esc(off.get('ошибка') or 'нет')}</td><td>{'<b class=yes>совпадает</b>' if off['сравнение']['совпадает'] else '<b class=no>расхождение</b>'}"
                    f"</td><td>поручения и статусы портфелей как у оригинала на тех же данных ({esc(orders_off)})</td></tr>")
    else:
        off_html = "<tr class='bad'><td colspan=4>Прогон с выключенными замерами не найден</td></tr>"
    all_ok = compare_ok and off_ok and orig_records == 0 and ok_checks == total_checks and not unassigned and not extra_keys

    # Протокол.
    proto = []
    for run in state["runs"]:
        for st in run["шаги"]:
            if st.get("шаг") == "Данные":
                continue
            recs = next((len(s["записи"]) for s in steps if s["данные"] is st), "")
            err = (st.get("ошибка") or st.get("ошибка_задания") or "").strip().split("\n")[0]
            note = ""
            if st.get("потоки"):
                note = "потоков " + str(len(st["потоки"])) + ", поручений " + str(sum(t["поручений"] for t in st["потоки"]))
            if st.get("запись_версий_лимитов"):
                w = st["запись_версий_лимитов"]
                note = f"фоновое задание записи версий лимитов завершилось через {w['ожидание_с']:g} с"
            if st.get("поручений") not in (None, 0) and not note:
                note = f"поручений передано на отправку: {st['поручений']}"
            journal = [j for j in st.get("журнал") or [] if j["уровень"] != "Примечание"]
            if journal:
                note += ("; " if note else "") + "журнал: " + " | ".join(
                    (j["комментарий"] or j["событие"]).strip().split("\n")[0][:160] for j in journal)
            proto.append(f"<tr><td>{esc(run['версия'])}</td><td>{esc(st.get('шаг', ''))}</td>"
                         f"<td>{esc(st.get('сценарий', ''))}</td><td class='n'>{esc(st.get('длительность_с') or '')}</td>"
                         f"<td>{esc(err[:220])}</td><td class='n'>{esc(recs)}</td><td>{esc(note)}</td></tr>")

    cov_parts, prev_step = [], None
    for step, proc, entry, key, exp, fact, ok, problem in cover_rows:
        head = (esc(step), esc(proc), esc(entry)) if step != prev_step else ("", "", "")
        prev_step = step
        cov_parts.append(
            f"<tr class='{'ok' if ok else 'bad'}'><td>{head[0]}</td><td>{head[1]}</td><td>{head[2]}</td><td><code>{esc(key)}</code></td>"
            f"<td>{esc(exp)}</td><td>{esc(fact)}</td><td>{'<b class=yes>да</b>' if ok else '<b class=no>нет</b> ' + esc(problem)}</td></tr>")
    cov_html = "".join(cov_parts)
    cmp_html = "".join(f"<tr class='{'ok' if ok else 'bad'}'><td>{esc(a)}</td><td>{esc(b)}</td>"
                       f"<td>{'<b class=yes>совпадает</b>' if ok else '<b class=no>расхождение</b>'}</td><td>{esc(c)}</td></tr>"
                       for a, b, ok, c in compare)

    def comment_text(r):
        c = r["комментарий"] or ""
        return "" if c.startswith("{") else c
    raw = "".join(
        f"<tr data-k><td>{esc(start_local(r).strftime('%d.%m %H:%M:%S.%f')[:-3])}</td><td class='n'>{r['сеанс']}</td>"
        f"<td><code>{esc(short(r['ключ']))}</code></td><td class='n'>{r['время_с']:.3f}</td><td class='n'>{r['вес']:g}</td>"
        f"<td>{'да' if r['ошибка'] else ''}</td><td>{esc(comment_text(r))}</td></tr>"
        for r in sorted(records, key=lambda x: x["начало_мс"]))

    keys_by_proc = Counter()
    for r in records:
        keys_by_proc[r["ключ"].split(".")[0]] += 1
    durations = {s["шаг"]: max((r["время_с"] for r in s["записи"] if r["ключ"].count(".") == (1 if r["ключ"].startswith(ROST) else 0)
                                and "Удельный" not in r["ключ"]), default=None) for s in steps if s["версия"] == "замеры"}

    shot1 = img_tag(os.path.join(HERE, "results", "web_reinvest_threads_S3.jpg"), "Форма после потоков")
    shot2 = img_tag(os.path.join(HERE, "results", "web_reinvest_log_S3.jpg"), "Лог формы")
    shot0 = img_tag(os.path.join(HERE, "results", "web_reinvest_threads.jpg"), "Форма после потоков, первый прогон")

    page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тест замеров этапа 4</title>
<style>
:root {{ --bg:#f3f5f9; --card:#fff; --ink:#18212d; --muted:#5d6b7c; --line:#dbe2ea; --soft:#eef2f7; --head:#1d3557;
  --accent:#2a6fdb; --ok:#1f9d55; --ok-bg:#e9f7ef; --bad:#d64545; --bad-bg:#fdecec; --code:#eef2f7; --warn:#c98a04; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#0f141b; --card:#171e27; --ink:#e6ebf1;
  --muted:#9aa8b8; --line:#2a3542; --soft:#1d2631; --head:#22324a; --ok-bg:#14291e; --bad-bg:#2f1a1a; --code:#222c38; }} }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 "Segoe UI",Arial,sans-serif; }}
.wrap {{ max-width:1500px; margin:0 auto; padding:22px 24px 30px; }}
h1 {{ margin:0 0 6px; font-size:23px; }} h2 {{ margin:26px 0 10px; font-size:17px; }}
.lead {{ color:var(--muted); margin:0 0 6px; max-width:1150px; }}
.verdict {{ margin:16px 0; padding:12px 16px; border-radius:10px; font-weight:600; border:1px solid var(--line);
  background:{'var(--ok-bg)' if all_ok else 'var(--bad-bg)'}; color:{'var(--ok)' if all_ok else 'var(--bad)'}; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 16px; }}
.card b {{ display:block; font-size:26px; line-height:1.15; }} .card span {{ color:var(--muted); font-size:12.5px; }}
.box {{ background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:auto; }}
table {{ border-collapse:collapse; width:100%; }} th, td {{ padding:7px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:var(--head); color:#fff; font-weight:600; font-size:12.5px; position:sticky; top:0; }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
code {{ font-family:Consolas,monospace; font-size:12px; background:var(--code); padding:0 4px; border-radius:4px; }}
tr.ok td:first-child {{ box-shadow:inset 4px 0 var(--ok); }} tr.bad td:first-child {{ box-shadow:inset 4px 0 var(--bad); }}
b.yes {{ color:var(--ok); }} b.no {{ color:var(--bad); }}
.note {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--warn); border-radius:8px; padding:10px 14px; margin:8px 0; }}
.filter {{ margin:8px 0; padding:7px 10px; border:1px solid var(--line); border-radius:8px; width:min(480px,100%); background:var(--card); color:var(--ink); }}
.scroll {{ max-height:560px; overflow:auto; }} ul {{ margin:6px 0; }} small {{ color:var(--muted); }}
.shots {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:12px; }}
.shots figure {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:8px; }}
.shots img {{ width:100%; height:auto; border-radius:6px; }} figcaption {{ color:var(--muted); font-size:12.5px; margin-top:6px; }}
@media (max-width:700px) {{ .wrap {{ padding:16px; }} }}
</style></head><body><div class="wrap">
<h1>Тестирование замеров внешних обработок лимитов и поручений (IMDEV-9530, этап 4)</h1>
<h2 style="margin-top:14px">Обработки, в которые добавлены замеры</h2>
<div class="box"><table><tr><th>Внешняя обработка</th><th>Файл</th><th>Версия: оригинал -&gt; с замерами</th><th>Строка списка ключевых операций</th>
<th>Ключи замеров (общая запись и шаги)</th><th>Точки входа с замером</th></tr>
<tr><td>Создание торговых поручений РОСТ</td><td><code>внСозданиеТорговыхПорученийРОСТ.epf</code></td><td class="n">1.15 -&gt; 1.16</td><td class="n">5</td>
<td>Длительная операция БСП <code>{ROST}.Покупка</code>, <code>.Продажа</code>, <code>.Реинвестирование</code>,
<code>.ПродажаПодБлокировки</code>, <code>.ОтправкаПачки</code>; шаги <code>ОтборПортфелей</code>, <code>РасчетПотоковОФЗ</code>,
<code>ЗаписьПоручения</code>, <code>ЦенаИзСтакана</code>, <code>ЦенаЗакрытия</code>, <code>ПроведениеСЦеной</code>, <code>ПроведениеСуммы</code>,
<code>РасчетКоличестваОФЗ</code>, <code>ПроведениеКоличества</code>, <code>СтатусПортфеля</code>, <code>ПроверкаИОтправка</code>,
<code>Рассылка</code> / <code>Завершение</code></td>
<td>Команды регламентного задания покупки и продажи; вызовы формы: покупка, продажа, реинвестирование без потоков, отправка пачки;
фоновые потоки формы реинвестирования и продаж под блокировки (в форме - размер пакета для потоков)</td></tr>
<tr><td>Распространение правил с одного клиента на список клиентов</td><td><code>внРаспространениеПравилСОдногоКлиентаНаСписокКлиентов.epf</code></td>
<td class="n">1.15 -&gt; 1.16</td><td class="n">3</td>
<td><code>РаспространениеПравилЛимитов</code>; шаги по каждому классу лимитов <code>.ПоискНовыхКлиентов</code>,
<code>.СозданиеУстановок</code>, <code>.Рассылка</code></td>
<td><code>ВыполнитьРаспространениеПравилПослеОбмена</code> (вызывается обработкой «Операции после обмена»)</td></tr>
<tr><td>Загрузка неторговых поручений РОСТ</td><td><code>внЗагрузкаНеторговыхПорученийРОСТ.epf</code></td><td class="n">1.06 -&gt; 1.07</td><td class="n">13</td>
<td><code>ЗагрузкаНеторговыхПорученийРОСТ</code> (с признаком ошибки); шаги <code>.СозданиеПоручений</code>, <code>.Рассылка</code></td>
<td>Команда регламентного задания (<code>ВыполнитьКоманду</code>)</td></tr>
</table></div>
<p class="lead" style="margin-top:12px">Каждая вставка замера помечена комментарием, который начинается с <code>IMDEV-9530</code>; строки
оригинала не менялись. Разработческая база ФО (WIN_FO_server), серия тестовых данных {esc(series)}. Обработки сравнивались в двух
версиях на одинаковых наборах данных: оригинал и версия с замерами. Обе версии регистрировались в один элемент справочника дополнительных обработок; у каждой версии
свои тестовые портфели и свое свойство статуса, поэтому прогоны версий не видят данных друг друга. Точки входа вызывались так же, как в
работе: процедуры команд регламентного задания, серверные вызовы кнопок формы, процедуры фоновых потоков формы (фоновыми заданиями,
по одному на поток), вызов распространения правил из обработки «Операции после обмена», команда через
<code>ДополнительныеОтчетыИОбработки.ВыполнитьКоманду</code>. Кнопка формы торговых поручений дополнительно нажата в веб-клиенте.</p>
<div class="verdict">{'Все проверки пройдены: ' if all_ok else 'Есть непройденные проверки: '}покрытие {ok_checks}/{total_checks},
записей во время прогонов оригинала {orig_records}, результат операций оригинала и версии с замерами
{'совпадает' if compare_ok else 'расходится'}; при выключенных замерах записей нет, результат как у оригинала</div>
<div class="cards">
<div class="card"><b>{len(records)}</b><span>записей регистра «Замеры времени» за прогон серии</span></div>
<div class="card"><b>{len(set(r['ключ'] for r in records))}</b><span>ключей операций и шагов</span></div>
<div class="card"><b>{sum(1 for s in steps if s['версия'] == 'замеры')}</b><span>сценариев версии с замерами</span></div>
<div class="card"><b>{orig_records}</b><span>записей при прогонах оригинала (ожидается 0)</span></div>
<div class="card"><b>{made_by['замеры']}</b><span>поручений создано обработками в каждой версии ({made_by['ориг']} в оригинале), совпали</span></div>
<div class="card"><b>{sum(lb.values())}</b><span>установок лимитов новых клиентов, совпали</span></div>
</div>

<h2>Сверка покрытия: ожидаемые записи по каждому сценарию</h2>
<p class="lead">Для каждого сценария версии с замерами заранее рассчитаны ожидаемые ключи, веса и комментарии (портфели, поручения,
проведения - по составу тестовых данных). Записи отнесены к сценарию по дате начала замера. Вес общей записи длительной операции БСП -
сумма весов шагов, время шага - среднее на единицу веса, запись <code>.Удельный</code> - сумма времени шагов на единицу.</p>
<div class="box scroll"><table><tr><th>Сценарий</th><th>Обработка</th><th>Точка входа</th><th>Ключ</th><th>Ожидалось</th><th>Факт</th><th>Совпало</th></tr>{cov_html}</table></div>
{'<div class="note"><b>Лишние ключи:</b> ' + esc(extra_keys) + '</div>' if extra_keys else ''}
{'<div class="note"><b>Записи вне сценариев:</b> ' + str(len(unassigned)) + '</div>' if unassigned else ''}

<h2>Результат операций: оригинал и версия с замерами</h2>
<p class="lead">Сравнение по портфелям с одинаковыми номерами в наборах версий. Даты документов и время статусов не сравниваются.</p>
<div class="box"><table><tr><th>Что сравнивалось</th><th>Объем</th><th>Итог</th><th>Подробно</th></tr>{cmp_html}</table></div>

<h2>Замеры выключены</h2>
<p class="lead">Отдельная серия S4 (07.10.2026): команда покупки версии 1.16 при выключенной константе - описание длительной операции
не создается, фиксации шагов и запись замера сразу выходят. Для сравнения на тех же данных в тот же день выполнена версия 1.15;
константа после прогона возвращена.</p>
<div class="box"><table><tr><th>Прогон</th><th>Факт</th><th>Итог</th><th>Подробно</th></tr>{off_html}</table></div>

<h2>Протокол прогонов</h2>
<div class="box scroll"><table><tr><th>Версия</th><th>Шаг</th><th>Сценарий</th><th>Длительность, с</th><th>Ошибка точки входа</th><th>Записей замеров</th><th>Примечание</th></tr>{''.join(proto)}</table></div>

<h2>Что показал тест</h2>
<div class="note"><b>Реинвестирование без потоков (кнопка формы «Создать и отправить ордера») в оригинале завершается ошибкой.</b>
<code>РеинвестСоздатьИОтправитьОрдера</code> передает в <code>РеинвестСоздатьОрдера</code> адрес <code>Неопределено</code>; процедура
помещает ответ во временное хранилище, но новый адрес не возвращает, и <code>ПолучитьИзВременногоХранилища(Неопределено)</code>
вызывает исключение. Поручения созданы и статусы портфелей изменены, отправка не выполняется. В версии с замерами поведение то же, общая
запись <code>РОСТ.Реинвестирование</code> с запуском «форма» не пишется: операция прерывается до записи замера. Бизнес-код по
инварианту не менялся; исправление - в IMDEV-9531.</div>
<div class="note"><b>Потоки формы могут не вернуть ответ форме.</b> Форма создает адрес ответа потока через
<code>ПоместитьВоВременноеХранилище(Неопределено)</code> без идентификатора формы. В первом нажатии кнопки в веб-клиенте ответы потоков
получены («Создание и отправка поручений на реинвестирование купона завершено!»), во втором - на закладке «Лог» по каждому потоку
«Ошибка получения результат из: e1cib/tempstorage/...», и отправка пачки из формы не вызывается. Сами потоки завершились, их замеры
записаны полностью. Код получения ответа и создания адреса не менялся (в модуле формы добавлен только подсчет
<code>ПортфелейВПакете</code>); передать в IMDEV-9531.</div>
<div class="note"><b>Неторговые поручения: ошибка вызова сервиса попадает в лог с текстом «Ошибка рассылки отчета по почте».</b>
Исключение вызова <code>GetAgreementAmount</code> перехватывает общая конструкция Попытка вокруг создания поручений и рассылки. Замер в
этом случае пишется общей записью с признаком ошибки, шаги не пишутся.</div>
<div class="note"><b>Путь регламентного задания без тестового режима</b> (команда через БСП): на dev нет адаптера биржи, запрос цены из
стакана не возвращает цену, поручение помечается на удаление, транзакция портфеля отменяется. Замер пишется: шаги записи поручения и
запроса цены видны, «Поручений: 0», «Проведений: 2». То же у кнопки в веб-клиенте: «Поручений: 0; Проведений: 1» в каждом потоке.</div>
<div class="note"><b>Размер пакета потоков.</b> В записях потоков «Портфелей в пакете» - число портфелей, распределенных по потокам в этом
нажатии (6 в сценариях формы, 3 в веб-клиенте), «Портфелей» - портфели самого потока. Сумма времени потоков больше длительности пакета:
потоки идут параллельно.</div>

<h2>Проверка кнопки формы в веб-клиенте</h2>
<p class="lead">Форма обработки версии 1.16 открыта командой карточки дополнительной обработки, закладка «Реинвестирование»: дата купона,
«Обновить список портфелей», отметить все, «Создать поручения в потоке». Модуль формы скомпилирован и выполнен в веб-клиенте, три
фоновых потока записали замеры с «Портфелей в пакете: 3». Сеанс завершен командой «Файл - Выход».</p>
<div class="shots"><figure>{shot1}<figcaption>Форма после потоков (серия {esc(series)})</figcaption></figure>
<figure>{shot2}<figcaption>Закладка «Лог»: форма не получила ответы потоков</figcaption></figure>
<figure>{shot0}<figcaption>Первое нажатие (серия S2): ответы получены, сообщения о завершении</figcaption></figure></div>

<h2>Тестовые данные и изменения разработческой базы</h2>
<ul>
<li>Портфели «T9530R &lt;серия&gt; &lt;версия&gt; &lt;группа&gt;NN» с субпортфелями (стратегия «T9530R РОСТ», место хранения
«T9530R Брокерский счет» вида «брокерский счет»), группы: П - покупка, К - покупка через БСП, С - продажа, Р - реинвестирование,
Б - продажи под блокировки, Ф - веб-клиент, Л - распространение правил, Н - неторговые; эталонный портфель серии.</li>
<li>Свойства «T9530R Статус портфеля (ориг/замеры)», «T9530R Дата статуса ...», «T9530R Статус неторговых (ориг/замеры)», свойства
распространения правил по классам, «T9530R Позиция выгружена», «T9530R Дата пересчета РСА»; тип клиента «T9530R Розничный ДУ».</li>
<li>Облигация и актив «T9530R ОФЗ» (копия облигации стенда) с купонным расписанием; неторговые поручения ввода и вывода, фактическая
позиция, установки лимитов эталона - тестовая обработка «T9530 тест обработок РОСТ (IMDEV-9530)», зарегистрирована в справочнике.</li>
<li>Константа «Использовать классы лимитов» на время шага распространения правил включалась (на dev выключена, без нее вторая
установка лимитов портфеля запрещена к проведению) и возвращена в исходное значение.</li>
<li>Неторговые поручения обращаются к веб-сервису 1С:ДО: на время теста использовалась локальная заглушка сервиса
(<code>mock_dm_service.py</code>), ответы по номерам договоров тестовых портфелей.</li>
<li>Константа «Выполнять замеры производительности» выключалась на один прогон серии S4 и возвращена.</li>
<li>Серии S1 (отладка) и S2 закрыты: их портфелям поставлены конечные статусы, не входящие в отборы обработок. Серия S2 повторена как
S3, потому что портфели отладочной серии попадали в отборы S2 и искажали счетчики. После сбора результатов серии S3 и S4 тоже закрыты.</li>
<li>Элементы справочника дополнительных обработок «Создание торговых поручений РОСТ», «Распространение правил ...», «Загрузка
неторговых поручений РОСТ» оставлены в версии с замерами и тестовыми настройками.</li>
</ul>

<h2>Все записи регистра</h2>
<input class="filter" id="f" type="search" placeholder="Фильтр по ключу или комментарию...">
<div class="box scroll"><table id="raw"><tr><th>Начало замера</th><th>Сеанс</th><th>Ключ</th><th>Время, с</th><th>Вес</th><th>Ошибка</th><th>Комментарий</th></tr>{raw}</table></div>
<p class="lead">Источник: Тестирование\\Стенд_замеры\\results\\stage4_{esc(series)}.json (run_stage4_tests.py collect);
<code>РОСТ.</code> - сокращение <code>{ROST}.</code>; время начала - местное время сервера ФО.</p>
</div>
<script>
document.getElementById("f").addEventListener("input", function () {{
  var q = this.value.toLowerCase();
  document.querySelectorAll("#raw tr[data-k]").forEach(function (tr) {{
    tr.style.display = !q || tr.textContent.toLowerCase().indexOf(q) !== -1 ? "" : "none"; }});
}});
</script></body></html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(OUT)
    print(f"покрытие {ok_checks}/{total_checks}, записей при оригинале {orig_records}, вне сценариев {len(unassigned)}, "
          f"лишних ключей {len(extra_keys)}, сравнение {'ок' if compare_ok else 'РАСХОЖДЕНИЕ'}")
    for c in compare:
        print("  ", c[0][:60], c[2], c[3][:200])
    for row in cover_rows:
        if not row[6]:
            print("  НЕ СОВПАЛО:", row[0], row[3], row[4], "|", row[5], "|", row[7])
    if extra_keys:
        print("  лишние ключи:", extra_keys)


if __name__ == "__main__":
    main()
