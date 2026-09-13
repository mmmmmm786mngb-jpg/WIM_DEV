#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COM-тесты экзаменационной конфигурации ОперативныйУчетУчебная.
Сценарии: партии, FIFO, средняя, услуги, недостача, корректировка, отчеты.
"""

from __future__ import annotations

import html
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Callable, List, Optional, Tuple

import pythoncom
import win32com.client

IB_PATH = r"C:\1c\Cursor_1c\WORK\OU_Training"
USER_NAME = "Admin"
USER_PASSWORD = "1"
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
YEAR = 2026


def safe_print(text: str) -> None:
    """Console output with ASCII fallback."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def connect(user: str = "", password: str = "") -> Any:
    """Connect to file IB via COM."""
    com = win32com.client.Dispatch("V83.COMConnector")
    parts = [f"File='{IB_PATH}';", "App='PyCOM';", "Locale=ru_RU;"]
    if user:
        parts.append(f"Usr='{user}';")
        parts.append(f"Pwd='{password}';")
    return com.Connect("".join(parts))


def ensure_admin_user() -> Tuple[bool, str]:
    """Create Admin / 1 with role PolnyePrava if missing."""
    # After first user exists, anonymous connect is denied.
    conn = None
    try:
        try:
            conn = connect(USER_NAME, USER_PASSWORD)
            already_ok = True
        except Exception:
            already_ok = False
            conn = connect()

        users = conn.ПользователиИнформационнойБазы
        existing = users.FindByName(USER_NAME)
        if already_ok and existing is not None:
            # Refresh password/role just in case
            user = existing
            created = False
        elif existing is not None:
            user = existing
            created = False
        else:
            user = users.СоздатьПользователя()
            created = True

        user.Имя = USER_NAME
        user.ПолноеИмя = "Administrator"
        user.Пароль = USER_PASSWORD
        user.АутентификацияСтандартная = True
        user.ПоказыватьВСпискеВыбора = True
        try:
            user.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
        except Exception:
            pass

        role = conn.Метаданные.Роли.Найти("ПолныеПрава")
        if role is None:
            return False, "Role PolnyePrava not found in metadata"

        try:
            while user.Роли.Количество() > 0:
                user.Роли.Удалить(0)
        except Exception:
            pass
        user.Роли.Добавить(role)
        user.Записать()

        del conn
        conn = None
        conn2 = connect(USER_NAME, USER_PASSWORD)
        del conn2
        action = "created" if created else "updated"
        return True, f"User {USER_NAME} {action}, password set, role PolnyePrava"
    finally:
        if conn is not None:
            del conn


