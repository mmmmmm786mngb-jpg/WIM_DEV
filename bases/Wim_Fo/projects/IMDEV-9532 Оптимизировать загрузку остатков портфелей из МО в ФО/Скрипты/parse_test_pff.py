# -*- coding: utf-8 -*-
"""Разбор замеров производительности ФО (.pff) прогона выгрузки остатков на тестовой копии.

Каждый файл - один сеанс ФО. Вид сеанса определяется по содержимому:
  флаги до позиции (шаг 1)   - строки ДополнительныеСведения, 1 строка на портфель;
  позиция (шаг 2)            - запись фактической позиции, строк ДополнительныеСведения нет;
  снятие блокировок (шаг 3)  - короткий вызов без записей;
  флаги после позиции (шаг 4)- строки ДополнительныеСведения, 3 строки на портфель;
  запуск перерасчета (шаг 5) - ожидание фонового задания БСП;
  фоновый перерасчет РСА     - сеанс фонового задания.
Для вызовов веб-сервиса берется полное время ЗагрузитьПакет, для строк расширения - число строк,
пропусков записи и записей. Результат: папка\разбор_замеров.txt.

  python parse_test_pff.py <папка с .pff>
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROW = re.compile(r'\},"((?:[^"]|"")*)",(\d+),"((?:[^"]|"")*)",(\d+),([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+),')
HEAD = re.compile(r'\{10,"([^"]*)","[^"]*",(\d+),"[^"]*",(\d+),"([^"]*)"')
EXT = "FO_PositionLoadOpt Обработка.ОбменДаннымиБэкОфис.МодульОбъекта"


def parse(path):
    text = open(path, encoding="utf-8-sig").read()
    head = HEAD.search(text[:3000])
    rows = []
    for m in ROW.finditer(text):
        module, line, code, count, total, pure, _, _ = m.groups()
        rows.append((module, int(line), re.sub(r"\s+", " ", code.replace('""', '"')), int(count), float(total),
                     float(pure)))
    return head, rows


def find(rows, module_part, code_part):
    for r in rows:
        if module_part in r[0] and code_part in r[2]:
            return r
    return None


def classify(head, rows):
    call = find(rows, "WebСервис.Avancore", "ЗагрузитьПакет(DownloadPositionReq)")
    loop = find(rows, EXT, "Для Каждого СтрокаОбъектXDTO")
    # Строка 71 модуля расширения - Продолжить после ФлагУжеИмеетЗначение (пропуск записи флага).
    skip = next((r for r in rows if r[0] == EXT and r[1] == 71), None)
    write = find(rows, EXT, "Запись.Записать();")
    wait = find(rows, "ДлительныеОперации", "ОжидатьЗавершенияВыполнения")
    info = {"время_с": call[4] if call else None, "строк": (loop[3] - 1) if loop else 0,
            "пропусков": skip[3] if skip else 0,
            "записей": write[3] if write else 0, "запись_с": write[4] if write else 0.0,
            "чистое_с": sum(r[5] for r in rows)}
    if head and head.group(3) == "16":
        kind = "фоновый перерасчет РСА"
    elif call is None:
        kind = "прочее"
    elif info["строк"] > 0 and info["строк"] >= 2 * max(info["записей"], 1) and info["пропусков"]:
        kind = "шаг 4: флаги после позиции"
    elif info["строк"] > 0:
        kind = "шаг 1: флаг до позиции"
    elif wait:
        kind = "шаг 5: запуск перерасчета"
    elif loop is not None and call[4] > 1:
        kind = "шаг 2: позиция"
    elif call[4] < 0.2:
        kind = "шаг 3: снятие блокировок"
    else:
        kind = "прочее"
    return kind, info


def main():
    folder = sys.argv[1]
    names = sorted((n for n in os.listdir(folder) if n.lower().endswith(".pff")),
                   key=lambda n: int(re.sub(r"\D", "", n) or 0))
    lines = [f"{'файл':12} {'вид сеанса':30} {'время, с':>9} {'строк':>6} {'пропусков':>9} {'записей':>8} "
             f"{'с на запись':>11}"]
    by_kind = {}
    for name in names:
        head, rows = parse(os.path.join(folder, name))
        kind, info = classify(head, rows)
        per_write = info["запись_с"] / info["записей"] if info["записей"] else 0
        time_s = info["время_с"] if info["время_с"] is not None else info["чистое_с"]
        lines.append(f"{name:12} {kind:30} {time_s:9.2f} {info['строк']:6} {info['пропусков']:9} "
                     f"{info['записей']:8} {per_write:11.3f}")
        by_kind.setdefault(kind, []).append((time_s, info))
    lines.append("")
    lines.append("СРЕДНЕЕ ПО ВИДАМ (полные вызовы)")
    for kind, items in sorted(by_kind.items()):
        full = [t for t, i in items if not (kind.startswith("шаг 1") and i["строк"] < 50)]
        if full:
            lines.append(f"  {kind:30} вызовов {len(full):2}  среднее {sum(full) / len(full):6.2f} с  "
                         f"мин {min(full):6.2f}  макс {max(full):6.2f}")
    out = os.path.join(folder, "разбор_замеров.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print("Записан", out)


if __name__ == "__main__":
    main()
