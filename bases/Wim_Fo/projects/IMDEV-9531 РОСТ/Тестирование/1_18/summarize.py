# -*- coding: utf-8 -*-
"""Сводка прогонов run_1_18_tests.py: время сценариев, запросы стакана, шаги замеров, сверка поручений и статусов."""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))


def step_totals(measures):
    totals = {}
    for row in measures:
        key = row["ключ"]
        if ".Удельный" in key:
            continue
        name = key.replace("СозданиеТорговыхПорученийРОСТ.", "")
        item = totals.setdefault(name, {"записей": 0, "время_всего_с": 0.0, "вес": 0.0})
        item["записей"] += 1
        item["вес"] += row["вес"]
        # шаги длительной операции БСП пишут среднее на единицу веса, общая запись - полное время
        if name.count(".") >= 1:
            item["время_всего_с"] += row["время_с"] * row["вес"]
        else:
            item["время_всего_с"] += row["время_с"]
    return totals


def main():
    for path in sorted(glob.glob(os.path.join(HERE, "reports", "run_delay_*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        print("=" * 100)
        print(os.path.basename(path), "задержка", data["задержка_с"], data["дата"])
        for version in data["версии"]:
            print("--", version["версия"])
            for prep in version["подготовка"]:
                print("   подготовка", prep["шаг"], prep["состояние"], prep["длительность_с"], prep["ошибка"][:120])
            for step in version["шаги"]:
                print("   %-16s %7s с  стакан %4s  отправка %4s  потоков %s  %s" % (
                    step["шаг"], step.get("длительность_с"), step.get("запросов_стакана"),
                    step.get("поручений_на_отправку"), step.get("потоков"),
                    (step.get("ошибка") or "")[:150] + " ".join(step.get("ошибки_потоков") or [])[:150]))
            for name, item in sorted(step_totals(version["замеры"]).items()):
                print("     %-45s n=%4d вес=%7.0f всего=%8.2f с" % (name, item["записей"], item["вес"],
                                                                     item["время_всего_с"]))
            print("   статусы", version["статусы"])
        check = data.get("сверка_поручений")
        if check:
            print("СВЕРКА:", {k: v for k, v in check.items() if k != "расхождения"})
            for diff in check["расхождения"][:10]:
                print("   diff", diff)
            print("СТАТУСЫ совпадают:", data["сверка_статусов"]["совпадают"])


if __name__ == "__main__":
    main()
