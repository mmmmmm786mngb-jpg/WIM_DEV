#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка стенда U1: константа замеров, пробная запись и версия ФО.

Результат пишется в state.json. В консоль уходит только ASCII-статус.
"""

import sys

from stand_common import (
    CONSTANT_NAME,
    PROBE_KEY,
    connect,
    load_state,
    query_rows,
    save_state,
)

sys.stdout.reconfigure(encoding="utf-8")

TIMER_VERSION = (1, 4, 10, 3)


def version_tuple(text):
    parts = []
    for piece in str(text).split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if digits == "":
            break
        parts.append(int(digits))
    return tuple(parts)


def constant_manager(conn):
    return getattr(conn.Константы, CONSTANT_NAME)


def constant_value(conn):
    return bool(constant_manager(conn).Получить())


def set_constant(conn, value):
    constant_manager(conn).Установить(value)


def probe(conn):
    perf = conn.ОценкаПроизводительности
    started = perf.НачатьЗамерВремени()
    perf.ЗакончитьЗамерВремени(PROBE_KEY, started, 1, "probe")
    rows = query_rows(
        conn,
        """
        ВЫБРАТЬ
            Замеры.КлючеваяОперация.Имя КАК Имя
        ИЗ
            РегистрСведений.ЗамерыВремени КАК Замеры
        ГДЕ
            Замеры.КлючеваяОперация.Имя = &Имя
        """,
        {"Имя": PROBE_KEY},
    )
    return len(rows)


def main():
    state = load_state()
    state["bases"] = {}
    for base_id in ("wim_fo", "wim_mo"):
        conn = connect(base_id)
        previous = constant_value(conn)
        set_constant(conn, True)
        safe_mode = bool(conn.БезопасныйРежим())
        written = probe(conn)
        version = str(conn.Метаданные.Версия)
        state["bases"][base_id] = {
            "constant_was_on": previous,
            "constant_on": True,
            "safe_mode": safe_mode,
            "probe_rows": written,
            "version": version,
        }
        print("%s probe_rows=%s safe_mode=%s version=%s" % (base_id, written, safe_mode, version))
        if written < 1:
            print("FAIL probe wrote nothing on %s" % base_id)
            save_state(state)
            return 1

    fo_version = version_tuple(state["bases"]["wim_fo"]["version"])
    state["fo_timer_present"] = fo_version >= TIMER_VERSION
    state["fo_timer_basis"] = "configuration version compared with 1.4.10.3"
    save_state(state)
    print("fo_timer_present=%s" % state["fo_timer_present"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
