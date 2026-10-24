# -*- coding: utf-8 -*-
"""Покупка и продажа РОСТ: эталон 1.18-т1 (релиз) и 1.25-т1 подряд на выборке T9531PROP (dev ФО).

Тот же прогон, что ../1_24/run_purchase_sale.py (команда задания и путь формы, повтор продажи), другие сборки
и файл результата reports/purchase_sale_118_125.json. Перед запуском - ../1_24/prepare_purchase_sale.py.

    python run_purchase_sale_125.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "1_24"))
import run_purchase_sale as rps  # noqa: E402

rps.BUILDS = {"1.18": os.path.join(rps.T1, "РОСТ_1.18-т1.epf"), "1.25": os.path.join(rps.T1, "РОСТ_1.25-т1.epf")}
rps.PLAN = (
    ("1.18", "команда", ("Покупка.Команда", "Продажа.Команда", "Продажа.Повтор")),
    ("1.25", "команда", ("Покупка.Команда", "Продажа.Команда", "Продажа.Повтор")),
    ("1.18", "форма", ("Покупка.Форма", "Продажа.Форма")),
    ("1.25", "форма", ("Покупка.Форма", "Продажа.Форма")),
)
rps.REPORTS = os.path.join(HERE, "reports")
rps.OUT = os.path.join(rps.REPORTS, "purchase_sale_118_125.json")

if __name__ == "__main__":
    rps.main()
