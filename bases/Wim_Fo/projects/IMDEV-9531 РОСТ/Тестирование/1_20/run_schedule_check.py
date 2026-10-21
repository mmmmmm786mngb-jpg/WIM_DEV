# -*- coding: utf-8 -*-
"""Проверка регламентной покупки на финальной сборке 1.20 (срок кеша 60 с).

Команда регламентного задания ФоновоеВыполнениеПокупка вызывается обвязкой T9530_ТестРОСТ (сценарий Покупка.Команда,
тот же ВыполнитьКоманду, что у задания) два раза подряд, как два соседних запуска раз в 10 минут:
  1-й запуск - поручения покупки сверяются с эталоном 1.16 из reports/run_1_20.json (портфели T9531PROP_P);
  2-й запуск - новых поручений нет (портфели уже переведены в следующий статус), ошибок нет.
Проверяются также комментарии замеров ("Запуск: регламентное задание") и отсутствие сообщений с таблицей цен.

    python run_schedule_check.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_1_20_tests as r  # noqa: E402

stage4 = r.stage4
OUT = os.path.join(HERE, "reports", "schedule_check.json")


def purchase_orders(orders):
    return {k: v for k, v in orders.items() if k.startswith("T9531PROP_P")}


def main():
    baseline = json.load(open(os.path.join(HERE, "reports", "run_1_20.json"), encoding="utf-8"))
    base_orders = purchase_orders({v["вариант"]: v for v in baseline["варианты"]}["1.16"]["поручения"])

    fo = stage4.connect("wim_fo")
    test_ref = r.base.harness_ref(fo)
    prepare = [r.base.service(fo, test_ref, name, name + " регламент 1.20")
               for name in ("ОчиститьСделки", "ПропорцииПрод", "ПозицияНаВчера")]
    rost_ref = r.v19.register(fo, r.EPF_120, 60)
    started = stage4.now_iso(fo)

    runs = []
    for number in (1, 2):
        r.base.mock("/reset")
        steps = r.v19.run_scenarios(fo, "регламент %d" % number, rost_ref, test_ref, ["Покупка.Команда"])
        # Ссылки rost_ref и test_ref принадлежат этому соединению: поручения читаются отдельным соединением.
        runs.append({"запуск": number, "шаг": steps[0],
                     "поручения": purchase_orders(r.base.orders(stage4.connect("wim_fo")))})

    first, second = runs[0]["поручения"], runs[1]["поручения"]
    measurements = [m for m in stage4.measurements(fo, started) if m["ключ"] == "СозданиеТорговыхПорученийРОСТ.Покупка"]
    report = {
        "подготовка": prepare,
        "запуски": [{"запуск": x["запуск"], **x["шаг"], "поручений_покупки": sum(len(v) for v in x["поручения"].values())}
                    for x in runs],
        "сверка_1_запуска_с_1_16": r.base.compare(base_orders, first),
        "2_запуск_не_добавил_поручений": first == second,
        "комментарии_замеров": [m["комментарий"] for m in measurements],
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    c = report["сверка_1_запуска_с_1_16"]
    for x in report["запуски"]:
        stage4.log("run", x["запуск"], x["длительность_с"], "orders", x["поручений_покупки"], "stakan", x["запросов_стакана"],
                   "error", (x.get("ошибка") or "")[:200], x["режим_кеша_в_логе"])
    stage4.log("compare with 1.16: same", c["совпало"], "of", c["поручений_1_16"], "diff", len(c["расхождения"]),
               "only16", len(c["только_1_16"]), "onlynew", len(c["только_1_18"]))
    stage4.log("second run added nothing:", report["2_запуск_не_добавил_поручений"])
    for comment in report["комментарии_замеров"]:
        stage4.log("measure:", comment)


if __name__ == "__main__":
    main()
