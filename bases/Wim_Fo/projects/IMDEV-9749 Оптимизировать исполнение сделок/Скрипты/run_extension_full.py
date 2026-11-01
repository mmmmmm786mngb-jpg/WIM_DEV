#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Прогон кода расширения FO_DealExecutionParallel на объеме ночи 27.10 через типовую процедуру (вариант A при
подключенном расширении): удалить прежние тестовые данные, создать данные, исполнить, сравнить со снимком
варианта A серии 01.11.2026 (код конфигурации без расширения) и удалить данные. Сводка - bench_parallel_series_*.txt."""

import os
import sys

import run_bench_parallel_series as series

BASELINE = os.path.join(series.REPORTS, "bench_parallel_snapA_20261101_075335.txt")


def main():
    series.say("Серия: код расширения FO_DealExecutionParallel на объеме ночи 27.10 (вариант A с расширением)")
    series.stage(["cleanup"], 1800)
    series.stage(["prepare"], 3600)
    snapshot = series.stage(["run", "A"], 7200)
    if snapshot:
        series.stage(["compare", BASELINE, snapshot], 600)
    series.stage(["cleanup"], 3600)
    series.say("Серия завершена. Сводка: " + series.SUMMARY)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
