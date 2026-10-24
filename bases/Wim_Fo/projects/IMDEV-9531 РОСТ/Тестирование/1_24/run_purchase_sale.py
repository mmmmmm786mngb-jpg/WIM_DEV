#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Покупка и продажа РОСТ: 1.16-т1 и 1.24-т1 подряд на выборке T9531PROP.

Команда задания - ВыполнитьКоманду, как регламентное задание.
Путь формы - те же серверные процедуры, что у кнопок "Создать отправить поручения покупка"
и "Создать поручения (продажа)".

Между прогонами удаляются сегодняшние сделки выборки и возвращаются статусы
20 портфелей покупки и 50 портфелей продажи. Полная подготовка 6694 портфелей
реинвестирования не повторяется.

    python run_purchase_sale.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "1_18"))
import run_1_18_tests as base  # noqa: E402

stage4 = base.stage4
T1 = os.path.join(TASK, "Т-1")
BUILDS = {
    "1.16": os.path.join(T1, "РОСТ_1.16-т1.epf"),
    "1.24": os.path.join(T1, "РОСТ_1.24-т1.epf"),
}
REPORTS = os.path.join(HERE, "reports")
OUT = os.path.join(REPORTS, "purchase_sale.json")
PLAN = (
    ("1.16", "команда", ("Покупка.Команда", "Продажа.Команда", "Продажа.Повтор")),
    ("1.24", "команда", ("Покупка.Команда", "Продажа.Команда", "Продажа.Повтор")),
    ("1.16", "форма", ("Покупка.Форма", "Продажа.Форма")),
    ("1.24", "форма", ("Покупка.Форма", "Продажа.Форма")),
)


def text(fo, value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return "" if value is None else str(value)
    return fo.String(value)


def rost_ref(fo):
    return stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": stage4.ROST_OBJECT},
    )


def settings_of(fo):
    return rost_ref(fo).ХранилищеНастроек.Получить()


def portfolio_refs(fo, mask):
    rows = stage4.query(
        fo,
        "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
        "ГДЕ П.ВнешнийКод ПОДОБНО &Маска И НЕ П.ПометкаУдаления",
        {"Маска": mask},
    )
    return [row["Ссылка"] for row in rows]


def subset(orders, prefix):
    return {key: value for key, value in orders.items() if key.startswith(prefix)}


def order_count(orders):
    return sum(len(docs) for docs in orders.values())


def statuses(fo, mask):
    prop = settings_of(fo).ДопРеквизитСтатусПортфеля
    rows = stage4.query(
        fo,
        """ВЫБРАТЬ
            ПРЕДСТАВЛЕНИЕ(С.Значение) КАК Статус,
            КОЛИЧЕСТВО(*) КАК Количество
        ИЗ
            РегистрСведений.ДополнительныеСведения КАК С
                ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Портфели КАК П
                ПО С.Объект = П.Ссылка
        ГДЕ
            П.ВнешнийКод ПОДОБНО &Маска
            И С.Свойство = &Свойство
        СГРУППИРОВАТЬ ПО
            ПРЕДСТАВЛЕНИЕ(С.Значение)""",
        {"Маска": mask, "Свойство": prop},
    )
    return {text(fo, row["Статус"]): int(row["Количество"]) for row in rows}


def snapshot(fo):
    orders = base.orders(fo)
    return {
        "покупка": subset(orders, "T9531PROP_P"),
        "продажа": subset(orders, "T9531PROP_S"),
        "поручений_покупки": order_count(subset(orders, "T9531PROP_P")),
        "поручений_продажи": order_count(subset(orders, "T9531PROP_S")),
        "статусы_покупки": statuses(fo, "T9531PROP_P%"),
        "статусы_продажи": statuses(fo, "T9531PROP_S%"),
    }


def fast_reset(fo, test_ref):
    """Сделки выборки за сегодня и статусы покупки/продажи. Позиции не переписываются."""
    cleared = base.service(fo, test_ref, "ОчиститьСделки", "очистка сделок")
    storage = settings_of(fo)
    stage4.set_statuses(
        fo, test_ref, portfolio_refs(fo, "T9531PROP_P%"),
        storage.ДопРеквизитСтатусПортфеля, storage.ДопРеквизитДатаОперации,
        storage.СтатусДляПоиска, "статус покупки",
    )
    stage4.set_statuses(
        fo, test_ref, portfolio_refs(fo, "T9531PROP_S%"),
        storage.ДопРеквизитСтатусПортфеля, storage.ДопРеквизитДатаОперации,
        storage.СтатусРасторжениеИнициировано, "статус продажи",
    )
    state = snapshot(fo)
    stage4.log("reset", "deals left", state["поручений_покупки"] + state["поручений_продажи"],
               "buy", state["статусы_покупки"], "sell", state["статусы_продажи"],
               "clear", cleared.get("состояние"), cleared.get("длительность_с"))
    if state["поручений_покупки"] or state["поручений_продажи"]:
        raise RuntimeError("после очистки остались сделки выборки")
    if state["статусы_покупки"] != {"Поиск ДС": 20} or state["статусы_продажи"] != {"Расторжение инициировано": 50}:
        raise RuntimeError("статусы покупки или продажи не вернулись в исходные")
    return cleared


