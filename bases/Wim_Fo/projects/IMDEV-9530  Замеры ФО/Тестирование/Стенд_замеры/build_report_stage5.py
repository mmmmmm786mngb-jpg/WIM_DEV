# -*- coding: utf-8 -*-
"""HTML-отчет о тестировании замеров этапа 5 IMDEV-9530 (внешние обработки загрузок) по results/stage5_<серия>.json.

    python build_report_stage5.py [серия]      по умолчанию S5
"""
import datetime
import glob
import html
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(TASK, "Тестирование", "Отчет о тестировании замеров, этап 5.html")
TZ = datetime.timedelta(hours=3)

DEP_ALL = "Депозитов ДУ/ПИФ/Calipso: 4/2/0"
DEP_POS = "Портфелей: 3; Обновлено: 4; Не найдено: 2"
IDX = "Индексов: 2; Записей: 2; Записей состава: 3; Источник: MICROAPI"


def expected(scenario, period):
    """Ожидаемые записи версии с замерами: [(ключ, вес, комментарий)]."""
    q_all = f"Котировок: 6; Активов: 5; Документов: 1; Период: {period} - {period}"
    q_read = f"Котировок: 6; Активов: 5; Период: {period} - {period}"
    q_write = "Котировок: 6; Активов: 5; Документов: 1"
    fill = ("ЗагрузкаДепозитов.ЗаполнитьДепозиты", 6, DEP_ALL)
    update = ("ЗагрузкаДепозитов.ОбновитьФактическуюПозицию", 3, DEP_POS)
    return {
        "Д.Успех": [("ЗагрузкаДепозитов", 3, f"{DEP_ALL}; {DEP_POS}"), fill, update],
        "Д.Рассылка": [fill, update],
        "Д.Сбой": [],
        "Д.Форма": [fill, update],
        "К.Успех": [("ЗагрузкаКотировокММВБ", 6, q_all), ("ЗагрузкаКотировокММВБ.Чтение", 6, q_read),
                    ("ЗагрузкаКотировокММВБ.Запись", 6, q_write)],
        "К.Сбой": [],
        "К.НеПроведен": [("ЗагрузкаКотировокММВБ.Чтение", 12, f"Котировок: 12; Активов: 10; Период: {period} - {period}")],
        "К.Форма": [("ЗагрузкаКотировокММВБ.Чтение", 6, q_read), ("ЗагрузкаКотировокММВБ.Запись", 6, q_write)],
        "И.Успех": [("ЗагрузкаИндексов", 2, IDX), ("ЗагрузкаИндексов.Чтение", 2, IDX), ("ЗагрузкаИндексов.Запись", 2, IDX)],
        "И.Сбой": [],
        "И.Форма": [("ЗагрузкаИндексов.Чтение", 2, IDX)],
        "T.Недоступна": [],
    }[scenario]


SCENARIO_TEXT = {
    "Д.Успех": ("Загрузка депозитов", "Команда регламентного задания: ДУ 4 депозита (1 без места хранения), ПИФ 2 (1 без места), "
                "Calipso недоступен; закрытый депозит в ФО; пересчет РСА - заглушка; рассылка не настроена"),
    "Д.Рассылка": ("Загрузка депозитов", "То же с настроенной рассылкой: системная учетная запись почты на dev не настроена, "
                   "отправка письма падает - сбой загрузки"),
    "Д.Сбой": ("Загрузка депозитов", "Сервисы ДУ и ПИФ недоступны, Calipso недоступен: ни одного депозита"),
    "Д.Форма": ("Загрузка депозитов", "Процедуры кнопок формы «Заполнить из внешних источников» и «Обновить позицию»"),
    "К.Успех": ("Котировки ММВБ", "Команда регламентного задания: сервис TIBCO вернул документ ММВБ (6 котировок, 1 тикер "
                "без бумаги) и документ другой биржи"),
    "К.Сбой": ("Котировки ММВБ", "Сервис TIBCO вернул ошибку (SOAP Fault)"),
    "К.НеПроведен": ("Котировки ММВБ", "Документы ММВБ на две даты; первый не проводится (запись регистра котировок на эту дату "
                     "и актив уже есть у документа другой биржи), записан без проведения; второй проведен"),
    "К.Форма": ("Котировки ММВБ", "Процедуры кнопок формы «Запрос к сервису» и «Загрузить»"),
    "И.Успех": ("Индексы", "Команда регламентного задания: MICROAPI вернул данные 2 индексов и состав 1 индекса "
                "(3 строки, 1 тикер без бумаги)"),
    "И.Сбой": ("Индексы", "MICROAPI вернул HTTP 500"),
    "И.Форма": ("Индексы", "Процедуры кнопок формы «Запрос к сервису» и «Загрузить» (форма записывает только данные индексов)"),
    "T.Недоступна": ("TCRIS", "База Rates с dev недоступна"),
}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def start_local(r):
    return datetime.datetime(1, 1, 1) + datetime.timedelta(milliseconds=r["начало_мс"]) + TZ


