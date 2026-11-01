#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полная серия стенда параллельного исполнения: данные ночи 27.10, варианты A, B, D (6 потоков), сравнение, удаление.

Каждый этап - отдельный процесс run_bench_parallel.py. После строки STAGE DONE процесс снимается,
если он завис на выходе из COM-соединения. Сводка серии пишется в Тестирование/reports/bench_parallel_series_*.txt.
"""

import datetime
import os
import re
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
RUNNER = os.path.join(HERE, "run_bench_parallel.py")
REPORTS = os.path.join(PROJECT, "Тестирование", "reports")
SUMMARY = os.path.join(REPORTS, "bench_parallel_series_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def say(text):
    line = "%s %s" % (datetime.datetime.now().strftime("%H:%M:%S"), text)
    print(line, flush=True)
    with open(SUMMARY, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def stage(args, timeout):
    say("=== " + " ".join(args))
    process = subprocess.Popen([sys.executable, RUNNER] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", cwd=HERE)
    lines = []
    done = threading.Event()

    def reader():
        for line in process.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            if line == "STAGE DONE":
                done.set()

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    started = time.time()
    while process.poll() is None and time.time() - started < timeout:
        if done.is_set():
            time.sleep(5)
            if process.poll() is None:
                process.kill()
                say("stage process killed after STAGE DONE")
            break
        time.sleep(2)
    if process.poll() is None:
        process.kill()
        say("STAGE TIMEOUT, killed")
    thread.join(timeout=10)
    for line in lines:
        if re.match(r"^\d\d:\d\d:\d\d ", line) or line.startswith(("SNAPSHOT", "REPORT", "state", "differences",
                                                                       "  ", "left", "right", "GetListOfDeals")):
            say("  " + line)
    snapshot = next((line.split(" ", 1)[1] for line in lines if line.startswith("SNAPSHOT ")), None)
    return snapshot


def main():
    os.makedirs(REPORTS, exist_ok=True)
    say("Серия: ночь 27.10 обычного ФО, варианты A, B, D (6 потоков)")
    stage(["prepare"], 7200)
    snap_a = stage(["run", "A"], 14400)
    stage(["reset"], 7200)
    snap_b = stage(["run", "B"], 14400)
    stage(["reset"], 7200)
    snap_d = stage(["run", "D", "6"], 14400)
    if snap_a and snap_b:
        stage(["compare", snap_a, snap_b], 600)
    if snap_a and snap_d:
        stage(["compare", snap_a, snap_d], 600)
    stage(["cleanup"], 7200)
    say("Серия завершена. Сводка: " + SUMMARY)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
