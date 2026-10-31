#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Регресс и ускорение пересчета поручений на 1000 тестовых сделках.

Проведение документов не заменяется списком: сравнивается только чтение,
которым ОбновитьДанныеИсполнения заполняет процент исполнения и объем.
Тысяча отдельных вызовов и один вызов на весь список должны вернуть те же
числа. Документы помечены TEXEC1000 и удаляются в конце.
"""

import datetime
import os
import sys
import time
import traceback

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
import bench_execution_queries as bench  # noqa: E402

COUNT = 1000
MARKER = "TEXEC1000"
REPORTS = os.path.join(os.path.dirname(HERE), "Тестирование", "reports")


def say(lines, text):
    lines.append(text)
    print(text.encode("ascii", "replace").decode("ascii"), flush=True)


def doc_manager(conn, name):
    try:
        return conn.NewObject("ДокументМенеджер." + name)
    except Exception:
        return getattr(conn.Документы, name)


def load_template(conn):
    rows = stand.query(
        conn,
        """
ВЫБРАТЬ ПЕРВЫЕ 1
    Поручения.Актив КАК Актив,
    Поручения.ВалютаРасчетов КАК ВалютаРасчетов,
    Поручения.Портфель КАК Портфель,
    Поручения.СчетУчета КАК СчетУчета,
    ЗНАЧЕНИЕ(Перечисление.ТипыПортфелей.АктивыДляПерепродажи) КАК ТипПортфеля,
    ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.Сделка) КАК ВидСделка,
    ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.РЕПО) КАК ВидРепо,
    ЗНАЧЕНИЕ(Перечисление.ВидыОперацийСделки.Покупка) КАК Покупка,
    ЗНАЧЕНИЕ(Перечисление.ВидыОперацийСделки.Продажа) КАК Продажа
ИЗ
    Документ.Поручение КАК Поручения
ГДЕ
    Поручения.Актив <> ЗНАЧЕНИЕ(Справочник.Активы.ПустаяСсылка)
    И Поручения.ВалютаРасчетов <> ЗНАЧЕНИЕ(Справочник.Валюты.ПустаяСсылка)
