# -*- coding: utf-8 -*-
"""IMDEV-9746. Таблицы распределения времени операции на ПРОД по замерам стенда (results/runs.jsonl, bench.jsonl).

Стенд дает доли действий внутри шага "создание установок", ПРОД - итоги шагов (выгрузки ЗамерыВремени 16.10-02.11).
Перевод на ПРОД: письма - по стоимости письма на ПРОД (итоговое письмо по классу, замер ПРОД; на стенде почта уходит
в локальную заглушку), остальные действия - время стенда, умноженное на коэффициент k режима; k подбирается так, чтобы
сумма шага создания на пару совпала с ПРОД. Запись набора порогов обычного ФО делится на действия обработчиков по
медианам раскладки (bench) того же объема.

    python tables.py [объем_обычный] [объем_розница] [начало_серии_обычный]  -> results/tables.json и вывод таблиц
"""
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

# ПРОД 16.10-02.11.2026 (выгрузки ЗамерыВремени, см. Скрипты/analyze_zamery.py)
PROD = {
    "r": {"всего": 3827.7, "пар": 1878, "создание": 2879.0, "поиск": 540.3, "итоговое": 365.6, "писем_итоговых": 949,
          "вне_шагов": 42.8},
    "o": {"всего": 577.0, "пар": 20, "создание": 518.3, "поиск": 45.7, "итоговое": 8.2, "писем_итоговых": 21,
          "вне_шагов": 4.8},
}
SDV = {"r": ["ДатаАвтоустановки", "ЭталонныйПортфель", "ПризнакСтратегии", "ДатаРаспространения", "ЛимитыЗаведены"],
       "o": ["ДатаАвтоустановки", "ВнешнийКод", "ЭталонныйПортфель", "ПризнакСтратегии", "ДатаРаспространения",
             "ЛимитыЗаведены"]}


def load(name):
    path = os.path.join(RESULTS, name)
    return [json.loads(line) for line in open(path, encoding="utf-8")] if os.path.exists(path) else []


def per_pair(runs):
    """Сумма мс по ключам на одну пару; первый запуск серии исключается (прогрев после регистрации)."""
    runs = runs[1:]
    pairs = sum(r["замеры"]["СоздатьУстановкиЛимитов.Всего"][0] for r in runs)
    acc = {}
    for r in runs:
        for k, (n, ms) in r["замеры"].items():
            acc[k] = acc.get(k, 0) + ms
    return {k: v / pairs for k, v in acc.items()}, len(runs), pairs


def build(mode, volume, since=None):
    runs = [r for r in load("runs.jsonl") if r["режим"] == mode and r["объем"] == volume and not r["ошибка"]
            and (since is None or r["начало"] >= since)]
    if len(runs) < 2:
        raise SystemExit(f"{mode}:{volume}: запусков {len(runs)}")
    z, n_runs, pairs = per_pair(runs)
    g = lambda key: z.get(key, 0.0)  # noqa: E731
    p = PROD[mode]
    letter_prod = p["итоговое"] / p["писем_итоговых"] * 1000          # мс, одно письмо на ПРОД
    rows = {}
    rows["ДопСведения"] = sum(g("ДопСведения." + k) for k in SDV[mode])
    rows["Проведение"] = g("Создание.Проведение")
    rows["Запросы"] = g("Создание.ЗапросДействующих") + g("Создание.ЗапросПороговЭталона")
    rows["Лог"] = g("Создание.Макет") + g("Создание.СтрокаЛогаПорогов") + g("Создание.ЛогЛимитов")
    rows["ФайлXLS"] = g("Письмо.ФайлXLS")
    thresholds = g("Пороги.ЗаписьНабора")
    inner = (g("Создание.Проведение") + rows["Запросы"] + rows["Лог"] + thresholds + g("Письмо.ПоПаре") +
             g("Письмо.ОбУспешном") + sum(g("ДопСведения." + k) for k in ["ПризнакСтратегии", "ДатаРаспространения", "ЛимитыЗаведены"]))
    rows["Прочее"] = g("СоздатьУстановкиЛимитов.Всего") - inner
    letters_dev_smtp = g("Письмо.ПоПаре") - g("Письмо.ФайлXLS") + g("Письмо.ОбУспешном")
    n_letters = 1 + (1 if g("Письмо.ОбУспешном") else 0)
    if mode == "o":
        bench = [b for b in load("bench.jsonl") if b.get("объем") == volume and "образцы" in b][-1]
        med = {s: st.median([x["мс"] for x in bench["образцы"] if x["шаг"] == s])
               for s in dict.fromkeys(x["шаг"] for x in bench["образцы"])}
        parts = ["КэшНастроекЛимита", "ВерсияЛимита", "ЗафиксироватьПороги", "ПроверкиЗаписи", "ЗаписьБезОбработчиков"]
        total_parts = sum(med[s] for s in parts)
        for s in parts:
            rows["Пороги." + s] = thresholds * med[s] / total_parts
    else:
        rows["Пороги.ЗаписьБезОбработчиков"] = thresholds
    nonletter_dev = sum(rows.values())
    create_prod_ms = p["создание"] / p["пар"] * 1000
    k = (create_prod_ms - n_letters * letter_prod) / nonletter_dev
    prod_rows = {name: ms * k for name, ms in rows.items()}
    prod_rows["Письма.Отправка"] = n_letters * letter_prod
    result = {"режим": mode, "объем": volume, "запусков": n_runs, "пар": pairs, "k": round(k, 2),
              "письмо_прод_мс": round(letter_prod), "стенд_мс_на_пару": {n: round(v, 1) for n, v in rows.items()},
              "стенд_письма_smtp_мс_на_пару": round(letters_dev_smtp, 1),
              "прод_мс_на_пару": {n: round(v) for n, v in prod_rows.items()}}
    total_prod = p["всего"] * 1000
    share = {n: round(100 * v * p["пар"] / total_prod, 1) for n, v in prod_rows.items()}
    share["Поиск (замер ПРОД)"] = round(100 * p["поиск"] * 1000 / total_prod, 1)
    share["Итоговое письмо по классу (замер ПРОД)"] = round(100 * p["итоговое"] * 1000 / total_prod, 1)
    share["Вне шагов (замер ПРОД)"] = round(100 * p["вне_шагов"] * 1000 / total_prod, 1)
    result["доля_операции_прод"] = share
    result["доля_пары_стенд"] = {n: round(100 * v / (nonletter_dev + letters_dev_smtp), 1) for n, v in rows.items()}
    return result


def main():
    vol_o = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    vol_r = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    since_o = sys.argv[3] if len(sys.argv) > 3 else None
    out = {"o": build("o", vol_o, since_o), "r": build("r", vol_r)}
    with open(os.path.join(RESULTS, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for mode, t in out.items():
        print(f"== {mode}: объем {t['объем']}, запусков {t['запусков']}, пар {t['пар']}, k = {t['k']}, письмо ПРОД {t['письмо_прод_мс']} мс")
        for name, share in sorted(t["доля_операции_прод"].items(), key=lambda kv: -kv[1]):
            print(f"   {name:42} {share:5.1f}%  ПРОД {t['прод_мс_на_пару'].get(name, '-'):>6} мс/пару  "
                  f"стенд {t['стенд_мс_на_пару'].get(name, '-')}")


if __name__ == "__main__":
    main()
