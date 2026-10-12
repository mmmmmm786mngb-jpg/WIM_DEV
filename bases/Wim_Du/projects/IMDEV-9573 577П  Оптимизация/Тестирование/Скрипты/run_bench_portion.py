# -*- coding: utf-8 -*-
"""Стенд: замер выгрузки одного раздела порциями (T9573_ЗамерCSV.ЗамерПорциями).

python run_bench_portion.py <номер> <раздел> <размеры порций через запятую, 0 - запрос без сортировки>

Файлы - ../Результаты/bench_<номер>/P<размер>/R<n>.csv, сверка побайтно с ../Результаты/csv_<номер>/new.
Время начала и конца каждого прогона печатается для сопоставления с sessmem.py.
"""
import filecmp
import os
import sys
import time

import stand

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
EPF = os.path.join(TASK, "Тестирование", "Обработки", "T9573_ЗамерCSV.epf")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number, section, sizes = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")]
    n = section.replace("Раздел", "")
    base = os.path.join(TASK, "Тестирование", "Результаты", f"bench_{number}")
    reference = os.path.join(TASK, "Тестирование", "Результаты", f"csv_{number}", "new", f"R{n}.csv")
    conn = stand.connect()
    ref = stand.doc_by_number(conn, number)
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    bench = conn.ВнешниеОбработки.Создать(EPF, False, protection)
    lines = []
    for size in sizes:
        d = os.path.join(base, f"P{size}")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"R{n}.csv")
        start = time.strftime("%H:%M:%S")
        t0 = time.time()
        q_ms, loop_ms, rows, parts = (int(x) for x in bench.ЗамерПорциями(ref, section, path, size).split(";"))
        wall = time.time() - t0
        same = ""
        if size and os.path.exists(reference):
            same = ", файл = эталон" if filecmp.cmp(reference, path, shallow=False) else ", ФАЙЛ ОТЛИЧАЕТСЯ"
        line = (f"{section} порция {size or 'без сортировки, только запрос'}: {start}-{time.strftime('%H:%M:%S')}, "
                f"всего {wall:.1f} s, запросы {q_ms / 1000:.1f} s, цикл {loop_ms / 1000:.1f} s, строк {rows:,}, порций {parts}{same}")
        print(line)
        sys.stdout.flush()
        lines.append(line)
    with open(os.path.join(base, "замер_порции.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d ") + "\n".join(lines) + "\n\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
