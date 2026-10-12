# -*- coding: utf-8 -*-
"""Стенд: замер вариантов цикла выгрузки CSV (T9573_ЗамерCSV.epf) по разделам документа 577-П.

python run_bench_csv.py <номер> [варианты, по умолчанию QIRABCDEF] [повторов, по умолчанию 1]

Файлы вариантов пишутся в ../Результаты/bench_<номер>/<вариант>/R<n>.csv и сверяются побайтно
с вариантом A (текущий код) и с эталоном прежней выгрузки ../Результаты/csv_<номер>/old.
Итог: время запроса и цикла по вариантам, мкс на ячейку, совпадение файлов.
"""
import filecmp
import os
import sys
import time

import stand

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
EPF = os.path.join(TASK, "Тестирование", "Обработки", "T9573_ЗамерCSV.epf")
WRITE = "ABCDEFGH"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number = sys.argv[1]
    variants = sys.argv[2] if len(sys.argv) > 2 else "QIRABCDEF"
    repeats = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    base = os.path.join(TASK, "Тестирование", "Результаты", f"bench_{number}")
    old_dir = os.path.join(TASK, "Тестирование", "Результаты", f"csv_{number}", "old")

    conn = stand.connect()
    ref = stand.doc_by_number(conn, number)
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    bench = conn.ВнешниеОбработки.Создать(EPF, False, protection)

    totals = {v: [0, 0, 0] for v in variants}
    cells = {}
    for n in range(1, 12):
        section = f"Раздел{n}"
        for _ in range(repeats):
            for v in variants:
                d = os.path.join(base, v)
                os.makedirs(d, exist_ok=True)
                path = os.path.join(d, f"R{n}.csv")
                q_ms, loop_ms, rows = (int(x) for x in bench.Замер(ref, section, v, path).split(";"))
                totals[v][0] += q_ms
                totals[v][1] += loop_ms
                totals[v][2] += rows
        if "A" in variants:
            with open(os.path.join(base, "A", f"R{n}.csv"), encoding="utf-8-sig") as f:
                cells[n] = (f.readline().count("|")) * (sum(1 for _ in f))

    lines = [f"Документ {number}, повторов {repeats}; время суммарно по 11 разделам, мс"]
    total_cells = sum(cells.values()) * repeats if cells else 0
    for v in variants:
        q_ms, loop_ms, rows = totals[v]
        per_cell = f", {loop_ms * 1000 / total_cells:.2f} мкс/ячейку" if total_cells and v in WRITE + "R" else ""
        lines.append(f"  {v}: запрос {q_ms:,}, цикл {loop_ms:,}, всего {q_ms + loop_ms:,}, строк {rows:,}{per_cell}")
    if "A" in variants:
        for v in variants:
            if v in WRITE and v != "A":
                same = [n for n in range(1, 12) if filecmp.cmp(os.path.join(base, "A", f"R{n}.csv"),
                                                                os.path.join(base, v, f"R{n}.csv"), shallow=False)]
                lines.append(f"  {v} = A побайтно: {len(same)} из 11")
        if os.path.isdir(old_dir):
            same = [n for n in range(1, 12) if filecmp.cmp(os.path.join(old_dir, f"R{n}.csv"),
                                                            os.path.join(base, "A", f"R{n}.csv"), shallow=False)]
            lines.append(f"  A = прежняя выгрузка побайтно: {len(same)} из 11")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(base, "замер.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M ") + text + "\n\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
