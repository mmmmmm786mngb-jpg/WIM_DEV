# -*- coding: utf-8 -*-
"""Сверка и сравнение двух серий прогонов run_series.py (например base и ext).

Для каждого сценария берется последний прогон серии <префикс>_<сценарий> из results/, сравниваются снимки ФО
(ожидается 0 расхождений) и время: Опубликовать по потокам, вызовы 754/768/872 на ФО, число записей флагов.
Сводка пишется в results/compare_<префикс1>_vs_<префикс2>.json.

  python compare_series.py <префикс1> <префикс2>
"""
import glob
import json
import os
import sys

import snapshot
from stand_common import RESULTS_DIR

SCENARIOS = ["full_1t_a", "full_1t_b", "norecalc_1t", "full_after_norecalc", "full_5t_a", "full_5t_b"]
KINDS = ["754: флаг до позиции", "768: позиция", "872: флаги после позиции"]


def last_run(prefix, scenario):
    # Имя каталога прогона: <ГГГГММДД_ЧЧММСС>_<префикс>_<сценарий>; сравнение по всему хвосту, чтобы префикс
    # base не совпадал с ver_base.
    runs = sorted(d for d in glob.glob(os.path.join(RESULTS_DIR, f"*_{prefix}_{scenario}"))
                  if os.path.basename(d)[16:] == f"{prefix}_{scenario}")
    return runs[-1] if runs else None


def load(run_dir, name):
    with open(os.path.join(run_dir, name), encoding="utf-8") as f:
        return json.load(f)


def metrics(summary):
    publish = max(w["опубликовать_с"] for w in summary["потоки"])
    kinds = {k: summary["по_видам"].get(k, {}).get("всего_с") for k in KINDS}
    errors = any(w["есть_ошибки_МО"] for w in summary["потоки"])
    return {"опубликовать_макс_с": publish, "вызовы_с": kinds, "записей_флагов": summary.get("новых_версий"),
            "ошибки_МО": errors, "готово": summary["готово_флагов"]}


def main():
    first, second = sys.argv[1], sys.argv[2]
    report = []
    for scenario in SCENARIOS:
        a_dir, b_dir = last_run(first, scenario), last_run(second, scenario)
        if not a_dir or not b_dir:
            continue
        a_sum, b_sum = load(a_dir, "summary.json"), load(b_dir, "summary.json")
        diffs = snapshot.compare(load(a_dir, "snapshot.json"), load(b_dir, "snapshot.json"), limit=3)
        item = {"сценарий": scenario, first: metrics(a_sum), second: metrics(b_sum),
                "расхождений_снимка": sum(d["только_в_первом"] + d["только_во_втором"] for d in diffs),
                "расхождения": diffs}
        report.append(item)
        a, b = item[first], item[second]
        print(f"{scenario:22} Опубликовать {a['опубликовать_макс_с']:6.1f} -> {b['опубликовать_макс_с']:6.1f} с | "
              f"872 {a['вызовы_с'][KINDS[2]]} -> {b['вызовы_с'][KINDS[2]]} с | "
              f"754 {a['вызовы_с'][KINDS[0]]} -> {b['вызовы_с'][KINDS[0]]} с | "
              f"записей {a['записей_флагов']} -> {b['записей_флагов']} | "
              f"ошибки МО {a['ошибки_МО']}/{b['ошибки_МО']} | расхождений снимка: {item['расхождений_снимка']}")
    with open(os.path.join(RESULTS_DIR, f"compare_{first}_vs_{second}.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    for item in report:
        for d in item["расхождения"]:
            print(item["сценарий"], json.dumps(d, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
