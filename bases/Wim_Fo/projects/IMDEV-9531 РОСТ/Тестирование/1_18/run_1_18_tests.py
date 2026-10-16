# -*- coding: utf-8 -*-
"""Регресс и скорость 1.16 против 1.18 на dev ФО (WIN_FO_server), выборка T9531PROP в пропорциях ПРОД.

Для каждой версии и каждого режима задержки:
  1. тестовая обработка T9530_ТестРОСТ 1.7 (уже зарегистрирована в базе, не перерегистрируется):
     ОчиститьСделки, ПропорцииПрод, ПозицияНаВчера - одинаковое исходное состояние;
  2. регистрация тестовой сборки обработки РОСТ (сборки/<версия>-тест) с настройками из базы;
  3. сценарии Покупка.Команда (20 портфелей), Продажа.Команда (50 портфелей, 100 строк),
     Реинвест.Потоки (пакет 200 из 6694 в 10 потоках), тестовая цена из котировок;
  4. снимок поручений и статусов портфелей, замеры РОСТ, число обращений к заглушке стакана.

Заглушка стакана stakan_mock.py (порт 18541) должна быть запущена. Задержка 1 с - время ответа адаптера на ПРОД.

    python run_1_18_tests.py            режимы 1.0 и 0
    python run_1_18_tests.py 1.0        только задержка 1 с
"""
import datetime
import json
import os
import sys
import traceback
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
STAND = os.path.join(os.path.dirname(TASK), "IMDEV-9530  Замеры ФО", "Тестирование", "Стенд_замеры")
sys.path.insert(0, STAND)
import run_stage4_tests as stage4  # noqa: E402

BUILDS = {
    "1.16": os.path.join(HERE, "сборки", "1.16-тест", "внСозданиеТорговыхПорученийРОСТ.epf"),
    "1.18": os.path.join(HERE, "сборки", "1.18-тест", "внСозданиеТорговыхПорученийРОСТ.epf"),
}
SCENARIOS = ["Покупка.Команда", "Продажа.Команда", "Реинвест.Потоки"]
MOCK = "http://127.0.0.1:18541"
REPORTS = os.path.join(HERE, "reports")


def mock(path):
    with urllib.request.urlopen(MOCK + path, timeout=10) as response:
        return response.read().decode()


def mock_count():
    return json.loads(mock("/stats"))["wait"]


def harness_ref(fo):
    ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": stage4.TEST_OBJECT},
    )
    version = fo.String(ref.Версия)
    if version != "1.7":
        raise RuntimeError("в базе тестовая обработка версии " + version + ", нужна 1.7 (сценарии T9531PROP)")
    return ref


def service(fo, test_ref, name, title):
    params = fo.NewObject("Структура")
    params.Вставить("Сценарий", name)
    out = stage4.run_harness(fo, test_ref, params, title, timeout=7200)
    return {"шаг": name, "состояние": out.get("состояние"), "длительность_с": out.get("длительность_с"),
            "ошибка": out.get("ошибка") or out.get("ошибка_задания") or "", "лог": (out.get("лог") or "")[-300:]}


def today_start(fo):
    now = datetime.datetime.now()
    return stage4.date_1c(fo, datetime.datetime(now.year, now.month, now.day))


def orders(fo):
    rows = stage4.query(fo, """
        ВЫБРАТЬ
            П.Портфель.ВнешнийКод КАК Код,
            П.Актив.Наименование КАК Актив,
            ПРЕДСТАВЛЕНИЕ(П.Направление) КАК Направление,
            П.Количество КАК Количество,
            П.ЦенаВВалютеРасчетов КАК Цена,
            П.Котировка КАК Котировка,
            П.СуммаПоручения КАК Сумма,
            П.Проведен КАК Проведен,
            П.ПометкаУдаления КАК Удален
        ИЗ
            Документ.Поручение КАК П
        ГДЕ
            П.Портфель.ВнешнийКод ПОДОБНО "T9531PROP%"
            И П.Дата >= &Начало
            И П.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.Сделка)""", {"Начало": today_start(fo)})
    grouped = {}
    for row in rows:
        key = "|".join([fo.String(row["Код"]), fo.String(row["Актив"]), fo.String(row["Направление"])])
        grouped.setdefault(key, []).append([
            round(float(row["Количество"]), 4), round(float(row["Цена"]), 4), round(float(row["Котировка"]), 4),
            round(float(row["Сумма"]), 4), bool(row["Проведен"]), bool(row["Удален"])])
    for docs in grouped.values():
        docs.sort()
    return grouped