def dt(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> Any:
    """Build 1C Date via COM NewObject Date."""
    # win32com: use python datetime; COM connector accepts COM dates
    return datetime(year, month, day, hour, minute, 0)


def catalog_find_or_create(conn: Any, catalog_name: str, description: str, fill: Optional[Callable] = None) -> Any:
    """Find catalog item by description or create."""
    manager = getattr(conn.Справочники, catalog_name)
    ref = manager.НайтиПоНаименованию(description, True)
    if ref is not None and not ref.Пустая():
        return ref
    obj = manager.СоздатьЭлемент()
    obj.Наименование = description
    if fill is not None:
        fill(obj, conn)
    obj.Записать()
    return obj.Ссылка


def set_policy(conn: Any, period: datetime, method_name: str) -> None:
    """Write accounting policy record."""
    method = getattr(conn.Перечисления.МетодыОценкиЗапасов, method_name)
    mgr = conn.РегистрыСведений.УчетнаяПолитикаУУ.СоздатьМенеджерЗаписи()
    mgr.Период = period
    mgr.МетодОценкиЗапасов = method
    mgr.Записать()


def create_receipt(conn: Any, date: datetime, warehouse, partner, lines: List[dict]) -> Any:
    """Create and post receipt document."""
    doc = conn.Документы.ПриходнаяНакладная.СоздатьДокумент()
    doc.Дата = date
    doc.Склад = warehouse
    doc.Контрагент = partner
    doc.Комментарий = "COM test receipt"
    for line in lines:
        row = doc.Товары.Добавить()
        row.Номенклатура = line["nomen"]
        row.Количество = line["qty"]
        row.Цена = line["price"]
        row.Сумма = line["qty"] * line["price"]
    doc.Записать(conn.РежимЗаписиДокумента.Проведение)
    return doc.Ссылка


def create_expense(conn: Any, date: datetime, warehouse, partner, lines: List[dict], expect_fail: bool = False) -> Tuple[bool, str, Any]:
    """Create and try to post expense document. Returns (ok, message, ref_or_none)."""
    doc = conn.Документы.РасходнаяНакладная.СоздатьДокумент()
    doc.Дата = date
    doc.Склад = warehouse
    doc.Контрагент = partner
    doc.Комментарий = "COM test expense"
    for line in lines:
        row = doc.Товары.Добавить()
        row.Номенклатура = line["nomen"]
        row.Количество = line["qty"]
        row.Цена = line["price"]
        row.Сумма = line["qty"] * line["price"]
    try:
        doc.Записать(conn.РежимЗаписиДокумента.Проведение)
        if expect_fail:
            return False, "Posting succeeded but shortage was expected", doc.Ссылка
        return True, "Posted OK", doc.Ссылка
    except Exception as exc:
        msg = str(exc)
        if expect_fail:
            return True, f"Blocked as expected: {msg}", None
        return False, f"Posting failed: {msg}", None


def query_table(conn: Any, text: str, params: Optional[dict] = None) -> List[Any]:
    """Run 1C query and return list of rows."""
    query = conn.NewObject("Запрос")
    query.Текст = text
    if params:
        for key, value in params.items():
            query.УстановитьПараметр(key, value)
    result = query.Выполнить().Выгрузить()
    rows = []
    for i in range(result.Количество()):
        rows.append(result.Получить(i))
    return rows


def approx_equal(a: float, b: float, tol: float = 0.02) -> bool:
    return abs(float(a) - float(b)) <= tol


class TestRun:
    def __init__(self) -> None:
        self.results: List[dict] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        self.results.append({"name": name, "status": status, "detail": detail})
        mark = "OK" if condition else "FAIL"
        safe_print(f"[{mark}] {name}: {detail}")

    def summary(self) -> Tuple[int, int]:
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        return passed, failed


def run_scenarios(conn: Any, tr: TestRun) -> None:
    """Create master data and execute exam scenarios."""
    tag = datetime.now().strftime("%H%M%S")
    # Master data
    warehouse = catalog_find_or_create(conn, "Склады", f"Основной склад {tag}")
    supplier = catalog_find_or_create(conn, "Контрагенты", f"Поставщик Тест {tag}")
    buyer = catalog_find_or_create(conn, "Контрагенты", f"Покупатель Тест {tag}")

    def fill_goods(obj, c):
        obj.ТипНоменклатуры = c.Перечисления.ТипыНоменклатуры.Товар

    def fill_service(obj, c):
        obj.ТипНоменклатуры = c.Перечисления.ТипыНоменклатуры.Услуга

    goods = catalog_find_or_create(conn, "Номенклатура", f"Товар А {tag}", fill_goods)
    service = catalog_find_or_create(conn, "Номенклатура", f"Услуга Б {tag}", fill_service)
    tr.check("Master data", True, f"tag={tag}; warehouse/partners/goods/service")

    # Policy FIFO from 01.01
    set_policy(conn, dt(YEAR, 1, 1), "FIFO")
    tr.check("Policy FIFO 01.01", True, "Method FIFO set")

    # Receipts
    r1 = create_receipt(
        conn,
        dt(YEAR, 1, 5),
        warehouse,
        supplier,
        [{"nomen": goods, "qty": 10, "price": 100}],
    )
    r2 = create_receipt(
        conn,
        dt(YEAR, 1, 10),
        warehouse,
        supplier,
        [{"nomen": goods, "qty": 10, "price": 200}],
    )
    tr.check("Receipts posted", True, f"R1={r1}, R2={r2}")

    # Parties created
    parties = query_table(
        conn,
        """
        ВЫБРАТЬ
            ПартииТоваров.Ссылка КАК Ссылка,
            ПартииТоваров.Наименование КАК Наименование,
            ПартииТоваров.ДатаПоступления КАК ДатаПоступления
        ИЗ
            Справочник.ПартииТоваров КАК ПартииТоваров
        ГДЕ
            ПартииТоваров.Номенклатура = &Номенклатура
        УПОРЯДОЧИТЬ ПО
            ДатаПоступления
        """,
        {"Номенклатура": goods},
    )
    tr.check("Parties created", len(parties) >= 2, f"count={len(parties)}")

    # Stock after receipts
    stock = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Остатки.КоличествоОстаток) КАК Количество,
            СУММА(Остатки.СтоимостьОстаток) КАК Стоимость
        ИЗ
            РегистрНакопления.ТоварыНаСкладах.Остатки(&Момент, Номенклатура = &Номенклатура И Склад = &Склад) КАК Остатки
        """,
        {"Момент": dt(YEAR, 1, 11), "Номенклатура": goods, "Склад": warehouse},
    )
    qty = float(stock[0].Количество) if stock and stock[0].Количество is not None else 0
    cost = float(stock[0].Стоимость) if stock and stock[0].Стоимость is not None else 0
    tr.check("Stock after receipts", approx_equal(qty, 20) and approx_equal(cost, 3000), f"qty={qty}, cost={cost}")

    # Service receipt - no stock movement for service
    create_receipt(
        conn,
        dt(YEAR, 1, 6),
        warehouse,
        supplier,
        [{"nomen": service, "qty": 1, "price": 500}],
    )
    svc_stock = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Остатки.КоличествоОстаток) КАК Количество
        ИЗ
            РегистрНакопления.ТоварыНаСкладах.Остатки(, Номенклатура = &Номенклатура) КАК Остатки
        """,
        {"Номенклатура": service},
    )
    svc_qty = 0.0
    if svc_stock and svc_stock[0].Количество is not None:
        svc_qty = float(svc_stock[0].Количество)
    tr.check("Service not on stock", approx_equal(svc_qty, 0), f"qty={svc_qty}")

    # FIFO expense 12.01: 5 pcs @ sale 300 -> cost 500
    ok, msg, exp1 = create_expense(
        conn,
        dt(YEAR, 1, 12),
        warehouse,
        buyer,
        [{"nomen": goods, "qty": 5, "price": 300}],
    )
    tr.check("FIFO expense posted", ok, msg)

    sales = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Продажи.Количество) КАК Количество,
            СУММА(Продажи.СуммаПродажи) КАК СуммаПродажи,
            СУММА(Продажи.Себестоимость) КАК Себестоимость
        ИЗ
            РегистрНакопления.Продажи КАК Продажи
        ГДЕ
            Продажи.Регистратор = &Регистратор
        """,
        {"Регистратор": exp1},
    )
    sebest = float(sales[0].Себестоимость) if sales else -1
    tr.check("FIFO cost = 500", approx_equal(sebest, 500), f"sebest={sebest}")

    stock2 = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Остатки.КоличествоОстаток) КАК Количество,
            СУММА(Остатки.СтоимостьОстаток) КАК Стоимость
        ИЗ
            РегистрНакопления.ТоварыНаСкладах.Остатки(&Момент, Номенклатура = &Номенклатура И Склад = &Склад) КАК Остатки
        """,
        {"Момент": dt(YEAR, 1, 13), "Номенклатура": goods, "Склад": warehouse},
    )
    qty2 = float(stock2[0].Количество) if stock2 and stock2[0].Количество is not None else 0
    cost2 = float(stock2[0].Стоимость) if stock2 and stock2[0].Стоимость is not None else 0
    tr.check("Stock after FIFO", approx_equal(qty2, 15) and approx_equal(cost2, 2500), f"qty={qty2}, cost={cost2}")

    # Switch to average from 15.01
    set_policy(conn, dt(YEAR, 1, 15), "ПоСредней")
    tr.check("Policy average 15.01", True, "Method PoSredney set")

    ok2, msg2, exp2 = create_expense(
        conn,
        dt(YEAR, 1, 16),
        warehouse,
        buyer,
        [{"nomen": goods, "qty": 6, "price": 350}],
    )
    tr.check("Average expense posted", ok2, msg2)
    sales2 = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Продажи.Себестоимость) КАК Себестоимость
        ИЗ
            РегистрНакопления.Продажи КАК Продажи
        ГДЕ
            Продажи.Регистратор = &Регистратор
        """,
        {"Регистратор": exp2},
    )
    sebest2 = float(sales2[0].Себестоимость) if sales2 else -1
    # 6 * (2500/15) = 1000
    tr.check("Average cost ~ 1000", approx_equal(sebest2, 1000), f"sebest={sebest2}")

    # Service expense - sales only, cost 0
    ok_s, msg_s, exp_s = create_expense(
        conn,
        dt(YEAR, 1, 17),
        warehouse,
        buyer,
        [{"nomen": service, "qty": 1, "price": 700}],
    )
    tr.check("Service expense posted", ok_s, msg_s)
    sales_s = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Продажи.Количество) КАК Количество,
            СУММА(Продажи.Себестоимость) КАК Себестоимость,
            СУММА(Продажи.СуммаПродажи) КАК СуммаПродажи
        ИЗ
            РегистрНакопления.Продажи КАК Продажи
        ГДЕ
            Продажи.Регистратор = &Регистратор
        """,
        {"Регистратор": exp_s},
    )
    svc_cost = float(sales_s[0].Себестоимость) if sales_s else -1
    svc_sale = float(sales_s[0].СуммаПродажи) if sales_s else -1
    tr.check("Service cost = 0", approx_equal(svc_cost, 0) and approx_equal(svc_sale, 700), f"cost={svc_cost}, sale={svc_sale}")

    # Remaining stock before shortage: 15-6=9
    stock3 = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Остатки.КоличествоОстаток) КАК Количество
        ИЗ
            РегистрНакопления.ТоварыНаСкладах.Остатки(&Момент, Номенклатура = &Номенклатура И Склад = &Склад) КАК Остатки
        """,
        {"Момент": dt(YEAR, 1, 18), "Номенклатура": goods, "Склад": warehouse},
    )
    qty3 = float(stock3[0].Количество) if stock3 and stock3[0].Количество is not None else 0
    tr.check("Stock before shortage = 9", approx_equal(qty3, 9), f"qty={qty3}")

    ok_bad, msg_bad, _ = create_expense(
        conn,
        dt(YEAR, 1, 18),
        warehouse,
        buyer,
        [{"nomen": goods, "qty": 999, "price": 1}],
        expect_fail=True,
    )
    tr.check("Shortage blocks posting", ok_bad, msg_bad)

    # Stock unchanged after failed posting
    stock4 = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Остатки.КоличествоОстаток) КАК Количество
        ИЗ
            РегистрНакопления.ТоварыНаСкладах.Остатки(&Момент, Номенклатура = &Номенклатура И Склад = &Склад) КАК Остатки
        """,
        {"Момент": dt(YEAR, 1, 19), "Номенклатура": goods, "Склад": warehouse},
    )
    qty4 = float(stock4[0].Количество) if stock4 and stock4[0].Количество is not None else 0
    tr.check("Stock unchanged after shortage", approx_equal(qty4, 9), f"qty={qty4}")

    # Korrektirovka: manual receipt + sales turn
    parties_left = query_table(
        conn,
        """
        ВЫБРАТЬ ПЕРВЫЕ 1
            Остатки.Партия КАК Партия
        ИЗ
            РегистрНакопления.ТоварыНаСкладах.Остатки(&Момент, Номенклатура = &Номенклатура И Склад = &Склад) КАК Остатки
        ГДЕ
            Остатки.КоличествоОстаток > 0
        """,
        {"Момент": dt(YEAR, 1, 20), "Номенклатура": goods, "Склад": warehouse},
    )
    party_ref = parties_left[0].Партия if parties_left else None
    adj = conn.Документы.КорректировкаРегистров.СоздатьДокумент()
    adj.Дата = dt(YEAR, 1, 20)
    adj.Комментарий = "COM test adjust"
    row_t = adj.ТоварыНаСкладах.Добавить()
    row_t.ВидДвижения = conn.Перечисления.ВидыДвижений.Приход
    row_t.Склад = warehouse
    row_t.Номенклатура = goods
    row_t.Партия = party_ref
    row_t.Количество = 1
    row_t.Стоимость = 50
    row_p = adj.Продажи.Добавить()
    row_p.Склад = warehouse
    row_p.Номенклатура = goods
    row_p.Контрагент = buyer
    row_p.Количество = 1
    row_p.СуммаПродажи = 80
    row_p.Себестоимость = 50
    adj.Записать(conn.РежимЗаписиДокумента.Проведение)
    adj_ref = adj.Ссылка
    adj_stock = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Движения.Количество) КАК Количество,
            СУММА(Движения.Стоимость) КАК Стоимость
        ИЗ
            РегистрНакопления.ТоварыНаСкладах КАК Движения
        ГДЕ
            Движения.Регистратор = &Регистратор
        """,
        {"Регистратор": adj_ref},
    )
    adj_sales = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Продажи.СуммаПродажи) КАК СуммаПродажи
        ИЗ
            РегистрНакопления.Продажи КАК Продажи
        ГДЕ
            Продажи.Регистратор = &Регистратор
        """,
        {"Регистратор": adj_ref},
    )
    adj_qty = float(adj_stock[0].Количество) if adj_stock and adj_stock[0].Количество is not None else 0
    adj_sale = float(adj_sales[0].СуммаПродажи) if adj_sales and adj_sales[0].СуммаПродажи is not None else 0
    tr.check(
        "Register adjustment movements",
        approx_equal(adj_qty, 1) and approx_equal(adj_sale, 80),
        f"stock_qty={adj_qty}, sale={adj_sale}",
    )

    # Reports data presence (query same sources as SKD)
    sales_period = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Продажи.КоличествоОборот) КАК Количество,
            СУММА(Продажи.СуммаПродажиОборот) КАК СуммаПродажи,
            СУММА(Продажи.СебестоимостьОборот) КАК Себестоимость
        ИЗ
            РегистрНакопления.Продажи.Обороты(&Начало, &Конец, , ) КАК Продажи
        """,
        {"Начало": dt(YEAR, 1, 1, 0, 0), "Конец": dt(YEAR, 1, 31, 23, 59)},
    )
    sales_qty = float(sales_period[0].Количество) if sales_period and sales_period[0].Количество is not None else 0
    tr.check("Report source Prodazhi has data", sales_qty > 0, f"qty={sales_qty}")

    stock_report = query_table(
        conn,
        """
        ВЫБРАТЬ
            СУММА(Остатки.КоличествоОстаток) КАК Количество
        ИЗ
            РегистрНакопления.ТоварыНаСкладах.Остатки(&Момент, ) КАК Остатки
        """,
        {"Момент": dt(YEAR, 1, 31)},
    )
    stock_rep_qty = float(stock_report[0].Количество) if stock_report and stock_report[0].Количество is not None else 0
    tr.check("Report source Ostatki has data", stock_rep_qty > 0, f"qty={stock_rep_qty}")

    # LIFO mini-scenario on separate item
    def fill_goods_b(obj, c):
        obj.ТипНоменклатуры = c.Перечисления.ТипыНоменклатуры.Товар

    goods_b = catalog_find_or_create(conn, "Номенклатура", f"Товар LIFO {tag}", fill_goods_b)
    set_policy(conn, dt(YEAR, 2, 1), "LIFO")
    create_receipt(conn, dt(YEAR, 2, 2), warehouse, supplier, [{"nomen": goods_b, "qty": 10, "price": 100}])
    create_receipt(conn, dt(YEAR, 2, 3), warehouse, supplier, [{"nomen": goods_b, "qty": 10, "price": 200}])
    ok_l, msg_l, exp_l = create_expense(
        conn,
        dt(YEAR, 2, 4),
        warehouse,
        buyer,
        [{"nomen": goods_b, "qty": 5, "price": 300}],
    )
    tr.check("LIFO expense posted", ok_l, msg_l)
    sales_l = query_table(
        conn,
        """
        ВЫБРАТЬ СУММА(Продажи.Себестоимость) КАК Себестоимость
        ИЗ РегистрНакопления.Продажи КАК Продажи
        ГДЕ Продажи.Регистратор = &Регистратор
        """,
        {"Регистратор": exp_l},
    )
    sebest_l = float(sales_l[0].Себестоимость) if sales_l else -1
    # LIFO: from party 2 (200) -> 5*200 = 1000
    tr.check("LIFO cost = 1000", approx_equal(sebest_l, 1000), f"sebest={sebest_l}")


def write_html_report(tr: TestRun, admin_msg: str) -> str:
    """Write HTML test report."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORT_DIR, f"ou_batch_test_report_{stamp}.html")
    passed, failed = tr.summary()
    rows_html = []
    for r in tr.results:
        color = "#28a745" if r["status"] == "PASS" else "#dc3545"
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(r['name'])}</td>"
            f"<td style='color:{color};font-weight:bold'>{r['status']}</td>"
            f"<td><pre>{html.escape(r['detail'])}</pre></td>"
            "</tr>"
        )

    body = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<title>OU Batch Accounting COM Tests</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #222; }}
