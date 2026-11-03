# -*- coding: utf-8 -*-
"""IMDEV-9746. Проверка ветки "нельзя изменять пороги подтвержденного лимита" в 1.16 и 1.17 (обычный ФО).

Временно: классу Compliance - расширенное подтверждение, первому лимиту с порогом эталона стенда - "Подтвержден".
По одному запуску каждой версии; затем признаки возвращаются. Ожидание: в обеих версиях порог этого лимита не записан,
у пары отказ (письмо с флагом FAIL), остальные пороги записаны.

    python confirmed_limit_test.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_versions as cv  # noqa: E402
import run_stand as rs  # noqa: E402


def set_attr(fo, ref, name, value):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "РеквизитОбъекта")
    p.Вставить("Ссылка", ref)
    p.Вставить("Реквизит", name)
    p.Вставить("Значение", value)
    return rs.checked(rs.scenario(fo, p, f"реквизит {name} = {value}", retry=True))["данные"].Было


def main():
    fo = rs.connect("wim_fo")
    rs.register(fo)
    klass = rs.limit_class(fo, "Compliance")
    limit = rs.mode_limits(fo, "o", "комплаенс")[0]
    log = rs.log
    log(f"лимит: {fo.String(limit)}")
    was_class = set_attr(fo, klass, "РасширенноеПодтверждение", True)
    was_limit = set_attr(fo, limit, "Подтвержден", True)
    try:
        for version in ("1.16", "1.17"):
            cv.run(fo, "o", version, 1)
    finally:
        set_attr(fo, limit, "Подтвержден", was_limit)
        set_attr(fo, klass, "РасширенноеПодтверждение", was_class)
        log(f"возвращено: класс {was_class}, лимит {was_limit}")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
