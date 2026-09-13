#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance test: posting expense invoice with many tabular rows.
Measures only Записать(Проведение) of РасходнаяНакладная.
"""

from __future__ import annotations

import html
import json
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Any, List

import pythoncom
import win32com.client

IB_PATH = r"C:\1c\Cursor_1c\WORK\OU_Training"
USER_NAME = "Admin"
USER_PASSWORD = "1"
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
# Default sizes for load curve
DEFAULT_SIZES = [50, 100, 200, 500]
REPEATS = 2


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def connect() -> Any:
    com = win32com.client.Dispatch("V83.COMConnector")
    return com.Connect(
        f"File='{IB_PATH}';Usr='{USER_NAME}';Pwd='{USER_PASSWORD}';App='PyCOM';Locale=ru_RU;"
    )


def dt(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, 0, 0)


def set_policy(conn: Any, period: datetime, method_name: str) -> None:
    method = getattr(conn.Перечисления.МетодыОценкиЗапасов, method_name)
    mgr = conn.РегистрыСведений.УчетнаяПолитикаУУ.СоздатьМенеджерЗаписи()
    mgr.Период = period
    mgr.МетодОценкиЗапасов = method
    mgr.Записать()


def create_catalog(conn: Any, name: str, description: str, fill=None) -> Any:
    manager = getattr(conn.Справочники, name)
    obj = manager.СоздатьЭлемент()
    obj.Наименование = description
    if fill is not None:
        fill(obj, conn)
    obj.Записать()
    return obj.Ссылка


def prepare_stock(conn: Any, n_rows: int, tag: str, date_in: datetime):
    """Create N goods + one receipt with qty=10 each. Returns context."""
    warehouse = create_catalog(conn, "Склады", f"Perf WH {tag}")
    supplier = create_catalog(conn, "Контрагенты", f"Perf Sup {tag}")
    buyer = create_catalog(conn, "Контрагенты", f"Perf Buy {tag}")

    def fill_goods(obj, c):
        obj.ТипНоменклатуры = c.Перечисления.ТипыНоменклатуры.Товар

    goods: List[Any] = []
    for i in range(n_rows):
        goods.append(
            create_catalog(conn, "Номенклатура", f"PerfGoods {tag} {i:04d}", fill_goods)
        )

    set_policy(conn, dt(date_in.year, 1, 1), "FIFO")

    receipt = conn.Документы.ПриходнаяНакладная.СоздатьДокумент()
    receipt.Дата = date_in
    receipt.Склад = warehouse
    receipt.Контрагент = supplier
    receipt.Комментарий = f"perf prepare {tag}"
    for g in goods:
        row = receipt.Товары.Добавить()
        row.Номенклатура = g
        row.Количество = 10
        row.Цена = 100
        row.Сумма = 1000
    t0 = time.perf_counter()
    receipt.Записать(conn.РежимЗаписиДокумента.Проведение)
    prep_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "warehouse": warehouse,
        "buyer": buyer,
        "goods": goods,
        "prep_receipt_ms": prep_ms,
    }


def post_expense(conn: Any, ctx: dict, date_out: datetime, qty: float = 1.0) -> float:
    """Post expense with one line per goods item; return duration_ms."""
    doc = conn.Документы.РасходнаяНакладная.СоздатьДокумент()
    doc.Дата = date_out
    doc.Склад = ctx["warehouse"]
    doc.Контрагент = ctx["buyer"]
    doc.Комментарий = "perf expense"
    for g in ctx["goods"]:
        row = doc.Товары.Добавить()
        row.Номенклатура = g
        row.Количество = qty
        row.Цена = 300
        row.Сумма = qty * 300
    t0 = time.perf_counter()
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    return (time.perf_counter() - t0) * 1000.0


def run_size(conn: Any, n_rows: int, version: str) -> dict:
    tag = f"{version}_{n_rows}_{datetime.now().strftime('%H%M%S%f')}"
    year = 2026
    # Use spaced dates per size to avoid collisions
    day_base = 1 + (n_rows % 20)
    date_in = dt(year, 3, day_base, 10)
    results_ms: List[float] = []
    prep_ms = 0.0

    for r in range(REPEATS):
        tag_r = f"{tag}_r{r}"
        ctx = prepare_stock(conn, n_rows, tag_r, date_in)
        prep_ms = ctx["prep_receipt_ms"]
        # expense next day
        date_out = dt(year, 3, day_base, 15)
        # shift date slightly per repeat via seconds in datetime - use different hour
        date_out = dt(year, 3, min(day_base + 1, 28), 12 + r)
        ms = post_expense(conn, ctx, date_out, qty=1.0)
        results_ms.append(ms)
        safe_print(f"  N={n_rows} repeat={r+1}/{REPEATS}: expense={ms:.1f} ms")

    avg = sum(results_ms) / len(results_ms)
    return {
        "version": version,
        "rows": n_rows,
        "repeats": REPEATS,
        "expense_ms_list": [round(x, 2) for x in results_ms],
        "expense_ms_avg": round(avg, 2),
        "ms_per_line": round(avg / n_rows, 3),
        "prep_receipt_ms_last": round(prep_ms, 2),
    }


def write_report(version: str, rows_data: List[dict], path: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(path.replace(".html", ".json"), "w", encoding="utf-8") as f:
        json.dump({"version": version, "results": rows_data, "time": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

    body_rows = []
    for r in rows_data:
        body_rows.append(
            "<tr>"
            f"<td>{r['rows']}</td>"
            f"<td>{r['expense_ms_avg']}</td>"
            f"<td>{r['ms_per_line']}</td>"
            f"<td>{html.escape(str(r['expense_ms_list']))}</td>"
            f"<td>{r['prep_receipt_ms_last']}</td>"
            "</tr>"
        )
    html_doc = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"/>
<title>Perf expense {html.escape(version)}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px}}
.box{{padding:12px;border-left:4px solid #17a2b8;background:#e8f7fb;margin:12px 0}}
.ok{{border-left-color:#28a745;background:#eaf7ee}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left}}
th{{background:#f5f5f5}}
</style></head><body>
<h1>Замер проведения расходной накладной ({html.escape(version)})</h1>
<div class="box">
Таймер только на Записать(Проведение) расходной. Подготовка остатков (приход) отдельно.
Repeats={REPEATS}. Version={html.escape(version)}.
</div>
<table>
<thead><tr><th>N строк</th><th>Avg ms</th><th>ms/строка</th><th>Все прогоны ms</th><th>Приход prep ms</th></tr></thead>
<tbody>{''.join(body_rows)}</tbody>
</table>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)


def main() -> int:
    version = "before"
    sizes = DEFAULT_SIZES
    if len(sys.argv) > 1:
        version = sys.argv[1]
    if len(sys.argv) > 2:
        sizes = [int(x) for x in sys.argv[2].split(",")]

    pythoncom.CoInitialize()
    try:
        safe_print(f"=== Perf version={version} sizes={sizes} ===")
        conn = connect()
        rows_data = []
        try:
            for n in sizes:
                safe_print(f"--- size {n} ---")
                rows_data.append(run_size(conn, n, version))
        finally:
            del conn

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(REPORT_DIR, f"perf_expense_{version}_{stamp}.html")
        write_report(version, rows_data, path)
        safe_print(f"Report: {path}")
        for r in rows_data:
            safe_print(
                f"SUMMARY {version} N={r['rows']}: avg={r['expense_ms_avg']} ms "
                f"({r['ms_per_line']} ms/line)"
            )
        return 0
    except Exception:
        safe_print(traceback.format_exc())
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
