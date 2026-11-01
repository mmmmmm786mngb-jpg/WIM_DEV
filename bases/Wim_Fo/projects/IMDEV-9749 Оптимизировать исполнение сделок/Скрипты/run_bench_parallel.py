#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Стенд параллельного исполнения сделок (BenchParallelExecution) на разработческой ФО.

Этапы (первый аргумент):
  prepare [smoke]       - включить GetListOfDeals (исходное значение в state), создать данные по образцу ночи 27.10
                          обычного ФО (smoke - малый набор для проверки обработки)
  run A|B|C|D [потоков] - ночь вариантом: A конфигурация как есть, B отложенный пересчет, C отложенный пересчет + потоки,
                          D как C плюс повтор записи документа при неуникальном номере (до 5 раз)
  reset [потоков]       - вернуть тестовые данные в состояние до ночи
  cleanup [потоков]     - удалить все тестовые данные и вернуть GetListOfDeals
  compare SNAP1 SNAP2   - сравнить два снимка итога построчно

Каждый этап запускается фоновым заданием на сервере 1С, скрипт ждет его завершения и печатает лог.
"""

import datetime
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

STAND = (
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Fo\projects"
    r"\IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО"
    r"\Тестирование\Стенд_МО_ФО"
)
sys.path.insert(0, STAND)

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
EPF = os.path.join(PROJECT, "Тестирование", "BenchParallelExecution.epf")
REPORTS = os.path.join(PROJECT, "Тестирование", "reports")
STATE = os.path.join(REPORTS, "bench_parallel_state.json")

MARKER = "TPAR"
DELIVERY_DAY = "20990504"
PORTFOLIOS = 278
THREADS = 6


def night_2710():
    """Сделок на поручение по ночи 27.10 обычного ФО: 1 014 поручений, 9 443 сделки, 18 886 документов.

    Первые 30 строк распределения и 8 крупнейших поручений - из лога практики Т-1; оставшиеся 64 поручения
    (7 050 документов) в логе свернуты, их размер разложен равномерно от 62 до 158 документов.
    """
    known = [(2, 491), (4, 90), (6, 72), (8, 54), (10, 31), (12, 29), (14, 21), (16, 12), (18, 12), (20, 13),
             (22, 16), (24, 14), (26, 7), (28, 9), (30, 13), (32, 8), (34, 8), (36, 7), (38, 6), (40, 4),
             (42, 3), (44, 1), (46, 3), (48, 4), (50, 1), (52, 3), (54, 5), (56, 2), (58, 1), (60, 2)]
    docs = []
    for size, orders in known:
        docs += [size] * orders
    docs += [760, 734, 650, 630, 366, 364, 336, 224]
    rest = [62 + 2 * round(i * 48 / 63) for i in range(64)]
    rest[-1] += 7050 - sum(rest)
    docs += rest
    assert len(docs) == 1014 and sum(docs) == 18886, (len(docs), sum(docs))
    # Перемешать детерминированно, чтобы крупные поручения не шли подряд.
    order = sorted(range(len(docs)), key=lambda i: (i * 7919) % 1014)
    return [docs[i] // 2 for i in order]


def night_smoke():
    return [1, 1, 2, 3, 5, 8, 13, 20, 1, 2, 30, 1, 4, 6, 2, 1, 9, 15, 1, 3]


def connect():
    import stand_common as stand
    return stand.connect("wim_fo")


def structure(conn, values):
    result = conn.NewObject("Структура")
    for key, value in values.items():
        result.Вставить(key, value)
    return result


def log_path(stage):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(REPORTS, "bench_parallel_%s_%s.txt" % (stage, stamp)), stamp


def run_job(conn, method, params, title, timeout):
    call = structure(conn, {
        "ЭтоВнешняяОбработка": True,
        "ИмяОбработки": EPF,
        "ИмяМетода": method,
        "ПараметрыВыполнения": structure(conn, params),
    })
    address = conn.ПоместитьВоВременноеХранилище("", conn.NewObject("УникальныйИдентификатор"))
    args = conn.NewObject("Массив")
    args.Добавить(call)
    args.Добавить(address)
    job = conn.ФоновыеЗадания.Выполнить(
        "ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", args, None, title)
    uid = job.УникальныйИдентификатор
    started = time.time()
    print("job started", title, flush=True)
    active = conn.СостояниеФоновогоЗадания.Активно
    while time.time() - started < timeout:
        job = conn.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != active:
            break
        time.sleep(10)
    print("state", conn.String(job.Состояние), "after %.0f s" % (time.time() - started), flush=True)
    if job.ИнформацияОбОшибке:
        print(conn.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке), flush=True)


def print_log(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as handle:
            print(handle.read(), flush=True)
        print("REPORT", path, flush=True)
    else:
        print("log file missing", path, flush=True)


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=1)


def set_exchange_flag(conn, value):
    conn.Константы.ИспользоватьМетодАpi_GetListOfDeals.Установить(value)


def stage_prepare(conn, smoke):
    state = load_state()
    if "exchange_flag" not in state:
        state["exchange_flag"] = bool(conn.Константы.ИспользоватьМетодАpi_GetListOfDeals.Получить())
        save_state(state)
    set_exchange_flag(conn, True)
    deals = night_smoke() if smoke else night_2710()
    path, _ = log_path("prepare")
    run_job(conn, "Подготовить", {
        "ПутьЛога": path, "Маркер": MARKER, "ДеньПоставки": DELIVERY_DAY,
        "СделокПоПоручениям": ",".join(str(x) for x in deals), "ЧислоПортфелей": PORTFOLIOS,
    }, "TPAR prepare", 7200)
    print_log(path)


def stage_run(conn, variant, threads):
    path, stamp = log_path("run" + variant)
    snapshot = os.path.join(REPORTS, "bench_parallel_snap%s_%s.txt" % (variant, stamp))
    run_job(conn, "ВыполнитьВариант", {
        "ПутьЛога": path, "ПутьСнимка": snapshot, "Маркер": MARKER, "ДеньПоставки": DELIVERY_DAY,
        "Вариант": variant, "Потоков": threads, "ПутьОбработки": EPF,
    }, "TPAR run " + variant, 14400)
    print_log(path)
    print("SNAPSHOT", snapshot, flush=True)


def stage_reset(conn, threads, cleanup):
    path, _ = log_path("cleanup" if cleanup else "reset")
    method = "УдалитьВсе" if cleanup else "Сбросить"
    run_job(conn, method, {
        "ПутьЛога": path, "Маркер": MARKER, "Потоков": threads, "ПутьОбработки": EPF,
    }, "TPAR " + method, 7200)
    print_log(path)
    if cleanup:
        state = load_state()
        if "exchange_flag" in state:
            set_exchange_flag(conn, state["exchange_flag"])
            print("GetListOfDeals restored:", state["exchange_flag"], flush=True)
            state.pop("exchange_flag")
            save_state(state)


def stage_compare(left, right):
    with open(left, encoding="utf-8-sig") as handle:
        rows_left = handle.read().splitlines()
    with open(right, encoding="utf-8-sig") as handle:
        rows_right = handle.read().splitlines()
    map_left = {row.split("|")[0] + "|" + row.split("|")[1]: row for row in rows_left}
    map_right = {row.split("|")[0] + "|" + row.split("|")[1]: row for row in rows_right}
    diffs = []
    for key in sorted(set(map_left) | set(map_right)):
        if map_left.get(key) != map_right.get(key):
            diffs.append((key, map_left.get(key), map_right.get(key)))
    orders = sum(1 for key in map_left if key.startswith("O|"))
    deals = sum(1 for key in map_left if key.startswith("D|"))
    print("left", os.path.basename(left), "orders", orders, "deals", deals)
    print("right", os.path.basename(right), "rows", len(rows_right))
    print("differences", len(diffs))
    for key, a, b in diffs[:20]:
        print(" ", key, "\n    L:", a, "\n    R:", b)


def main():
    stage = sys.argv[1]
    if stage == "compare":
        stage_compare(sys.argv[2], sys.argv[3])
        return
    os.makedirs(REPORTS, exist_ok=True)
    conn = connect()
    if stage == "prepare":
        stage_prepare(conn, len(sys.argv) > 2 and sys.argv[2] == "smoke")
    elif stage == "run":
        threads = int(sys.argv[3]) if len(sys.argv) > 3 else THREADS
        stage_run(conn, sys.argv[2], threads)
    elif stage in ("reset", "cleanup"):
        threads = int(sys.argv[2]) if len(sys.argv) > 2 else THREADS
        stage_reset(conn, threads, stage == "cleanup")
    else:
        raise SystemExit("unknown stage " + stage)


if __name__ == "__main__":
    try:
        main()
    finally:
        # Процесс с COM-соединением 1С иногда зависает на выходе; серия по этой строке снимает его сама.
        print("STAGE DONE", flush=True)
        os._exit(0)