def norm_text(text):
    """Номера строк модуля сдвинуты вставками, номера документов состава индекса растут от прогона к прогону."""
    text = re.sub(r"\(\d+\)", "(N)", text or "")
    return re.sub(r"\b\d{9}\b", "N", text)


def norm_result(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def main():
    series = sys.argv[1] if len(sys.argv) > 1 else "S5"
    with open(os.path.join(HERE, "results", f"stage5_{series}.json"), encoding="utf-8") as f:
        state = json.load(f)
    # Записи других серий (S5BUG - воспроизведение замечания ревью) попадают в выборку по времени: исключаются по окнам
    # сценариев этих серий.
    foreign = []
    for path in glob.glob(os.path.join(HERE, "results", "stage5_*.json")):
        if os.path.basename(path) == f"stage5_{series}.json":
            continue
        with open(path, encoding="utf-8") as f:
            other = json.load(f)
        for run in other["runs"]:
            for sc in run["сценарии"]:
                foreign.append((datetime.datetime.fromisoformat(sc["начало"]) - datetime.timedelta(seconds=2),
                                datetime.datetime.fromisoformat(sc["конец"]), other["series"]))
    excluded = [r for r in state["measurements"] if any(a <= start_local(r) <= b for a, b, _ in foreign)]
    records = [r for r in state["measurements"] if r not in excluded]
    scenarios = []
    for run in state["runs"]:
        tag = "замеры выключены" if run["замеры_выключены"] else run["версия"]
        for sc in run["сценарии"]:
            sc = dict(sc)
            sc["тег"] = tag
            sc["от"] = datetime.datetime.fromisoformat(sc["начало"]) - datetime.timedelta(seconds=2)
            sc["до"] = datetime.datetime.fromisoformat(sc["конец"])
            sc["записи"] = []
            scenarios.append(sc)
    unassigned = []
    for r in records:
        hit = [sc for sc in scenarios if sc["от"] <= start_local(r) <= sc["до"]]
        (hit[0]["записи"] if hit else unassigned).append(r)

    quotes_ok = next(sc for sc in scenarios if sc["тег"] == "замеры" and sc["сценарий"] == "К.Успех")
    period = quotes_ok["результат"][0]["Дата"][:10] if quotes_ok["результат"] else ""

    # Сверка покрытия: каждый сценарий каждой версии
    cover, ok_checks, total_checks = [], 0, 0
    for sc in scenarios:
        exp = expected(sc["сценарий"], period) if sc["тег"] == "замеры" else []
        fact = {r["ключ"]: r for r in sc["записи"]}
        rows = []
        for key, weight, comment in exp:
            r = fact.get(key)
            ok = r is not None and abs(r["вес"] - weight) < 1e-9 and r["комментарий"] == comment and not r["ошибка"]
            got = f"вес {r['вес']:g}; {r['комментарий']}" if r else "записи нет"
            rows.append((key, f"вес {weight}; {comment}", got, ok))
        count_ok = len(sc["записи"]) == len(exp) and len(fact) == len(sc["записи"])
        rows.append(("число записей", str(len(exp)), str(len(sc["записи"])), count_ok))
        for row in rows:
            total_checks += 1
            ok_checks += row[3]
        cover.append((sc, rows))
    extra_keys = sorted({r["ключ"] for r in records} - {k for sc in scenarios if sc["тег"] == "замеры"
                                                     for k, _, _ in expected(sc["сценарий"], period)})

    # Сравнение результатов загрузок и поведения
    by = {(sc["тег"], sc["сценарий"]): sc for sc in scenarios}
    compare = []
    for name in SCENARIO_TEXT:
        o, m, off = by.get(("ориг", name)), by.get(("замеры", name)), by.get(("замеры выключены", name))
        if not o or not m:
            continue
        same_data = norm_result(o["результат"]) == norm_result(m["результат"])
        behavior = lambda sc: (sc["состояние"], norm_text(sc["ошибка_задания"].split("по причине")[-1]),
                               tuple(norm_text(x) for x in sc["сообщения"]))
        same_behavior = behavior(o) == behavior(m)
        compare.append((name, "оригинал и версия с замерами", same_data and same_behavior,
                        f"данные загрузки {'совпали' if same_data else 'расходятся'}; состояние задания, ошибка и сообщения "
                        f"{'совпали' if same_behavior else 'расходятся'}"))
        if off:
            same_off = norm_result(off["результат"]) == norm_result(m["результат"]) and behavior(off) == behavior(m)
            compare.append((name, "замеры выключены и версия с замерами", same_off and not off["записи"],
                            f"данные {'совпали' if same_off else 'расходятся'}; записей замеров {len(off['записи'])}"))
    compare_ok = all(c[2] for c in compare)
    orig_records = sum(len(sc["записи"]) for sc in scenarios if sc["тег"] == "ориг")
    off_records = sum(len(sc["записи"]) for sc in scenarios if sc["тег"] == "замеры выключены")

    # Ожидаемый результат загрузок (не зависит от версии)
    def result_check(sc):
        res, name = sc["результат"], sc["сценарий"]
        if name in ("Д.Успех", "Д.Рассылка", "Д.Форма"):
            places = sorted(p["Место"][-2:] for p in res["позиции"])
            rates = {r["Счет"][-2:]: r["Ставка"] for r in res["ставки"]}
            ok = places == ["01", "02", "03", "04"] and rates == {"01": 12.6, "02": 12.7, "03": 12.8, "04": 13.1, "05": 0}
            return ok, f"позиции мест 01-04 записаны, закрытый депозит 05 удален, ставки 12,6/12,7/12,8/13,1: {places}, {rates}"
        if name == "Д.Сбой":
            return not res["позиции"], f"позиций на дату нет (закрытый депозит удален и при пустом ответе источников): {len(res['позиции'])}"
        if name in ("К.Успех", "К.Форма"):
            ok = len(res) == 5 and all(r["Проведен"] for r in res)
            return ok, f"документ ММВБ на {period}: {len(res)} котировок тестовых бумаг, проведен"
        if name == "К.НеПроведен":
            first = [r for r in res if not r["Проведен"]]
            second = [r for r in res if r["Проведен"]]
            ok = len(first) == 5 and len(second) == 5 and first[0]["Дата"] < second[0]["Дата"]
            return ok, (f"документ на {first[0]['Дата'][:10] if first else '-'} записан без проведения ({len(first)} строк), "
                        f"на {second[0]['Дата'][:10] if second else '-'} проведен ({len(second)} строк)")
        if name == "К.Сбой":
            return not res, f"документов котировок нет: {len(res)}"
        if name == "И.Успех":
            ok = len(res["данные"]) == 2 and len(res["составы"]) == 2
            return ok, f"данных индексов {len(res['данные'])}, строк состава {len(res['составы'])} (тикер без бумаги не записан)"
        if name == "И.Форма":
            ok = len(res["данные"]) == 2 and not res["составы"]
            return ok, f"данных индексов {len(res['данные'])}, составов {len(res['составы'])} (кнопка пишет только данные)"
        if name == "И.Сбой":
            return not res["данные"] and not res["составы"], "данных и составов нет"
        return res.get("сведений_TCRIS") == 0, f"сведений TCRIS: {res.get('сведений_TCRIS')}; задание: {sc['состояние']}"
    results = [(sc["тег"], sc["сценарий"]) + result_check(sc) for sc in scenarios]
    results_ok = all(r[2] for r in results)

    all_ok = ok_checks == total_checks and compare_ok and results_ok and orig_records == 0 and off_records == 0 \
        and not unassigned and not extra_keys

    def mark(ok):
        return "<span class='tk ok'>&#10003;</span>" if ok else "<span class='tk bad'>&#10007;</span>"

    groups = {"Д": "Депозиты", "К": "Котировки ММВБ", "И": "Индексы", "T": "TCRIS"}
    cover_last = {(sc["тег"], sc["сценарий"]): all(r[3] for r in rows) for sc, rows in cover}
    cmp_by, res_by = {}, {}
    for a, _, ok, _ in compare:
        cmp_by.setdefault(a, []).append(ok)
    for _, n, ok, _ in results:
        res_by.setdefault(n, []).append(ok)

    matrix, current = [], None
    for name in SCENARIO_TEXT:
        if ("замеры", name) not in by:
            continue
        if groups[name[0]] != current:
            current = groups[name[0]]
            matrix.append(f"<tr class='grp'><td colspan='7'>{esc(current)}</td></tr>")
        m = by[("замеры", name)]
        exp = expected(name, period)
        chips = "".join(f"<span class='chip'>{esc(k.split('.', 1)[1] if '.' in k else 'общий')}<i>{w}</i></span>"
                        for k, w, _ in exp) or "<span class='muted'>не пишется</span>"
        o_cnt = sum(len(sc["записи"]) for sc in scenarios if sc["тег"] == "ориг" and sc["сценарий"] == name)
        off = by.get(("замеры выключены", name))
        off_cell = f"{mark(not off['записи'])}<span class='num'>{len(off['записи'])}</span>" if off else "<span class='muted'>-</span>"
        main = [r for r in m["записи"] if "." not in r["ключ"]]
        dur = f"{main[0]['время_с']:.2f}" if main else "<span class='muted'>-</span>"
        data_ok = all(cmp_by.get(name, [False])) and all(res_by.get(name, [True]))
        matrix.append(
            f"<tr><td><span class='code'>{esc(name)}</span><div class='sub'>{esc(SCENARIO_TEXT[name][1])}</div></td>"
            f"<td>{chips}</td>"
            f"<td class='c'>{mark(cover_last[('замеры', name)])}<span class='num'>{len(m['записи'])}/{len(exp)}</span></td>"
            f"<td class='c'>{mark(o_cnt == 0)}<span class='num'>{o_cnt}</span></td><td class='c'>{off_cell}</td>"
            f"<td class='c'>{mark(data_ok)}</td><td class='n'>{dur}</td></tr>")

    cov_html = []
    for sc, rows in cover:
        for i, (key, exp_text, got, ok) in enumerate(rows):
            head = f"<span class='code'>{esc(sc['сценарий'])}</span> <span class='muted'>{esc(sc['тег'])}</span>" if i == 0 else ""
            cov_html.append(f"<tr><td>{head}</td><td><code>{esc(key)}</code></td><td>{esc(exp_text)}</td>"
                            f"<td>{esc(got)}</td><td class='c'>{mark(ok)}</td></tr>")
    cmp_html = "".join(f"<tr><td><span class='code'>{esc(a)}</span> <span class='muted'>{esc(SCENARIO_TEXT[a][0])}</span></td>"
                       f"<td>{esc(b)}</td><td class='c'>{mark(ok)}</td><td>{esc(c)}</td></tr>" for a, b, ok, c in compare)
    res_html = "".join(f"<tr><td><span class='code'>{esc(n)}</span> <span class='muted'>{esc(t)}</span></td>"
                       f"<td class='c'>{mark(ok)}</td><td>{esc(c)}</td></tr>" for t, n, ok, c in results)
    proto = []
    for sc in scenarios:
        err = sc["ошибка_задания"].split("по причине:")[-1].strip().split("\n")[0][:200] if sc["ошибка_задания"] else ""
        msgs = "; ".join(x[:140] for x in sc["сообщения"][:3])
        main = [r for r in sc["записи"] if "." not in r["ключ"]]
        proto.append(f"<tr><td><span class='code'>{esc(sc['сценарий'])}</span> <span class='muted'>{esc(sc['тег'])}</span></td>"
                     f"<td class='n'>{sc['длительность_с']:.1f}</td><td class='n'>{main[0]['время_с']:.2f}</td>" if main else
                     f"<tr><td><span class='code'>{esc(sc['сценарий'])}</span> <span class='muted'>{esc(sc['тег'])}</span></td>"
                     f"<td class='n'>{sc['длительность_с']:.1f}</td><td class='n'><span class='muted'>-</span></td>")
        proto[-1] += (f"<td class='n'>{len(sc['записи'])}</td><td>{esc(sc['состояние'])}</td>"
                      f"<td class='small'>{esc(err)}</td><td class='small muted'>{esc(msgs)}</td></tr>")
    raw = "".join(
        f"<tr data-k><td class='n'>{esc(start_local(r).strftime('%d.%m %H:%M:%S.%f')[:-3])}</td><td class='n'>{r['сеанс']}</td>"
        f"<td><code>{esc(r['ключ'])}</code></td><td class='n'>{r['время_с']:.3f}</td><td class='n'>{r['вес']:g}</td>"
        f"<td class='small'>{esc(r['комментарий'])}</td></tr>"
        for r in sorted(records, key=lambda x: x["начало_мс"]))
    keys = Counter(r["ключ"] for r in records)

    def step_time(name, key):
        sc = by.get(("замеры", name))
        r = [x for x in (sc["записи"] if sc else []) if x["ключ"] == key]
        return f"{r[0]['время_с']:.1f}" if r else "-"

    findings = [
        ("fix", "Исправлено по ревью", "Котировки: непроведенный документ",
         "Обработка сбрасывает <code>Отказ</code> перед каждым документом: если не провелся документ в середине загрузки, "
         "итоговый <code>Отказ</code> - <code>Ложь</code>. Первая сборка 1.03 в этом случае писала шаг записи и общий замер "
         f"(серия S5BUG, {len(excluded)} записи). Исправлено счетчиком <code>ПоказателиЗамера.Непроведенных</code>, строка "
         "<code>Отказ = Ложь</code> не тронута; сценарии котировок повторены на исправленной сборке."),
        ("orig", "Оригинал", "Депозиты: пустой ответ источников",
         "Если ни один источник не вернул депозиты, обработка удаляет все позиции депозитов ФО за дату загрузки "
         "(сценарий Д.Сбой). Замеры в этом случае не пишутся."),
        ("orig", "Оригинал", "Котировки: «Успех!» при непроведенном документе",
         "Если не провелся документ в середине загрузки, а следующий провелся, обработка пишет в журнал «Успех!». "
         "Непроведенный документ виден только в сообщении «Не удалось провести»."),
        ("orig", "Оригинал", "TCRIS: ошибка задания при недоступной Rates",
         "После ошибок подключения обработка передает в запрос сопоставления <code>Неопределено</code> и падает на "
         "«Неверные параметры ВходнаяТЗ». Так ведут себя обе версии; замеры не пишутся."),
        ("orig", "Оригинал", "Учетные данные в коде",
         "В обработках депозитов и TCRIS логины и пароли SQL Server (Rates, MasterData) и пароль веб-сервисов в настройках "
         "по умолчанию заданы в коде. Код не менялся, передать владельцу."),
        ("info", "Время шагов", "Депозиты: где уходит время",
         f"Получение депозитов {step_time('Д.Успех', 'ЗагрузкаДепозитов.ЗаполнитьДепозиты')} с: почти все - тайм-аут подключения "
         f"к Calipso (15 с), с dev недоступен. Обновление позиции {step_time('Д.Успех', 'ЗагрузкаДепозитов.ОбновитьФактическуюПозицию')} с: "
         "из них 10 с - пауза <code>АванкорВыполнениеРегламентныхЗаданий.Пауза(10)</code> перед постановкой рассылки по пересчету РСА."),
        ("info", "Поведение", "Вызов с формы и ошибка письма",
         "С формы пишутся только шаги (у индексов кнопка «Загрузить» пишет только данные - есть только шаг чтения). При ошибке "
         "отправки письма шаги получения и обновления остаются, общий замер и шаг рассылки не пишутся."),
        ("dev", "Ограничение dev", "Проверяется на тестовой копии",
         "Calipso, шаг <code>ЗагрузкаДепозитов.Рассылка</code> при отправленном письме, TCRIS с записью сведений, реальные "
         "сервисы TIBCO и MICROAPI, ветка TIBCO у индексов."),
    ]
    find_html = "".join(f"<div class='fc {kind}'><div class='ft'><span class='tag {kind}'>{esc(tag)}</span></div>"
                        f"<h4>{esc(title)}</h4><p>{text}</p></div>" for kind, tag, title, text in findings)
    run_dates = sorted({sc["начало"][:10] for sc in scenarios})
    run_date = datetime.date.fromisoformat(run_dates[-1]).strftime("%d.%m.%Y") if run_dates else ""

    page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тест замеров этапа 5</title>
<style>
:root {{ --bg:#f5f6f8; --surface:#ffffff; --ink:#0f172a; --ink2:#475569; --muted:#94a3b8; --line:#e6e9ef; --soft:#f1f4f8;
  --brand:#4f46e5; --brand-soft:#eef2ff; --ok:#059669; --ok-soft:#ecfdf5; --bad:#dc2626; --bad-soft:#fef2f2;
  --warn:#d97706; --warn-soft:#fffbeb; --info:#0284c7; --info-soft:#f0f9ff; --code:#f1f4f8; --shadow:0 1px 2px rgba(15,23,42,.05); }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#0b0f17; --surface:#121826; --ink:#e5e9f0;
  --ink2:#a3adbf; --muted:#6b7689; --line:#222b3b; --soft:#182033; --brand:#818cf8; --brand-soft:#1e1b4b; --ok:#34d399;
  --ok-soft:#06281e; --bad:#f87171; --bad-soft:#2a1012; --warn:#fbbf24; --warn-soft:#2a1d06; --info:#38bdf8; --info-soft:#082236;
  --code:#1b2436; --shadow:none; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:13px/1.5 Inter,"Segoe UI Variable","Segoe UI",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:1280px; margin:0 auto; padding:24px 20px 40px; }}
header {{ display:flex; flex-wrap:wrap; gap:12px 24px; align-items:flex-end; justify-content:space-between; margin-bottom:18px; }}
.eyebrow {{ font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--brand); }}
h1 {{ margin:4px 0 2px; font-size:22px; font-weight:650; letter-spacing:-.01em; }}
.meta {{ color:var(--ink2); }}
.status {{ display:inline-flex; align-items:center; gap:8px; padding:8px 14px; border-radius:999px; font-weight:600;
  background:{'var(--ok-soft)' if all_ok else 'var(--bad-soft)'}; color:{'var(--ok)' if all_ok else 'var(--bad)'}; }}
.status::before {{ content:""; width:8px; height:8px; border-radius:50%; background:currentColor; }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:18px; }}
.kpi {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:12px 14px; box-shadow:var(--shadow); }}
.kpi .l {{ font-size:11px; color:var(--ink2); text-transform:uppercase; letter-spacing:.05em; }}
.kpi .v {{ font-size:22px; font-weight:650; margin-top:2px; font-variant-numeric:tabular-nums; }}
.kpi .v small {{ font-size:13px; color:var(--muted); font-weight:500; }}
.kpi.good .v {{ color:var(--ok); }}
section {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; margin-bottom:14px; box-shadow:var(--shadow); overflow:hidden; }}
.sh {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; padding:14px 16px 10px; }}
.sh h2 {{ margin:0; font-size:14px; font-weight:650; }} .sh p {{ margin:0; color:var(--ink2); max-width:760px; }}
.tw {{ overflow:auto; }}
table {{ border-collapse:collapse; width:100%; }}
th {{ text-align:left; font-size:11px; font-weight:600; color:var(--ink2); text-transform:uppercase; letter-spacing:.04em;
  padding:8px 12px; background:var(--soft); border-top:1px solid var(--line); border-bottom:1px solid var(--line); white-space:nowrap; }}
