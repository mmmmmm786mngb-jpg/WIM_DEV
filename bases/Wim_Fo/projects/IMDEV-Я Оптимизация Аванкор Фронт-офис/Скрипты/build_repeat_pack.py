#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дополнительные лимиты FO_REP с повтором как в обычном ФО и в рознице.

Обычный ФО: много структурных лимитов с одним отбором и разными порогами
на всех портфелях одного набора.
Розница: короткий шаблон структуры, состава и поручений, одинаковый для портфелей.
Пред-контроль: несколько лимитов поручений с одним квалификатором.
"""

import os
import traceback

import build_shape_data as shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    conn = shape.connect()
    limit_class = conn.NewObject("Запрос")
    limit_class.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.КлассыЛимитов ГДЕ НЕ ПометкаУдаления"
    selection = limit_class.Выполнить().Выбрать()
    selection.Следующий()
    limit_class = selection.Ссылка
    dataset = shape.find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", "FO_SHAPE набор 482")
    order_dataset = shape.find_by_name(conn, "НаборыДанныхДляПроверкиЛимитов", "FO_SHAPE набор поручение")
    variant = shape.find_by_name(conn, "ВариантыПроверкиПороговЛимитов", "FO_SHAPE процент от РСА")
    if dataset is None or order_dataset is None or variant is None:
        raise RuntimeError("FO_SHAPE dataset or variant is missing")
    portfolios = []
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Портфели ГДЕ Наименование ПОДОБНО \"FO_SHAPE %\" "
        "УПОРЯДОЧИТЬ ПО Наименование"
    )
    selection = query.Выполнить().Выбрать()
    while selection.Следующий():
        portfolios.append(selection.Ссылка)
    refs = {
        "bond_rub": shape.kind_ref(conn, "ОблигацииГосРФ"),
        "bonds": shape.kind_ref(conn, "Облигации"),
        "receipts": shape.kind_ref(conn, "ДепозитарныеРасписки"),
        "tail_bond": shape.kind_ref(conn, "ОблигацииСубРФ"),
        "rub": shape.currency_ref(conn, "RUB"),
    }
    structure = conn.Перечисления.ВидыЛимитов.Структура
    composition = conn.Перечисления.ВидыЛимитов.Состав
    order_kind = conn.Перечисления.ВидыЛимитов.Поручение
    bond_rub = shape.pack_filter(conn, [("ВидАктива", "in", refs["bond_rub"]), ("ВалютаНоминала", "eq", refs["rub"])])
    bond_fx = shape.pack_filter(conn, [("ВидАктива", "in", refs["bonds"]), ("ВалютаНоминала", "ne", refs["rub"])])
    receipts = shape.pack_filter(conn, [("ВидАктива", "in", refs["receipts"])])
    tail_only = shape.pack_filter(conn, [("ВидАктива", "in", refs["tail_bond"])])
    order_bond = shape.pack_filter(conn, [("ВидАктива", "eq", refs["bond_rub"])])
    plan = []
    # Обычный ФО: 16 копий одного отбора ОФЗ, порог 85. Доля 70 и 10 оба проходят.
    for index in range(1, 17):
        plan.append(("FO_REP S%02d" % index, structure, dataset, bond_rub, False, 85))
    # Тот же отбор, более низкий порог: обычные портфели с 70 процентами нарушают.
    for index in range(17, 19):
        plan.append(("FO_REP S%02d" % index, structure, dataset, bond_rub, False, 50))
    # Валютные облигации: 6 копий порога 80 (все проходят) и 2 копии порога 20 (хвост нарушает).
    for index in range(19, 25):
        plan.append(("FO_REP S%02d" % index, structure, dataset, bond_fx, False, 80))
    for index in range(25, 27):
        plan.append(("FO_REP S%02d" % index, structure, dataset, bond_fx, False, 20))
    # Розничный состав: 4 одинаковых пустых и 2 одинаковых на хвостовой актив.
    for index in range(1, 5):
        plan.append(("FO_REP C%02d" % index, composition, dataset, receipts, True, None))
    for index in range(5, 7):
        plan.append(("FO_REP C%02d" % index, composition, dataset, tail_only, True, None))
    # Пред-контроль: 6 одинаковых квалификаторов без совпадения и 2 одинаковых на ОФЗ.
    for index in range(1, 7):
        plan.append(("FO_REP O%02d" % index, order_kind, order_dataset, receipts, True, None))
    for index in range(7, 9):
        plan.append(("FO_REP O%02d" % index, order_kind, order_dataset, order_bond, True, None))
    limits = []
    for name, kind, limit_dataset, packed_pair, qualifier, threshold in plan:
        packed, query_text = packed_pair
        use_variant = None if kind == order_kind else variant
        limits.append((
            shape.save_limit(conn, name, kind, limit_dataset, limit_class, use_variant, packed, query_text, qualifier),
            threshold,
            kind == structure,
        ))
        shape.safe_print("limit " + name)
    shape.ensure_thresholds(conn, limits)
    post_limits = [item[0] for item in limits if item[2] or " C" in conn.String(item[0])]
    order_limits = [item[0] for item in limits if " O" in conn.String(item[0])]
    # Имена уже отфильтрованы выше ненадежно для состава. Разложим по плану заново.
    post_limits = []
    order_limits = []
    for (limit_ref, _threshold, is_structure), (name, kind, _dataset, _pair, _qualifier, _threshold2) in zip(limits, plan):
        if kind == order_kind:
            order_limits.append(limit_ref)
        else:
            post_limits.append(limit_ref)
    shape.install_on(conn, portfolios, post_limits, limit_class, "post")
    shape.install_on(conn, portfolios[:50], order_limits, limit_class, "pre")
    note = os.path.join(ROOT, "Тестирование", "reports", "repeat_data.txt")
    with open(note, "w", encoding="utf-8") as handle:
        handle.write("\n".join([
            "FO_REP дополнительные данные",
            "Портфелей %s" % len(portfolios),
            "Структура: 16 лимитов один отбор ОФЗ порог 85, 2 лимита тот же отбор порог 50.",
            "Структура: 6 лимитов валютные облигации порог 80, 2 лимита порог 20.",
            "Состав: 4 одинаковых пустых, 2 одинаковых на субфедеральную облигацию.",
            "Поручения: 6 одинаковых без совпадения, 2 одинаковых на ОФЗ.",
            "Обычные портфели 001-080 держат 70 процентов ОФЗ и 5 процентов валютных облигаций.",
            "Хвост 081-100 держит 10 процентов ОФЗ и 60 процентов валютных облигаций.",
        ]))
    shape.safe_print(note)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        shape.safe_print(traceback.format_exc()[-2000:])
        raise