""",
        {},
    )
    if not rows:
        raise RuntimeError("Нет поручения-образца с активом, валютой и типом портфеля")
    return rows[0]


def profile(index):
    """Разные ветки запроса: непроведенные, покупка, продажа, РЕПО по сумме."""
    if index < 100:
        return "draft", 10 + (index % 7), 0, False
    if index < 800:
        return "buy", 10 + (index % 50), 100 + (index % 17), False
    if index < 950:
        return "sell", 20 + (index % 10), 50 + (index % 9), False
    return "repo", 5 + (index % 4), 1000 + index, True


def write_order(conn, manager, template, moment, index):
    kind, qty, price, by_sum = profile(index)
    order = manager.СоздатьДокумент()
    order.Дата = moment
    order.Актив = template["Актив"]
    order.ВалютаРасчетов = template["ВалютаРасчетов"]
    order.ТипПортфеля = template["ТипПортфеля"]
    order.Портфель = template["Портфель"]
    order.СчетУчета = template["СчетУчета"]
    order.ВидОперации = template["ВидРепо"] if kind == "repo" else template["ВидСделка"]
    order.Направление = template["Продажа"] if kind == "sell" else template["Покупка"]
    order.Количество = qty
    order.СуммаПоручения = 1000 + index if by_sum else qty * price
    order.ЗаполнениеПоСумме = by_sum
    order.ЦенаВВалютеРасчетов = price
    order.Купон = 1
    order.КурсПересчетов = 1
    order.КомментарийКлиента = MARKER
    row = order.РаспределениеПоПортфелям.Добавить()
    row.Портфель = template["Портфель"]
    row.ТипПортфеля = template["ТипПортфеля"]
    row.Количество = qty
    row.СчетУчета = template["СчетУчета"]
    order.ОбменДанными.Загрузка = True
    if kind == "draft":
        order.Записать()
    else:
        order.Записать(conn.РежимЗаписиДокумента.Проведение)
    return order.Ссылка, kind


def write_deal(manager, template, moment, index, order_ref):
    deal = manager.СоздатьДокумент()
    deal.Дата = moment
    deal.ДатаПоставки = moment
    deal.Актив = template["Актив"]
    deal.Поручение = order_ref
    deal.ВидОперации = template["ВидСделка"]
    deal.Внебиржевая = False
    deal.Количество = 10
    deal.НомерСделки = "%s-%04d" % (MARKER, index)
    deal.ОбменДанными.Загрузка = True
    deal.Записать()
    return deal.Ссылка


def write_forecast(conn, order_ref, template, moment, quantity):
    recordset = conn.РегистрыНакопления.ПрогнозПоПоручению.СоздатьНаборЗаписей()
    recordset.Отбор.Регистратор.Установить(order_ref)
    row = recordset.ДобавитьПриход()
    row.Период = moment
    row.Портфель = template["Портфель"]
    row.Актив = template["Актив"]
    row.Поручение = order_ref
    row.ТипПортфеля = template["ТипПортфеля"]
    row.СчетУчета = template["СчетУчета"]
    row.Количество = quantity
    row.Сумма = quantity
    recordset.Записать()


def clear_forecast(conn, order_ref):
    recordset = conn.РегистрыНакопления.ПрогнозПоПоручению.СоздатьНаборЗаписей()
    recordset.Отбор.Регистратор.Установить(order_ref)
    recordset.Записать()


def create_pack(conn, template, lines):
    order_mgr = doc_manager(conn, "Поручение")
    deal_mgr = doc_manager(conn, "Сделка")
    moment = stand.date_1c(conn, datetime.datetime(2026, 10, 31, 12, 0, 0))
    orders = []
    forecast_orders = []
    started = time.perf_counter()
    forecast_enabled = True
    for index in range(COUNT):
        ref, kind = write_order(conn, order_mgr, template, moment, index)
        orders.append(ref)
        write_deal(deal_mgr, template, moment, index, ref)
        if kind == "sell" and forecast_enabled:
            try:
                write_forecast(conn, ref, template, moment, 5)
                forecast_orders.append(ref)
            except Exception:
                forecast_enabled = False
                say(lines, "Остаток прогноза не записан, сравнение пойдет без него: %s" % sys.exc_info()[1])
        if index == 0 or (index + 1) % 200 == 0:
            say(lines, "Создано %d из %d за %.1f с" % (index + 1, COUNT, time.perf_counter() - started))
    say(lines, "Пакет создан за %.1f с, остатков прогноза %d" % (
        time.perf_counter() - started, len(forecast_orders)))
    return orders, forecast_orders, moment


def delete_marked(conn, lines):
    deals = stand.query(
        conn,
        """
ВЫБРАТЬ
    Сделки.Ссылка КАК Ссылка
ИЗ
    Документ.Сделка КАК Сделки
ГДЕ
    Сделки.НомерСделки ПОДОБНО &Маска
""",
        {"Маска": MARKER + "%"},
    )
    orders = stand.query(
        conn,
        """
ВЫБРАТЬ
    Поручения.Ссылка КАК Ссылка
ИЗ
    Документ.Поручение КАК Поручения
ГДЕ
    Поручения.КомментарийКлиента = &Маркер
