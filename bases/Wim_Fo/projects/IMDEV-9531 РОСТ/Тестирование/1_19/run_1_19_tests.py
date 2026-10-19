# -*- coding: utf-8 -*-
"""Регресс и скорость 1.19 (срок кеша цены стакана в настройках) против 1.16 на dev ФО, стакан 1 с.

Варианты, каждый на одинаковом исходном состоянии (ОчиститьСделки, ПропорцииПрод, ПозицияНаВчера):
  1.16       - тестовая сборка 1.16, базовая линия;
  1.19 / 0   - настройка 0: кеш выключен, ожидается поведение 1.16 и столько же запросов стакана;
  1.19 / 60  - настройка 60: кеш включен, ожидается поведение 1.18.
Затем проверка ограничения: настройка 500, только реинвестирование после ОчиститьСделки, в логе потоков ожидается
"Кеш цены стакана: 300 с".

Срок кеша записывается в настройки элемента справочника дополнительных обработок перед регистрацией сборки.
Заглушка стакана stakan_mock.py (порт 18541) должна быть запущена.
"""
import datetime
import json
import os
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")
import os as _os
# Общий стенд IMDEV-9531 (заглушка стакана, тестовые сборки, функции прогона) - в каталоге Тестирование/1_18
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "1_18"))
import run_1_18_tests as base  # noqa: E402

stage4 = base.stage4
BUILD_DIR = os.path.join(base.HERE, "сборки")
VARIANTS = [
    ("1.16", os.path.join(BUILD_DIR, "1.16-тест", "внСозданиеТорговыхПорученийРОСТ.epf"), None),
    ("1.19 / 0", os.path.join(BUILD_DIR, "1.19-тест", "внСозданиеТорговыхПорученийРОСТ.epf"), 0),
    ("1.19 / 60", os.path.join(BUILD_DIR, "1.19-тест", "внСозданиеТорговыхПорученийРОСТ.epf"), 60),
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "run_1_19.json")
# Дата выплаты купона тестовой облигации T9530R ОФЗ в купонном расписании dev: реинвестирование отбирает
# портфели с купоном на эту дату (сценарий обвязки по умолчанию подставляет сегодня).
COUPON_DATE = datetime.datetime(2026, 10, 16)


def register(fo, path, seconds):
    rost_ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": stage4.ROST_OBJECT},
    )
    settings = rost_ref.ПолучитьОбъект().ХранилищеНастроек.Получить()
    if seconds is not None:
        settings.Вставить("СрокКешаЦеныСтаканаСек", seconds)
    return stage4.register_epf(fo, stage4.ROST_OBJECT, path, settings)


def cache_lines(text):
    return sorted({line.strip() for line in (text or "").splitlines() if "Кеш цены стакана" in line})


def run_scenarios(fo, label, rost_ref, test_ref, scenarios):
    steps = []
    for name in scenarios:
        base.mock("/reset")
        try:
            extra = {"ЗадержкаСтакана": 1.0, "ДатаКупона": stage4.date_1c(fo, COUPON_DATE)}
            params = stage4.rost_params(fo, name, rost_ref, test_ref, "замеры", extra)
            out = stage4.run_harness(fo, test_ref, params, name + " " + label, timeout=7200)
            threads = out.get("потоки") or []
            logs = [out.get("лог") or ""] + [t.get("лог") or "" for t in threads]
            steps.append({
                "шаг": name,
                "длительность_с": out.get("длительность_с"),
                "ошибка": out.get("ошибка") or out.get("ошибка_задания") or "",
                "запросов_стакана": base.mock_count(),
                "потоков": len(threads),
                "ошибки_потоков": [t["ошибка"][:300] for t in threads if t.get("ошибка")],
                "режим_кеша_в_логе": cache_lines("\n".join(logs)),
            })
        except Exception:
            steps.append({"шаг": name, "ошибка": traceback.format_exc()[-1500:]})
        stage4.log("done", label, json.dumps(steps[-1], ensure_ascii=False))
    return steps


def run_variant(label, path, seconds):
    fo = stage4.connect("wim_fo")
    test_ref = base.harness_ref(fo)
    prepare = [base.service(fo, test_ref, name, name + " " + label)
               for name in ("ОчиститьСделки", "ПропорцииПрод", "ПозицияНаВчера")]
    rost_ref = register(fo, path, seconds)
    started = stage4.now_iso(fo)
    steps = run_scenarios(fo, label, rost_ref, test_ref, base.SCENARIOS)
    fo = stage4.connect("wim_fo")
    return {
        "вариант": label,
        "срок_кеша": seconds,
        "подготовка": prepare,
        "шаги": steps,
        "поручения": base.orders(fo),
        "статусы": base.statuses(fo),
        "замеры": stage4.measurements(fo, started),
    }


def clamp_check(path):
    fo = stage4.connect("wim_fo")
    test_ref = base.harness_ref(fo)
    cleared = base.service(fo, test_ref, "ОчиститьСделки", "очистка 1.19 / 500")
    rost_ref = register(fo, path, 500)
    started = stage4.now_iso(fo)
    steps = run_scenarios(fo, "1.19 / 500", rost_ref, test_ref, ["Реинвест.Потоки"])
    fo = stage4.connect("wim_fo")
    comments = sorted({m["комментарий"] for m in stage4.measurements(fo, started)
                       if m["ключ"] == "СозданиеТорговыхПорученийРОСТ.Реинвестирование"})
    return {"очистка": cleared, "шаги": steps, "комментарии_замера": comments}


def main():
    base.mock("/stats")
    report = {"дата": datetime.datetime.now().isoformat(timespec="seconds"), "варианты": []}
    if os.path.exists(OUT):
        report = json.load(open(OUT, encoding="utf-8"))
    done = {item["вариант"] for item in report["варианты"]}
    for label, path, seconds in VARIANTS:
        if label in done:
            continue
        report["варианты"].append(run_variant(label, path, seconds))
        with open(OUT, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    by_label = {item["вариант"]: item for item in report["варианты"]}
    old = by_label["1.16"]
    report["сверки"] = {}
    for label in ("1.19 / 0", "1.19 / 60"):
        new = by_label[label]
        report["сверки"][label] = {
            "поручения": base.compare(old["поручения"], new["поручения"]),
            "статусы_совпадают": old["статусы"] == new["статусы"],
        }
    if "ограничение_500" not in report:
        report["ограничение_500"] = clamp_check(VARIANTS[1][1])
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    for label, check in report["сверки"].items():
        c = check["поручения"]
        stage4.log("compare", label, "same", c["совпало"], "diff", len(c["расхождения"]), "only16",
                   len(c["только_1_16"]), "only_new", len(c["только_1_18"]), "statuses", check["статусы_совпадают"])
    stage4.log("clamp", json.dumps(report["ограничение_500"]["шаги"], ensure_ascii=False),
               report["ограничение_500"]["комментарии_замера"][:2])
    stage4.log("DONE", OUT)


if __name__ == "__main__":
    main()
