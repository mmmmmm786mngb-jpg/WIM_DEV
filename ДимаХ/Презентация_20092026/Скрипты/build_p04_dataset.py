#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Датасет презентации 04: скорость операционного учёта 1С.

Это НЕ часы разработчика (презентация 02) и НЕ счета вендора (01).
Единица: длительность самой операции до/после оптимизации.

Источники: закрытые протоколы IMDEV-7330, IMDEV-9153, IMDEV-8663,
IMDEV-9393 (таблица ключевых операций), карточки перехода 01.04.2026
и совещания 28.04.2026. Утренний регламент ФО (IMDEV-8829) в набор
не входит: есть «было», нет закрытого «стало».
"""

import json
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPTS, "p04_dataset.json")


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def minutes(hours, mins, secs=0):
    return hours * 60.0 + mins + secs / 60.0


def x_of(before_min, after_min):
    return round(before_min / after_min, 1)


def build():
    ndfl_before = minutes(55, 5)
    ndfl_after = minutes(5, 32, 56)
    fee_before = minutes(9, 52)
    fee_after = minutes(1, 4, 34)
    eve_before = 118.0
    eve_after = 42.4
    load_before_per1000 = 20.0 / 0.9
    load_after_per1000 = 50.0 / 30.0
    exch_before_per1000 = minutes(4, 16) / 15.0
    exch_after_per1000 = minutes(1, 50) / 30.0
    t1_before = minutes(3, 36)
    t1_after = 45.0

    cases = [
        {
            "id": "ndfl",
            "hero": True,
            "contour": "ФИН",
            "key": "IMDEV-7330",
            "name": "Расчёт НДФЛ",
            "before_label": "55 ч 05 мин",
            "after_label": "5 ч 33 мин",
            "before_short": "55 ч",
            "after_short": "5,5 ч",
            "before_min": round(ndfl_before, 1),
            "after_min": round(ndfl_after, 1),
            "x": x_of(ndfl_before, ndfl_after),
            "x_head": "10",
            "volume": "27 292 клиента",
            "env": "DR, эталон 01-02.09.2026, релиз 2.8.5.5",
            "what": "Пакетные запросы, кэш НКД, параллель, снятие блокировок 1 222",
            "note": "Чистый расчёт. Стена с паузами: 6 ч 40 мин (x8,3).",
            "source": "imdev7330_ndfl_old_vs_new3_diff.html",
        },
        {
            "id": "fee",
            "hero": False,
            "contour": "ДУ",
            "key": "IMDEV-9153",
            "name": "Начисление вознаграждения РДУ",
            "before_label": "9 ч 52 мин",
            "after_label": "1 ч 05 мин",
            "before_short": "10 ч",
            "after_short": "1 ч",
            "before_min": round(fee_before, 1),
            "after_min": round(fee_after, 1),
            "x": x_of(fee_before, fee_after),
            "x_head": "9",
            "volume": "20 467 договоров",
            "env": "DR, параллельная версия, 12 потоков",
            "what": "Последовательный прогон заменён параллельным",
            "note": "Точно: 1 ч 04 мин 34 сек.",
            "source": "IMDEV-9393 KeyOperationsDuration",
        },
        {
            "id": "load",
            "hero": False,
            "contour": "ДУ",
            "key": "IMAPPS-34094",
            "name": "Загрузка сделок",
            "before_label": "22,2 мин / 1 000",
            "after_label": "1,67 мин / 1 000",
            "before_short": "22 мин",
            "after_short": "1,7 мин",
            "before_min": round(load_before_per1000, 2),
            "after_min": round(load_after_per1000, 2),
            "x": x_of(load_before_per1000, load_after_per1000),
            "x_head": "13",
            "volume": "было 900 сделок; стало 30 000",
            "env": "тест, 10 потоков, сопоставимо на 1 000 сделок",
            "what": "Параллельное создание документов",
            "note": "Доп. тест 100 000 сделок: 0,45 мин / 1 000. Не смешиваем объёмы.",
            "source": "карточки перехода 01.04.2026 / 28.04.2026",
            "norm": True,
        },
        {
            "id": "exchange",
            "hero": False,
            "contour": "МО / ФИН",
            "key": "обмен ДУ-Финансы 3.0",
            "name": "Обмен ДУ - Финансы",
            "before_label": "17,1 мин / 1 000",
            "after_label": "3,67 мин / 1 000",
            "before_short": "17 мин",
            "after_short": "3,7 мин",
            "before_min": round(exch_before_per1000, 2),
            "after_min": round(exch_after_per1000, 2),
            "x": x_of(exch_before_per1000, exch_after_per1000),
            "x_head": "5",
            "volume": "было 15 000; стало 30 000 сделок",
            "env": "многопоточный обмен 1+6 потоков",
            "what": "Параллельный обмен вместо одного потока",
            "note": "Было 4 ч 16 мин на 15 тыс. Стало 1 ч 50 мин на 30 тыс.",
            "source": "карточки совещания 28.04.2026",
            "norm": True,
        },
        {
            "id": "t1",
            "hero": False,
            "contour": "ДУ",
            "key": "исполнение сделок Т-1",
            "name": "Проведение сделок Т-1",
            "before_label": "3 ч 36 мин",
            "after_label": "45 мин",
            "before_short": "3,6 ч",
            "after_short": "45 мин",
            "before_min": round(t1_before, 1),
            "after_min": t1_after,
            "x": x_of(t1_before, t1_after),
            "x_head": "5",
            "volume": "30 000 сделок",
            "env": "тот же объём до и после, цель достигнута",
            "what": "Переписанные запросы проведения, потоки",
            "note": "7,2 мин / 1 000 стало 1,5 мин / 1 000.",
            "source": "карточки совещания 28.04.2026",
        },
    ]

    evening = {
        "id": "evening",
        "contour": "ДУ",
        "key": "IMDEV-8663",
        "name": "Вечерние регламенты / СЧА-РСА",
        "before_label": "118 мин",
        "after_label": "42 мин",
        "before_min": eve_before,
        "after_min": eve_after,
        "x": x_of(eve_before, eve_after),
        "volume": "полный объём базы",
        "env": "разработческая после оптимизации, IMDEV-8663.1",
        "what": "Фоновые задания, пакетный расчёт СЧА/РСА, вынос в конец",
        "alt": "Пакетный СЧА: 122 мин -> 69 мин на 21 993 договора (x1,8), регресс документов 0.",
        "source": "IMDEV-9393 + протокол IMDEV-8663 группа 3",
    }

    payload = {
        "title": "Окно то же. Клиентов больше.",
        "goal": "Скорость операционного учёта 1С при росте клиентской базы",
        "unit": "Длительность операции, не часы разработчика",
        "hero": cases[0],
        "cases": cases,
        "evening": evening,
        "ai": {
            "thesis": (
                "ИИ не лучше человека во всём. Если результат можно проверить "
                "(есть образец, секундомер, правильный ответ) - люди с ИИ быстрее "
                "и делают работу заметно качественнее. Если эталона нет - с ИИ "
                "ошибаются чаще, чем без него. Наши кейсы проверяемые: операция уже есть, "
                "замер до и после."
            ),
            "claims": [
                {
                    "src": "HBS / BCG, 2023",
                    "stat": "+25% / +40%",
                    "t": "Когда ответ можно проверить",
                    "d": (
                        "758 консультантов BCG работали с GPT-4. "
                        "На задачах с понятным эталоном: +25% к скорости, качество выше более чем на 40%. "
                        "На задачах без эталона верных ответов стало меньше, чем у коллег без ИИ."
                    ),
                    "map": "НДФЛ, СЧА, сделки: запрос уже работает, секундомер показывает, стало лучше или нет.",
                },
                {
                    "src": "McKinsey, июнь 2023",
                    "stat": "20-30%",
                    "t": "Существующий код, не система с нуля",
                    "d": (
                        "Эмпирика на Copilot: рефакторинг и оптимизация уже написанного кода - "
                        "на 20-30% меньше времени. Документация и чтение кода: 45-50%. "
                        "Инструмент силён, когда нужно объяснить и переписать модуль, а не придумать продукт."
                    ),
                    "map": "НДФЛ, СЧА, сделки - читать вендорский модуль и найти цикл.",
                },
                {
                    "src": "McKinsey, сложные задачи",
                    "stat": "<10%",
                    "t": "Там, где человек нужнее",
                    "d": (
                        "На очень сложных задачах экономия времени падает ниже 10%. "
                        "Это новая архитектура или работа без образца правильного ответа. "
                        "ИИ не заменяет приёмку замера. Он быстрее предлагает варианты запроса."
                    ),
                    "map": "Человек ставит цель и читает секундомер. ИИ перебирает пакет, кэш, потоки.",
                },
            ],
            "contrast": (
                "Исследования меряют часы разработчика. Презентация 02 - это 25% таких часов "
                "(McKinsey, рефакторинг). Здесь другой эффект: найденная правка сокращает "
                "саму операцию в 3-13 раз. Слепое принятие ответа ИИ здесь не проходит: "
                "замер отсекает ошибочную гипотезу."
            ),
            "cites": (
                "Dell'Acqua et al., Navigating the Jagged Technological Frontier, "
                "HBS Working Paper 24-013 / SSRN 4573321, 2023 (BCG, n=758). "
                "McKinsey, Unleashing developer productivity with generative AI, 27 июня 2023: "
                "refactoring 20-30%, documentation 45-50%, high-complexity <10%."
            ),
        },
        "out_of_scope": {
            "fo": "Утренний регламент ФО (IMDEV-8829, порядка 5 ч 30 мин) - тот же класс задач, окно к открытию торгов. Закрытого «стало» в протоколах нет, в пятёрку не входит.",
            "p02": "Часы Time Sheet по задачам «Оптимизировать ...» уже в презентации 02. Здесь только runtime операции.",
        },
        "sources": [
            {"who": "IMDEV-7330", "what": "НДФЛ: 55 ч 05 мин -> 5 ч 33 мин, 27 292 клиента"},
            {"who": "IMDEV-9153 / 9393", "what": "Вознаграждение РДУ: 9 ч 52 мин -> 1 ч 05 мин, 20 467 договоров"},
            {"who": "IMDEV-8663 / 9393", "what": "Вечерние: 118 мин -> 42 мин; пакет СЧА 122 -> 69 мин"},
            {"who": "Переход 01.04 / 28.04.2026", "what": "Загрузка сделок, обмен ДУ-Финансы, проведение Т-1"},
            {"who": "IMDEV-9393", "what": "26 273 замера ключевых операций PROD, сценарий 25 тыс. -> 250 тыс."},
        ],
    }
    return payload


def main():
    payload = build()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    safe_print("OK - p04 dataset: %d cases" % len(payload["cases"]))
    for c in payload["cases"]:
        safe_print("  %s  x%s  %s -> %s" % (
            c["id"], ("%.1f" % c["x"]).replace(".", ","),
            c["before_label"], c["after_label"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