def statuses(fo):
    """Статусы портфелей T9531PROP: группа портфеля, свойство статуса, значение, число портфелей."""
    rows = stage4.query(fo, """
        ВЫБРАТЬ
            ПОДСТРОКА(Портфели.ВнешнийКод, 1, 11) КАК Группа,
            ПРЕДСТАВЛЕНИЕ(Сведения.Свойство) КАК Свойство,
            ПРЕДСТАВЛЕНИЕ(Сведения.Значение) КАК Статус,
            КОЛИЧЕСТВО(*) КАК Количество
        ИЗ
            РегистрСведений.ДополнительныеСведения КАК Сведения
                ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Портфели КАК Портфели
                ПО Сведения.Объект = Портфели.Ссылка
        ГДЕ
            Портфели.ВнешнийКод ПОДОБНО "T9531PROP%"
            И Сведения.Значение ССЫЛКА Справочник.ЗначенияСвойствОбъектов
        СГРУППИРОВАТЬ ПО
            ПОДСТРОКА(Портфели.ВнешнийКод, 1, 11),
            ПРЕДСТАВЛЕНИЕ(Сведения.Свойство),
            ПРЕДСТАВЛЕНИЕ(Сведения.Значение)""")
    return {"|".join([fo.String(r["Группа"]), fo.String(r["Свойство"]), fo.String(r["Статус"])]): int(r["Количество"])
            for r in rows}


def run_version(label, path, delay):
    fo = stage4.connect("wim_fo")
    test_ref = harness_ref(fo)
    prepare = [service(fo, test_ref, name, name + " " + label)
               for name in ("ОчиститьСделки", "ПропорцииПрод", "ПозицияНаВчера")]
    rost_ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": stage4.ROST_OBJECT},
    )
    settings = rost_ref.ПолучитьОбъект().ХранилищеНастроек.Получить()
    rost_ref = stage4.register_epf(fo, stage4.ROST_OBJECT, path, settings)
    started = stage4.now_iso(fo)
    steps = []
    for name in SCENARIOS:
        mock("/reset")
        try:
            extra = {"ЗадержкаСтакана": delay} if delay else None
            params = stage4.rost_params(fo, name, rost_ref, test_ref, "замеры", extra)
            out = stage4.run_harness(fo, test_ref, params, name + " " + label, timeout=7200)
            threads = out.get("потоки") or []
            steps.append({
                "шаг": name,
                "длительность_с": out.get("длительность_с"),
                "состояние": out.get("состояние"),
                "ошибка": out.get("ошибка") or out.get("ошибка_задания") or "",
                "поручений_на_отправку": out.get("поручений") or len(out.get("документы") or []),
                "запросов_стакана": mock_count(),
                "потоков": len(threads),
                "ошибки_потоков": [t["ошибка"] for t in threads if t.get("ошибка")],
            })
        except Exception:
            steps.append({"шаг": name, "ошибка": traceback.format_exc()[-1500:]})
        stage4.log("done", label, delay, steps[-1])
    fo = stage4.connect("wim_fo")
    return {
        "версия": label,
        "задержка_с": delay,
        "подготовка": prepare,
        "шаги": steps,
        "поручения": orders(fo),
        "статусы": statuses(fo),
        "замеры": stage4.measurements(fo, started),
    }


def compare(old, new):
    keys_old, keys_new = set(old), set(new)
    diffs = [{"ключ": k, "1.16": old[k], "1.18": new[k]} for k in sorted(keys_old & keys_new) if old[k] != new[k]]
    return {
        "ключей_1_16": len(keys_old),
        "ключей_1_18": len(keys_new),
        "поручений_1_16": sum(len(v) for v in old.values()),
        "поручений_1_18": sum(len(v) for v in new.values()),
        "совпало": len(keys_old & keys_new) - len(diffs),
        "расхождения": diffs,
        "только_1_16": sorted(keys_old - keys_new),
        "только_1_18": sorted(keys_new - keys_old),
    }


def main():
    delays = [float(a) for a in sys.argv[1:]] or [1.0, 0.0]
    os.makedirs(REPORTS, exist_ok=True)
    mock("/stats")
    for delay in delays:
        out_path = os.path.join(REPORTS, "run_delay_%s.json" % str(delay).replace(".", "_"))
        report = {"задержка_с": delay, "дата": datetime.datetime.now().isoformat(timespec="seconds"), "версии": []}
        if os.path.exists(out_path):
            report = json.load(open(out_path, encoding="utf-8"))
        done = {item["версия"] for item in report["версии"]}
        for label, path in BUILDS.items():
            if label in done:
                stage4.log("уже есть", label, delay)
                continue
            report["версии"].append(run_version(label, path, delay))
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
        old, new = report["версии"]
        report["сверка_поручений"] = compare(old["поручения"], new["поручения"])
        report["сверка_статусов"] = {"1.16": old["статусы"], "1.18": new["статусы"],
                                     "совпадают": old["статусы"] == new["статусы"]}
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
        check = report["сверка_поручений"]
        stage4.log("compare delay", delay, "same", check["совпало"], "diff", len(check["расхождения"]),
                   "only16", len(check["только_1_16"]), "only18", len(check["только_1_18"]),
                   "statuses", report["сверка_статусов"]["совпадают"])


if __name__ == "__main__":
    main()
