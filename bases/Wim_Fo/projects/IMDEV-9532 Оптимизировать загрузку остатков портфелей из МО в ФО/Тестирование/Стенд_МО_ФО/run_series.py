# -*- coding: utf-8 -*-
"""Серия прогонов для сравнения вариантов (без расширения / с расширением) при одном состоянии данных.

Порядок сценариев фиксирован, чтобы каждый вариант начинался с одного и того же состояния флагов:
  full_1t_a, full_1t_b          - полная выгрузка 450 портфелей в 1 поток (флаги перед ней: после перерасчета)
  norecalc_1t                   - то же без перерасчета: снимок фиксирует флаги сразу после вызова 872
  full_after_norecalc           - полная выгрузка после прогона без перерасчета (возвращает флаги в исходное)
  full_5t_a, full_5t_b          - полная выгрузка в 5 потоков, как в ПРОД

  python run_series.py <префикс> 1t|5t|all
Каждый прогон сохраняется в results/<время>_<префикс>_<сценарий>/ (см. run_export.py).
"""
import subprocess
import sys

SCENARIOS = {
    "1t": [("full_1t_a", []), ("full_1t_b", []), ("norecalc_1t", ["--no-recalc"]), ("full_after_norecalc", [])],
    "5t": [("full_5t_a", ["--threads", "5"]), ("full_5t_b", ["--threads", "5"])],
}
KEEP = ("Опубликовать", "Выгрузка всего", "позиция_выгружена", "Версионирование", "Фоновый перерасчет", "754:",
        "768:", "872:", "4-й:", "Результаты")


def main():
    prefix, part = sys.argv[1], sys.argv[2]
    parts = ["1t", "5t"] if part == "all" else [part]
    for name in parts:
        for scenario, extra in SCENARIOS[name]:
            print(f"=== {prefix}_{scenario}", flush=True)
            result = subprocess.run([sys.executable, "run_export.py", "--scenario", f"{prefix}_{scenario}", *extra],
                                    capture_output=True, text=True, encoding="utf-8")
            for line in (result.stdout + result.stderr).splitlines():
                if any(k in line for k in KEEP) or "Error" in line or "Traceback" in line:
                    print(line, flush=True)


if __name__ == "__main__":
    main()