td {{ padding:8px 12px; border-bottom:1px solid var(--line); vertical-align:top; }}
tr:last-child td {{ border-bottom:0; }}
tbody tr:hover td {{ background:var(--soft); }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td.c {{ text-align:center; white-space:nowrap; }}
tr.grp td {{ background:var(--soft); font-size:11px; font-weight:650; text-transform:uppercase; letter-spacing:.05em; color:var(--ink2); padding:6px 12px; }}
.sub {{ color:var(--ink2); font-size:12px; margin-top:2px; max-width:520px; }}
.small {{ font-size:12px; }} .muted {{ color:var(--muted); }}
.code, code {{ font-family:"JetBrains Mono",Consolas,monospace; font-size:12px; }}
code {{ background:var(--code); padding:1px 5px; border-radius:5px; }}
.code {{ font-weight:600; }}
.chip {{ display:inline-flex; align-items:center; gap:5px; margin:0 4px 4px 0; padding:2px 8px; border-radius:999px;
  background:var(--brand-soft); color:var(--brand); font-size:11.5px; font-weight:550; white-space:nowrap; }}
.chip i {{ font-style:normal; color:var(--ink2); font-weight:500; }}
.tk {{ display:inline-grid; place-items:center; width:18px; height:18px; border-radius:50%; font-size:11px; font-weight:700; margin-right:6px; }}
.tk.ok {{ background:var(--ok-soft); color:var(--ok); }} .tk.bad {{ background:var(--bad-soft); color:var(--bad); }}
.num {{ font-variant-numeric:tabular-nums; color:var(--ink2); }}
.ver {{ font-variant-numeric:tabular-nums; white-space:nowrap; }} .ver b {{ color:var(--brand); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:10px; padding:0 16px 16px; }}
.fc {{ border:1px solid var(--line); border-radius:12px; padding:12px 14px; border-left:3px solid var(--muted); }}
.fc.fix {{ border-left-color:var(--ok); }} .fc.orig {{ border-left-color:var(--warn); }} .fc.info {{ border-left-color:var(--info); }}
.fc.dev {{ border-left-color:var(--muted); }}
.fc h4 {{ margin:6px 0 4px; font-size:13px; font-weight:650; }} .fc p {{ margin:0; color:var(--ink2); }}
.tag {{ font-size:10.5px; font-weight:650; text-transform:uppercase; letter-spacing:.05em; padding:2px 8px; border-radius:999px; }}
.tag.fix {{ background:var(--ok-soft); color:var(--ok); }} .tag.orig {{ background:var(--warn-soft); color:var(--warn); }}
.tag.info {{ background:var(--info-soft); color:var(--info); }} .tag.dev {{ background:var(--soft); color:var(--ink2); }}
details {{ border-top:1px solid var(--line); }} details:first-of-type {{ border-top:0; }}
summary {{ cursor:pointer; list-style:none; padding:12px 16px; font-weight:600; display:flex; justify-content:space-between; gap:12px; }}
summary::-webkit-details-marker {{ display:none; }}
summary::after {{ content:"+"; color:var(--muted); font-weight:500; }} details[open] summary::after {{ content:"\\2212"; }}
summary span {{ color:var(--ink2); font-weight:500; }}
.scroll {{ max-height:520px; overflow:auto; }}
.filter {{ margin:0 16px 10px; padding:7px 10px; border:1px solid var(--line); border-radius:8px; width:min(420px,calc(100% - 32px));
  background:var(--surface); color:var(--ink); font:inherit; }}
ul.plain {{ margin:0; padding:0 16px 14px 34px; color:var(--ink2); }} ul.plain li {{ margin:3px 0; }}
.note {{ padding:0 16px 14px; color:var(--ink2); }}
@media (max-width:640px) {{ .wrap {{ padding:16px; }} h1 {{ font-size:19px; }} }}
</style></head><body><div class="wrap">
<header><div><div class="eyebrow">IMDEV-9530 · Этап 5 · Отчет о тестировании</div>
<h1>Замеры внешних обработок загрузок</h1>
<div class="meta">Разработческая база ФО WIN_FO_server · серия {esc(series)} · {esc(run_date)} · оригинал и версия с замерами на одинаковом исходном состоянии</div></div>
<div class="status">{'Все проверки пройдены' if all_ok else 'Есть непройденные проверки'}</div></header>

<div class="kpis">
<div class="kpi {'good' if ok_checks == total_checks else ''}"><div class="l">Сверка замеров</div><div class="v">{ok_checks}<small>/{total_checks}</small></div></div>
<div class="kpi {'good' if compare_ok else ''}"><div class="l">Результат загрузки совпал</div><div class="v">{sum(1 for c in compare if c[2])}<small>/{len(compare)}</small></div></div>
<div class="kpi"><div class="l">Записей замеров</div><div class="v">{len(records)}</div></div>
<div class="kpi"><div class="l">Ключей</div><div class="v">{len(keys)}</div></div>
<div class="kpi {'good' if orig_records == 0 else ''}"><div class="l">Записей у оригинала</div><div class="v">{orig_records}</div></div>
<div class="kpi {'good' if off_records == 0 else ''}"><div class="l">Записей при выкл. замерах</div><div class="v">{off_records}</div></div>
</div>

<section><div class="sh"><h2>Обработки</h2><p>Простой замер БСП; при сбое загрузки замер не пишется. Каждая вставка помечена комментарием <code>IMDEV-9530</code>.</p></div>
<div class="tw"><table><thead><tr><th>Строка</th><th>Обработка</th><th>Версия</th><th>Ключи</th><th>Вес</th></tr></thead><tbody>
<tr><td class="n">9</td><td>Загрузка депозитов<div class="sub">внЗагрузкаДепозитовИзВнешнихИсточников.epf</div></td><td class="ver">1.18 &rarr; <b>1.19</b></td>
<td><span class="chip">ЗагрузкаДепозитов</span><span class="chip">.ЗаполнитьДепозиты</span><span class="chip">.ОбновитьФактическуюПозицию</span><span class="chip">.Рассылка</span></td><td class="small">портфели с обновленной позицией; получение - депозиты</td></tr>
<tr><td class="n">10</td><td>Котировки ММВБ<div class="sub">внЗагрузкаКотировокММВБ.epf</div></td><td class="ver">1.02 &rarr; <b>1.03</b></td>
<td><span class="chip">ЗагрузкаКотировокММВБ</span><span class="chip">.Чтение</span><span class="chip">.Запись</span></td><td class="small">котировки к загрузке</td></tr>
<tr><td class="n">11</td><td>Индексы<div class="sub">внЗагрузкаИндексовФО.epf</div></td><td class="ver">1.03 &rarr; <b>1.04</b></td>
<td><span class="chip">ЗагрузкаИндексов</span><span class="chip">.Чтение</span><span class="chip">.Запись</span></td><td class="small">записи данных индексов</td></tr>
<tr><td class="n">12</td><td>TCRIS<div class="sub">ЗагрузкаДопРеквизитаTCRIS.epf</div></td><td class="ver">1.01 &rarr; <b>1.02</b></td>
<td><span class="chip">ЗагрузкаTCRIS</span><span class="chip">.ЧтениеRates</span><span class="chip">.Сопоставление</span><span class="chip">.Запись</span></td><td class="small">контрагенты с записанным TCRIS</td></tr>
</tbody></table></div></section>

<section><div class="sh"><h2>Сценарии</h2><p>Ожидаемые записи версии с замерами (шаг и вес) и результат по каждому прогону. Общий замер, с - время общей записи.</p></div>
<div class="tw"><table><thead><tr><th>Сценарий</th><th>Ожидаемые записи</th><th>С замерами</th><th>Оригинал</th><th>Выкл. замеры</th><th>Данные</th><th>Общий, с</th></tr></thead>
<tbody>{''.join(matrix)}</tbody></table></div></section>

<section><div class="sh"><h2>Что показал тест</h2></div><div class="grid">{find_html}</div></section>

<section>
<details><summary>Детальная сверка замеров <span>{ok_checks}/{total_checks} · ключ, вес, комментарий, число записей</span></summary>
<div class="tw scroll"><table><thead><tr><th>Прогон</th><th>Ключ</th><th>Ожидалось</th><th>Факт</th><th></th></tr></thead><tbody>{''.join(cov_html)}</tbody></table></div>
{'<div class="note">Лишние ключи: ' + esc(extra_keys) + '</div>' if extra_keys else ''}
{'<div class="note">Записи вне сценариев: ' + str(len(unassigned)) + '</div>' if unassigned else ''}
{'<div class="note">Из выборки исключены записи серии воспроизведения S5BUG (' + str(len(excluded)) + ').</div>' if excluded else ''}
</details>
<details><summary>Сравнение результата загрузки <span>данные, состояние задания, ошибки и сообщения</span></summary>
<div class="note">Номера строк модуля в текстах ошибок (сдвинуты вставками) и номера новых документов состава индекса не сравниваются.</div>
<div class="tw"><table><thead><tr><th>Сценарий</th><th>Что сравнивалось</th><th></th><th>Подробно</th></tr></thead><tbody>{cmp_html}</tbody></table></div>
</details>
<details><summary>Ожидаемый результат загрузок <span>по каждому прогону</span></summary>
<div class="tw scroll"><table><thead><tr><th>Прогон</th><th></th><th>Подробно</th></tr></thead><tbody>{res_html}</tbody></table></div>
</details>
<details><summary>Протокол прогонов <span>{len(scenarios)} прогонов</span></summary>
<div class="tw scroll"><table><thead><tr><th>Прогон</th><th>Задание, с</th><th>Общий, с</th><th>Записей</th><th>Состояние</th><th>Ошибка задания</th><th>Сообщения</th></tr></thead><tbody>{''.join(proto)}</tbody></table></div>
</details>
<details><summary>Стенд и тестовые данные <span>что осталось в разработческой базе</span></summary>
<ul class="plain">
<li>Перед каждым сценарием данные загрузок возвращались в одно исходное состояние, после сценария снимался результат. Команды
запускались как регламентное задание (<code>ДополнительныеОтчетыИОбработки.ВыполнитьКоманду</code> в фоновом задании), вызовы с
формы - серверными вызовами процедур обработки.</li>
<li>Внешние источники заменены заглушками: веб-сервисы ДУ и ПИФ, TIBCO котировок (WSDL из макета обработки), MICROAPI индексов.
Адреса TIBCO и MICROAPI заданы в коде обработок: на время теста имена серверов направлены на заглушку через hosts.</li>
<li>Акции «T9530Z Акция T9530ZQ01..05» с тикерами на ММВБ, индексы T9530ZIX1, T9530ZIX2, портфели T9530ZD1, T9530ZD2, T9530ZP1,
депозитные счета «T9530Z депозит 01..05» с местами хранения, субпортфелями и свойством «ИдентификаторДепозита».</li>
<li>Остаются позиции депозитов тестовых субпортфелей, ставки тестовых счетов, документы котировок и составов тестовых индексов
(предыдущие помечены на удаление), данные тестовых индексов.</li>
<li>Тестовая обработка «T9530 тест обработок РОСТ» 1.1: сброс данных загрузок, вызов процедур как с формы, заглушка пересчета РСА,
конфликт проведения котировок. Константа «Выполнять замеры производительности» выключалась на один прогон и возвращена.</li>
<li>Обработки загрузок зарегистрированы на dev в версии с замерами и тестовыми настройками.</li>
</ul></details>
<details><summary>Все записи регистра «Замеры времени» <span>{len(records)} записей</span></summary>
<input class="filter" id="f" type="search" placeholder="Фильтр по ключу или комментарию">
<div class="tw scroll"><table id="raw"><thead><tr><th>Начало</th><th>Сеанс</th><th>Ключ</th><th>Время, с</th><th>Вес</th><th>Комментарий</th></tr></thead><tbody>{raw}</tbody></table></div>
<div class="note">Источник: results\\stage5_{esc(series)}.json; время - местное время сервера ФО.</div>
</details>
</section>
</div>
<script>
document.getElementById("f").addEventListener("input", function () {{
  var q = this.value.toLowerCase();
  document.querySelectorAll("#raw tr[data-k]").forEach(function (tr) {{
    tr.style.display = !q || tr.textContent.toLowerCase().indexOf(q) !== -1 ? "" : "none"; }});
}});
</script></body></html>"""

    for ch in ("—", "–", "ё", "Ё"):
        page = page.replace(ch, {"—": "-", "–": "-", "ё": "е", "Ё": "Е"}[ch])
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(OUT)
    print(f"покрытие {ok_checks}/{total_checks}, записей при оригинале {orig_records}, при выключенных {off_records}, "
          f"вне сценариев {len(unassigned)}, лишних ключей {len(extra_keys)}, сравнение {'ок' if compare_ok else 'РАСХОЖДЕНИЕ'}, "
          f"результаты {'ок' if results_ok else 'НЕ ОК'}")
    for sc, rows in cover:
        for key, exp, got, ok in rows:
            if not ok:
                print("  НЕ СОВПАЛО:", sc["тег"], sc["сценарий"], key, "|", exp, "|", got)
    for c in compare:
        if not c[2]:
            print("  СРАВНЕНИЕ:", c)
    for r in results:
        if not r[2]:
            print("  РЕЗУЛЬТАТ:", r)


if __name__ == "__main__":
    main()