def run_step(fo, rost, test_ref, scenario, title):
    name = "Продажа.Команда" if scenario == "Продажа.Повтор" else scenario
    params = stage4.rost_params(fo, name, rost, test_ref, "замеры")
    out = stage4.run_harness(fo, test_ref, params, title, timeout=1800)
    step = {
        "шаг": scenario,
        "длительность_с": out.get("длительность_с"),
        "состояние": out.get("состояние"),
        "ошибка": (out.get("ошибка") or out.get("ошибка_задания") or "")[:500],
        "важность": out.get("важность"),
        "лог": (out.get("лог") or "")[-400:],
    }
    stage4.log("step", title, step["длительность_с"], step["состояние"], (step["ошибка"] or "")[:180])
    return step


def ensure_build(fo, version):
    """Ссылка на сборку нужной версии. Повторная регистрация не нужна, если она уже стоит."""
    ref = rost_ref(fo)
    expected = version + "-т1"
    if text(fo, ref.Версия) != expected:
        ref = stage4.register_epf(fo, stage4.ROST_OBJECT, BUILDS[version], settings_of(fo))
        stage4.log("registered", version, text(fo, ref.Версия))
    return ref


def run_variant(version, kind, scenarios, reset, done_steps=None, checkpoint=None):
    done_steps = list(done_steps or [])
    fo = stage4.connect("wim_fo")
    test_ref = base.harness_ref(fo)
    if reset:
        fast_reset(fo, test_ref)
    ensure_build(fo, version)
    steps = done_steps
    after = []
    for scenario in scenarios:
        if any(step["шаг"] == scenario for step in steps):
            stage4.log("skip step", version, kind, scenario)
            continue
        # Ссылки берутся из нового соединения: объект прошлого соединения не сериализуется в задание.
        fo = stage4.connect("wim_fo")
        test_ref = base.harness_ref(fo)
        rost = ensure_build(fo, version)
        steps.append(run_step(fo, rost, test_ref, scenario, "%s %s %s" % (version, kind, scenario)))
        fo = stage4.connect("wim_fo")
        after.append({"шаг": scenario, **snapshot(fo)})
        stage4.log("orders", scenario, "buy", after[-1]["поручений_покупки"], "sell", after[-1]["поручений_продажи"])
        if checkpoint:
            checkpoint(steps, after)
    if not after:
        fo = stage4.connect("wim_fo")
        after.append({"шаг": steps[-1]["шаг"], **snapshot(fo)})
    return {
        "версия": version,
        "путь": kind,
        "сборка": version + "-т1",
        "шаги": steps,
        "после_шагов": after,
        "итог": after[-1],
    }


def load():
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as handle:
            return json.load(handle)
    return {"прогоны": []}


def save(report):
    os.makedirs(REPORTS, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str)


def main():
    report = load()
    by_key = {(item["версия"], item["путь"]): item for item in report["прогоны"]}
    first = not report["прогоны"]
    for version, kind, scenarios in PLAN:
        existing = by_key.get((version, kind))
        if existing and existing.get("готово"):
            stage4.log("skip", version, kind)
            continue
        done_steps = existing["шаги"] if existing else []
        # Первый прогон садится на уже подготовленные данные. Дальше - быстрый сброс.
        # Незавершенный прогон продолжается без сброса: часть поручений уже создана.
        def checkpoint(steps, after):
            existing_item = by_key.get((version, kind))
            payload = {
                "версия": version, "путь": kind, "сборка": version + "-т1", "готово": False,
                "шаги": steps, "после_шагов": after, "итог": after[-1] if after else {},
            }
            if existing_item:
                existing_item.update(payload)
            else:
                report["прогоны"].append(payload)
                by_key[(version, kind)] = payload
            save(report)

        item = run_variant(
            version, kind, scenarios, reset=not first and not done_steps,
            done_steps=done_steps, checkpoint=checkpoint,
        )
        first = False
        item["готово"] = True
        current = by_key.get((version, kind))
        if current:
            current.update(item)
        else:
            report["прогоны"].append(item)
            by_key[(version, kind)] = item
        save(report)
    stage4.log("DONE", OUT)


if __name__ == "__main__":
    main()
