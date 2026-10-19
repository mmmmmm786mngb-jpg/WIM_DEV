# -*- coding: utf-8 -*-
"""Проверка истечения срока цены в кеше внутри одного запуска (1.19), dev ФО, стакан 1 с.

Срок кеша 3 с - меньше длительности прогонов: покупка 20 поручений одной облигации (~9 с), продажа 100 поручений по
двум бумагам (~30 с), реинвестирование 10 потоков по 20 поручений (у каждого потока свой кеш). Заглушка стакана
(stakan_mock.py, порт 18541) пишет время начала и конца каждого запроса, бумагу и номер сеанса (тестовая сборка
1.19-тест передает их в адресе запроса).

Для каждой пары "сеанс + бумага" запросы сортируются по времени; пауза между концом запроса и началом следующего -
это время жизни цены в кеше. Ожидается:
  - пауза не меньше срока (цена не запрашивается повторно, пока она действует);
  - пауза не больше срока плюс длительность одного поручения (устаревшая цена не используется);
  - запросов больше одного на пару (срок действительно истекает внутри запуска).
Поручения и статусы сверяются с эталоном 1.16 из reports/run_1_19.json (то же исходное состояние, тот же день).
"""
import datetime
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_1_19_tests as t19  # noqa: E402

base = t19.base
stage4 = t19.stage4
TTL = 3
EPF = os.path.join(t19.BUILD_DIR, "1.19-тест", "внСозданиеТорговыхПорученийРОСТ.epf")
OUT = os.path.join(HERE, "reports", "ttl_check.json")
# Допуск сверху: пауза может быть больше срока на время обработки одного поручения (запись, проведения) после того,
# как цена устарела. На dev одно поручение - до 0,7 с в потоках; берем с запасом.
UPPER_SLACK = 2.5
LOWER_SLACK = 0.05


def calls():
    with urllib.request.urlopen(base.MOCK + "/calls", timeout=10) as response:
        return json.loads(response.read().decode())


def analyse(items):
    pairs = {}
    for item in items:
        pairs.setdefault((item["session"], item["asset"]), []).append(item)
    result = []
    for (session, asset), rows in sorted(pairs.items()):
        rows.sort(key=lambda r: r["start"])
        pauses = [round(b["start"] - a["end"], 2) for a, b in zip(rows, rows[1:])]
        result.append({
            "сеанс": session, "бумага": asset, "запросов": len(rows), "паузы_с": pauses,
            "мин": min(pauses) if pauses else None, "макс": max(pauses) if pauses else None,
            "срок_соблюден": all(p >= TTL - LOWER_SLACK for p in pauses),
            "устаревшая_не_используется": all(p <= TTL + UPPER_SLACK for p in pauses),
            "истекал": len(rows) > 1,
        })
    return result


def main():
    base.mock("/stats")
    fo = stage4.connect("wim_fo")
    test_ref = base.harness_ref(fo)
    prepare = [base.service(fo, test_ref, name, name + " ttl")
               for name in ("ОчиститьСделки", "ПропорцииПрод", "ПозицияНаВчера")]
    rost_ref = t19.register(fo, EPF, TTL)
    started = stage4.now_iso(fo)
    scenarios = []
    for name in base.SCENARIOS:
        steps = t19.run_scenarios(fo, "1.19 / %d" % TTL, rost_ref, test_ref, [name])
        items = calls()
        scenarios.append({"сценарий": name, "шаг": steps[0], "запросы": items, "анализ": analyse(items)})
        stage4.log("ttl", name, json.dumps([{k: v for k, v in a.items() if k != "паузы_с"}
                                             for a in scenarios[-1]["анализ"]], ensure_ascii=False))
    fo = stage4.connect("wim_fo")
    orders = base.orders(fo)
    statuses = base.statuses(fo)
    baseline = {v["вариант"]: v for v in json.load(open(t19.OUT, encoding="utf-8"))["варианты"]}["1.16"]
    report = {
        "дата": datetime.datetime.now().isoformat(timespec="seconds"),
        "срок_с": TTL,
        "подготовка": prepare,
        "сценарии": scenarios,
        "сверка_поручений": base.compare(baseline["поручения"], orders),
        "статусы_совпадают": baseline["статусы"] == statuses,
        "замеры": stage4.measurements(fo, started),
    }
    # Срок кеша на dev возвращается в 0.
    t19.register(fo, EPF, 0)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    c = report["сверка_поручений"]
    stage4.log("compare", "same", c["совпало"], "diff", len(c["расхождения"]), "only16", len(c["только_1_16"]),
               "only_new", len(c["только_1_18"]), "statuses", report["статусы_совпадают"])
    stage4.log("DONE", OUT)


if __name__ == "__main__":
    main()
