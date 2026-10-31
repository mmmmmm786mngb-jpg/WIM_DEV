#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цена одного списочного чтения процента исполнения и статусов на разном числе поручений."""

import datetime
import os
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STAND = (
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Fo\projects"
    r"\IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО"
    r"\Тестирование\Стенд_МО_ФО"
)
sys.path.insert(0, STAND)

import stand_common as stand  # noqa: E402
from bench_execution_queries import EXEC_READ, STATUS_ORIGINAL  # noqa: E402


def log(text):
    print(text.encode("ascii", "replace").decode("ascii"), flush=True)


def timed(conn, text, params):
    stand.query(conn, text, params)
    samples = []
    count = 0
    for _ in range(3):
        started = time.perf_counter()
        rows = stand.query(conn, text, params)
        samples.append((time.perf_counter() - started) * 1000.0)
        count = len(rows)
    return statistics.median(samples), count


def main():
    conn = stand.connect("wim_fo")
    counted = stand.query(
        conn,
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.Поручение ГДЕ Проведен И НЕ ПометкаУдаления",
        {},
    )
    log("posted orders %s" % counted[0]["Количество"])
    rows = stand.query(
        conn,
        """
ВЫБРАТЬ ПЕРВЫЕ 5000
    Поручения.Ссылка КАК Поручение
ИЗ
    Документ.Поручение КАК Поручения
ГДЕ
    Поручения.Проведен
    И НЕ Поручения.ПометкаУдаления
""",
        {},
    )
    orders = [row["Поручение"] for row in rows]
    log("loaded %d" % len(orders))
    now = stand.date_1c(conn, datetime.datetime.now())
    empty = stand.to_array(conn, [])
    sizes = [1, 20, 100, 500, 1000, 2000, 5000]
    for size in sizes:
        if size > len(orders):
            continue
        chunk = stand.to_array(conn, orders[:size])
        exec_ms, exec_rows = timed(conn, EXEC_READ, {
            "Поручения": chunk,
            "ПорученияОтменяемые": empty,
        })
        status_ms, status_rows = timed(conn, STATUS_ORIGINAL, {
            "Поручения": chunk,
            "ТекущаяДатаСеанса": now,
        })
        log("size %d exec %.1f ms rows %d status %.1f ms rows %d" % (
            size, exec_ms, exec_rows, status_ms, status_rows))


if __name__ == "__main__":
    main()