h1 {{ color: #17a2b8; }}
.box {{ padding: 12px 16px; border-radius: 6px; margin: 12px 0; }}
.info {{ background: #e8f7fb; border-left: 4px solid #17a2b8; }}
.ok {{ background: #eaf7ee; border-left: 4px solid #28a745; }}
.fail {{ background: #fdeeee; border-left: 4px solid #dc3545; }}
.warn {{ background: #fff8e1; border-left: 4px solid #ffc107; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; text-align: left; }}
th {{ background: #f5f5f5; }}
pre {{ margin: 0; white-space: pre-wrap; font-family: Consolas, monospace; font-size: 12px; }}
</style>
</head>
<body>
<h1>Тестирование: ОУ партионный учет</h1>
<div class="box info">
<strong>Введение.</strong> Автоматический прогон экзаменационных сценариев через COM
(pywin32 / V83.COMConnector) в файловой ИБ OU_Training.
</div>

<h2>Технология</h2>
<div class="box info">
<p><strong>COM подключение</strong> — Component Object Model, библиотека pywin32,
объект <code>V83.COMConnector</code>.</p>
<p>Параметры: File, Usr, Pwd, App='PyCOM', Locale=ru_RU.</p>
<pre>File='C:\\1c\\Cursor_1c\\WORK\\OU_Training';Usr='Admin';Pwd='1';App='PyCOM';Locale=ru_RU;</pre>
<p>Примеры:</p>
<ul>
<li>Файловая база без пользователя (до создания Admin)</li>
<li>Файловая база Admin / 1</li>
<li>Запросы через NewObject("Запрос") и проведение документов РежимЗаписиДокумента.Проведение</li>
</ul>
</div>

<h2>Статистика</h2>
<div class="box {'ok' if failed == 0 else 'fail'}">
Passed: {passed} / {passed + failed}; Failed: {failed}<br/>
Admin: {html.escape(admin_msg)}<br/>
Time: {html.escape(datetime.now().isoformat(timespec='seconds'))}
</div>

<h2>Детали тестов</h2>
<table>
<thead><tr><th>Сценарий</th><th>Статус</th><th>Детали</th></tr></thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>

<h2>Возможности</h2>
<div class="box info">
Проверены: создание пользователя Admin, приходы с партиями, FIFO/LIFO/средняя,
услуги без склада, блокировка недостачи, корректировка регистров, источники отчетов.
</div>

<h2>Выводы</h2>
<div class="box {'ok' if failed == 0 else 'warn'}">
{"Все сценарии прошли успешно." if failed == 0 else "Есть ошибки — см. таблицу деталей."}
</div>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def main() -> int:
    pythoncom.CoInitialize()
    tr = TestRun()
    admin_msg = ""
    try:
        safe_print("=== Ensure Admin user ===")
        ok, admin_msg = ensure_admin_user()
        tr.check("Create Admin user", ok, admin_msg)
        if not ok:
            path = write_html_report(tr, admin_msg)
            safe_print(f"Report: {path}")
            return 1

        safe_print("=== Connect as Admin ===")
        conn = connect(USER_NAME, USER_PASSWORD)
        try:
            run_scenarios(conn, tr)
        finally:
            del conn

        passed, failed = tr.summary()
        path = write_html_report(tr, admin_msg)
        safe_print(f"=== Done: passed={passed} failed={failed} ===")
        safe_print(f"Report: {path}")
        return 0 if failed == 0 else 2
    except Exception:
        safe_print("FATAL:")
        safe_print(traceback.format_exc())
        tr.check("Fatal error", False, traceback.format_exc())
        path = write_html_report(tr, admin_msg or "n/a")
        safe_print(f"Report: {path}")
        return 3
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
