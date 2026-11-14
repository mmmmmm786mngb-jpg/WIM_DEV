#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Уборка дополнительных сведений контрагентов T5L5K фоновым заданием на ФО."""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "Тестирование", "stand"))
import stand_common as sc  # noqa: E402


def main():
    fo = sc.connect("wim_fo")
    epf = os.path.join(HERE, "build", "ЗагрузкаДопРеквизитаTCRIS.epf")
    state, error = sc.run_epf_method_bg(fo, epf, "УборкаДопСведенийНагрузки", timeout=600,
                                        job_key="T5L5CLEAN")
    print("state", state)
    if error:
        print(error[:800])
        raise SystemExit(1)
    left = sc.query_rows(
        fo,
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ РегистрСведений.ДополнительныеСведения КАК Св "
        "ГДЕ Св.Объект ССЫЛКА Справочник.Контрагенты "
        "И ВЫРАЗИТЬ(Св.Объект КАК Справочник.Контрагенты).Наименование ПОДОБНО &Маска",
        {"Маска": "T5L5K%"})
    print("осталось записей:", left[0]["К"])


if __name__ == "__main__":
    main()