""",
        {"Маркер": MARKER},
    )
    started = time.perf_counter()
    cleared = 0
    for row in orders:
        try:
            clear_forecast(conn, row["Ссылка"])
            cleared += 1
        except Exception:
            break
    for row in list(deals) + list(orders):
        obj = row["Ссылка"].ПолучитьОбъект()
        if obj is None:
            continue
        obj.ОбменДанными.Загрузка = True
        obj.Удалить()
    say(lines, "Удалено сделок %d, поручений %d, очищено наборов прогноза %d за %.1f с" % (
        len(deals), len(orders), cleared, time.perf_counter() - started))


def uid(conn, ref):
    return conn.String(ref.УникальныйИдентификатор())


def row_map(conn, rows):
    found = {}
    for row in rows:
        found[uid(conn, row["Поручение"])] = (
            round(float(bench.num(row["Исполнение"]) or 0), 4),
            round(float(bench.num(row["Объем"]) or 0), 2),
        )
    return found


def compare_maps(lines, single_map, batch_map):
    only_single = [key for key in single_map if key not in batch_map]
    only_batch = [key for key in batch_map if key not in single_map]
    mismatched = []
    for key, left in single_map.items():
        right = batch_map.get(key)
        if right is None:
            continue
        if abs(left[0] - right[0]) > 0.0001 or abs(left[1] - right[1]) > 0.01:
            mismatched.append((key, left, right))
    say(lines, "Поштучно поручений %d, списком %d" % (len(single_map), len(batch_map)))
    say(lines, "Только в поштучном %d, только в списке %d, расхождений чисел %d" % (
        len(only_single), len(only_batch), len(mismatched)))
    distinct = sorted(set(single_map.values()))
    say(lines, "Различных пар (исполнение, объем) в поштучном результате: %d" % len(distinct))
    for sample in distinct[:8]:
        say(lines, "  пример %.4f / %.2f" % sample)
    for item in mismatched[:5]:
        say(lines, "  расхождение %s: поштучно %s, список %s" % (item[0], item[1], item[2]))
    ok = not only_single and not only_batch and not mismatched and len(single_map) == COUNT
    say(lines, "Регресс чтения: %s" % ("совпало" if ok else "ЕСТЬ РАСХОЖДЕНИЯ"))
    return ok


def run_read(conn, orders, empty_orders):
    started = time.perf_counter()
    rows = stand.query(conn, bench.EXEC_READ, {
        "Поручения": stand.to_array(conn, orders),
        "ПорученияОтменяемые": empty_orders,
    })
    return (time.perf_counter() - started) * 1000.0, rows


def main():
    lines = []
    say(lines, "Старт %s. Стенд WIN_FO_server, документов %d." % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), COUNT))
    say(lines, "Сравнивается чтение ОбновитьДанныеИсполнения. Проведение исполнения этим тестом не выполняется.")
    conn = stand.connect("wim_fo")
    delete_marked(conn, lines)
    template = load_template(conn)
    forecast_orders = []
    try:
        orders, forecast_orders, _moment = create_pack(conn, template, lines)
        empty_orders = stand.to_array(conn, [])
        say(lines, "--- Поштучное чтение, как в проведении каждого документа")
        single_rows = []
        single_times = []
        run_read(conn, [orders[0]], empty_orders)
        started = time.perf_counter()
        for index, order in enumerate(orders):
            elapsed, rows = run_read(conn, [order], empty_orders)
            single_times.append(elapsed)
            single_rows.extend(rows)
            if (index + 1) % 200 == 0:
                say(lines, "Прочитано по одному %d, сумма %.1f с" % (index + 1, sum(single_times) / 1000.0))
        single_total = time.perf_counter() - started
        say(lines, "1000 отдельных вызовов: %.1f с, медиана %.1f мс" % (
            single_total, bench.median(single_times)))

        say(lines, "--- Один вызов на все поручения")
        run_read(conn, orders, empty_orders)
        batch_times = []
        batch_rows = None
        for _ in range(3):
            elapsed, batch_rows = run_read(conn, orders, empty_orders)
            batch_times.append(elapsed)
        say(lines, "Список из 1000: медиана %.1f мс, замеры %s" % (
            bench.median(batch_times), ", ".join("%.1f" % item for item in batch_times)))
        speedup = single_total / (bench.median(batch_times) / 1000.0) if bench.median(batch_times) else 0
        say(lines, "Ускорение чтения: %.0f раз (%.1f с против %.1f мс)" % (
            speedup, single_total, bench.median(batch_times)))
        compare_maps(lines, row_map(conn, single_rows), row_map(conn, batch_rows))
    except Exception:
        say(lines, "Ошибка:\n%s" % traceback.format_exc())
    finally:
        try:
            delete_marked(conn, lines)
        except Exception:
            say(lines, "Ошибка удаления:\n%s" % traceback.format_exc())
    os.makedirs(REPORTS, exist_ok=True)
    path = os.path.join(REPORTS, "bench_execution_1000_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print("REPORT %s" % path, flush=True)


if __name__ == "__main__":
    main()
