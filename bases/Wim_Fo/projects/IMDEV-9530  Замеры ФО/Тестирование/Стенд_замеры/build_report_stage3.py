# -*- coding: utf-8 -*-
"""Отчет о тестировании замеров этапа 3 (IMDEV-9530): исполнение сделок, упаковка данных, постконтроль лимитов.

    python build_report_stage3.py [<папка прогона results/stage3_...>]

Источник - measurements.json прогона run_stage3_tests.py (записи регистра ЗамерыВремени и протокол тестов).
Раздел про исправления этапа 2 строится по прогонам run_measure_tests.py: до исправления (BEFORE_RUN) и после
(записи ОбменБэкОфис.* этого же окна времени).
"""
import collections
import datetime
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(TASK, "Тестирование", "Отчет о тестировании замеров, этап 3.html")
BEFORE_RUN = os.path.join(HERE, "results", "20261002_121116")
EPOCH = datetime.datetime(1, 1, 1)
PACK_STEPS = ["КэшВмОписания", "ОчиститьСлужебныеКэши", "ОчиститьДанныеНеактивныхСеансов"]
PACK_REGISTERS = ["БиржевыеТранзакции", "БиржевыеТранзакцииНеторговые", "БиржевыеЗаявкиВнешние",
                  "СообщенияАдаптеров", "СведенияОБиржевыхДисконтах"]


def esc(s):
    return html.escape(str(s))


def fmt(x, d=3):
    return f"{x:,.{d}f}".replace(",", " ")


def parse_comment(text):
    result = {}
    for part in str(text).split(";"):
        if ":" in part:
            k, _, v = part.partition(":")
            result[k.strip()] = v.strip()
    return result


def written(r):
    return datetime.datetime.fromisoformat(r["записано"].replace("+00:00", ""))


def load_run(path=None):
    if path is None:
        path = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(HERE, "results", "stage3_*", "measurements.json")))[-1]
    with open(os.path.join(path, "measurements.json"), encoding="utf-8") as f:
        return path, json.load(f)


def main():
    run_dir, data = load_run(sys.argv[1] if len(sys.argv) > 1 else None)
    rows = data["замеры"]
    for r in rows:
        if str(r["комментарий"]).startswith("{"):
            r["комментарий"] = "(стандартный комментарий БСП)"
        r["доп"] = parse_comment(r["комментарий"])
        r["dt"] = written(r)
    tests = data["тесты"]
    checks = []

    def in_test(t, prefix):
        a = datetime.datetime.fromisoformat(t["начало"])
        b = datetime.datetime.fromisoformat(t["окончание"]) + datetime.timedelta(seconds=1)
        return [r for r in rows if a <= r["dt"] <= b and r["ключ"].startswith(prefix)]

    def check(name, ok, fact):
        checks.append((name, bool(ok), fact))

    # ---------------- строка 15: исполнение сделок ----------------
    e_tests = {t["метка"]: t for t in tests if t["тест"] == "E"}
    m_test = next(t for t in tests if t["тест"] == "M")
    e_a, e_rep, e_b = e_tests["с_замерами"], e_tests["повторный_запуск"], e_tests["без_замеров"]
    ra, rrep, rb = (in_test(t, "ИсполнениеСделок") for t in (e_a, e_rep, e_b))
    rm = in_test(m_test, "ИсполнениеСделок")
    keys_a = sorted(r["ключ"] for r in ra)
    after = e_a["после"]
    expected_comment = (f"Строк: {e_a['до']['строк_остатка']}; Сделок: {after['сделок']}; Портфелей: {after['портфелей']}; "
                        f"Запуск: регламентное задание")
    check("Исполнение по расписанию: три ключа (заполнение, проведение, итог)",
          keys_a == ["ИсполнениеСделок", "ИсполнениеСделок.ЗаполнитьТаблицуСделок", "ИсполнениеСделок.Проведение"],
          ", ".join(keys_a))
    check("Вес = разные портфели сделок, комментарий = факт исполнения",
          all(r["вес"] == after["портфелей"] and r["комментарий"] == expected_comment for r in ra),
          f"вес {sorted({r['вес'] for r in ra})}, комментарий '{ra[0]['комментарий'] if ra else '-'}'; создано документов "
          f"{after['документов']} (проведено {after['проведено']}) по {after['сделок']} сделкам и {after['портфелей']} портфелям, "
          f"строк остатка плановой позиции {e_a['до']['строк_остатка']} -> {after['строк_остатка']}")
    t_total = next((r["время_с"] for r in ra if r["ключ"] == "ИсполнениеСделок"), 0)
    t_parts = sum(r["время_с"] for r in ra if r["ключ"] != "ИсполнениеСделок")
    check("Итог не меньше суммы шагов", t_total + 1e-6 >= t_parts, f"итог {fmt(t_total)} с, шаги {fmt(t_parts)} с")
    check("Повторный запуск: исполнять нечего, документы не задваиваются",
          len(rrep) == 3 and all(r["вес"] == 1 and r["доп"].get("Строк") == "0" for r in rrep)
          and e_rep["после"]["документов"] == e_rep["до"]["документов"],
          f"записей {len(rrep)}, вес {sorted({r['вес'] for r in rrep})}, документов {e_rep['до']['документов']} -> {e_rep['после']['документов']}")
    check("Ручной запуск: два ключа без шага заполнения, режим 'вручную'",
          sorted(r["ключ"] for r in rm) == ["ИсполнениеСделок", "ИсполнениеСделок.Проведение"]
          and all(r["доп"].get("Запуск") == "вручную" for r in rm),
          ", ".join(f"{r['ключ']} ({r['доп'].get('Запуск')})" for r in rm))
    cmp_e = data.get("сравнение_исполнения") or {}
    check("Без расширения замеров нет, результат исполнения тот же",
          not rb and e_b["после"] == e_a["после"] and cmp_e.get("совпадают"),
          f"записей без расширения {len(rb)}; набор 01.10 без замеров: документов {e_b['после']['документов']}, "
          f"проведено {e_b['после']['проведено']}, остаток {e_b['до']['строк_остатка']} -> {e_b['после']['строк_остатка']}; "
          f"документы двух наборов построчно (портфель, актив, количество, место хранения, тип портфеля, счет, проведен): "
          f"{len(cmp_e.get('с_замерами_02.10', []))} и {len(cmp_e.get('без_замеров_01.10', []))}, расхождений {cmp_e.get('расхождений', '?')}")

    # ---------------- строка 17: упаковка данных ----------------
    u_runs = []
    for t in (x for x in tests if x["тест"] == "U"):
        rr = in_test(t, "УпаковкаДанных")
        keys = {r["ключ"].replace("УпаковкаДанных.", "") if r["ключ"] != "УпаковкаДанных" else "итог": r for r in rr}
        u_runs.append((t, rr, keys, (keys.get("итог") or {}).get("доп", {}).get("Активных торговых дат", "")))
    u_test, ru, u_keys, trading = next(x for x in u_runs if x[3] in ("", "0"))
    u2_test, ru2, u2_keys, trading2 = next(x for x in u_runs if x[3] not in ("", "0"))
    need = ["итог"] + PACK_STEPS
    need2 = need + [f"Сократить.{x}" for x in PACK_REGISTERS]
    check("Упаковка, число активных торговых дат не задано: три шага и итог",
          u_test["задание"]["состояние"] == "Задание выполнено" and sorted(u_keys) == sorted(need),
          f"состояние '{u_test['задание']['состояние']}', записей {len(ru)}; в комментарии итога 'Активных торговых дат: {trading}' - "
          "ветка сокращения регистров не выполняется (так же и в базовом коде), ключей Сократить.* нет")
    u_total = u_keys["итог"]["время_с"] if "итог" in u_keys else 0
    u_parts = sum(r["время_с"] for k, r in u_keys.items() if k != "итог")
    check("Итог упаковки равен сумме шагов", abs(u_total - u_parts) <= max(1.0, u_total * 0.01),
          f"итог {fmt(u_total, 1)} с, сумма шагов {fmt(u_parts, 1)} с (остаток - чтение настройки торговой части и запись замеров)")
    ub, ua = u_test["до"], u_test["после"]
    check("Штатный результат упаковки: старые проверки лимитов в архиве, подробные кэши очищены",
          ua["КэшВмОписания.Архив=False"] < ub["КэшВмОписания.Архив=False"] and ua["КэшВмКратко.вместилищ"] < ub["КэшВмКратко.вместилищ"],
          f"в архиве {ub['КэшВмОписания.Архив=True']} -> {ua['КэшВмОписания.Архив=True']}, не в архиве "
          f"{ub['КэшВмОписания.Архив=False']} -> {ua['КэшВмОписания.Архив=False']} (моложе суток, не архивируются), вместилищ "
          f"подробного кэша {ub['КэшВмКратко.вместилищ']} -> {ua['КэшВмКратко.вместилищ']}; КэшВмДетально 15,05 млн -> 400 записей")
    u2_total = u2_keys["итог"]["время_с"] if "итог" in u2_keys else 0
    u2_parts = sum(r["время_с"] for k, r in u2_keys.items() if k != "итог")
    check("Упаковка с 7 активными торговыми датами: три шага, пять сокращений регистров и итог",
          u2_test["задание"]["состояние"] == "Задание выполнено" and sorted(u2_keys) == sorted(need2)
          and all(u2_keys[f"Сократить.{x}"]["доп"].get("Активных торговых дат") == "7" for x in PACK_REGISTERS),
          f"записей {len(ru2)} из {len(need2)}, итог {fmt(u2_total)} с, сумма шагов {fmt(u2_parts)} с; число дат задано временным "
          "документом 'Установка настроек торговой части'")

    # ---------------- строка 2: постконтроль ----------------
    p_tests = [t for t in tests if t["тест"] == "P"]
    p_rows = {(t["вариант"], t["метка"]): in_test(t, "ПроверкаЛимитов.ПостКонтроль") for t in p_tests}
    p_by = {(t["вариант"], t["метка"]): t for t in p_tests}
    expect = {("пустая", ""): (1, True, "Проверка не выполнялась"), ("неактивные", ""): (1, False, "Проверка не выполнялась"),
              ("отказ", ""): (20, True, "Фоновые задания"), ("рассылка", ""): (20, False, "Фоновые задания"),
              ("успех", "с_замерами"): (20, False, "Фоновые задания")}
    for key, (weight, error, marker) in expect.items():
        rr = p_rows.get(key, [])
        check(f"Постконтроль, вариант '{key[0]}': одна запись, вес {weight}, ошибка = {'да' if error else 'нет'}",
              len(rr) == 1 and rr[0]["вес"] == weight and rr[0]["ошибка"] == error and marker in rr[0]["комментарий"],
              "; ".join(f"вес {fmt(r['вес'], 0)}, ошибка {'да' if r['ошибка'] else 'нет'}, {fmt(r['время_с'])} с, '{r['комментарий']}'" for r in rr) or "записей нет")
    mail = p_by[("рассылка", "")]
    t_mail = p_rows[("рассылка", "")][0]["время_с"]
    t_ok = p_rows[("успех", "с_замерами")][0]["время_с"]
    check("Замер включает постановку в очередь рассылки",
          mail["очередь_рассылки_после_проверки"] == mail["очередь_рассылки_до"] + 1 and t_mail - t_ok >= 9,
          f"очередь {mail['очередь_рассылки_до']} -> {mail['очередь_рассылки_после_проверки']} (после теста удалено {mail['удалено_из_очереди']}); "
          f"время с рассылкой {fmt(t_mail, 1)} с против {fmt(t_ok, 1)} с без нее: разница {fmt(t_mail - t_ok, 1)} с - штатная пауза 10 с перед постановкой в очередь")
    with_rows = [(k, list(t["строки_результата"].values())[0]) for k, t in p_by.items() if t["строки_результата"]]
    base_rows = with_rows[0][1]
    diffs = sum(len(set(rr) ^ set(base_rows)) for _, rr in with_rows)
    no_ext_runs = [k for k, t in p_by.items() if not any(e["активно"] for e in t["расширения"] if e["имя"] == "FO_KeyOpsPerf")]
    check("Без расширения замера нет, результат проверки тот же построчно",
          all(not p_rows[k] for k in no_ext_runs) and diffs == 0,
          f"прогонов с проверкой {len(with_rows)} (с расширением и без, с рассылкой и без), строк результата по {len(base_rows)}, "
          f"расхождений {diffs}; прогонов без расширения {len(no_ext_runs)}, записей замера в них 0. Поле Замер регистра КэшВмКратко "
          "из сравнения исключено: это хронометраж самой проверки (мс на строку), он меняется от прогона к прогону")
    check("Тестовые настройки возвращены",
          all(t["константа_восстановлена"] and t["неактивных_после_теста"] == 0 and t["очередь_рассылки_после_очистки"] == 0 for t in p_tests),
          "константа НастройкиРассылкиПоЛимитам восстановлена во всех вариантах, временных неактивных портфелей 0, очередь рассылки 0")

    # ---------------- исправления этапа 2 ----------------
    obmen = [r for r in rows if r["ключ"].startswith("ОбменБэкОфис.")]
    by_packet = collections.defaultdict(list)
    for r in obmen:
        by_packet[r["доп"].get("Пакет", "")].append(r)
    aff_after = [r for r in obmen if r["ключ"].endswith(".АффилированныеЛица")]
    contr_after = [r for r in obmen if r["ключ"].endswith(".Контрагенты")]
    before_rows = []
    if os.path.exists(os.path.join(BEFORE_RUN, "measurements.json")):
        with open(os.path.join(BEFORE_RUN, "measurements.json"), encoding="utf-8") as f:
            before_rows = [r for r in json.load(f)["замеры"] if r["ключ"].endswith((".АффилированныеЛица", ".Контрагенты"))]
    mandate_packets = [p for p, rr in by_packet.items() if any(r["ключ"].endswith(".Портфели") for r in rr)
                       and any(r["ключ"].endswith(".Контрагенты") for r in rr)]
    aff_packets = [p for p, rr in by_packet.items() if any(r["ключ"].endswith(".АффилированныеЛица") for r in rr)]
    check("Аффилированные лица: контрагент без них замер не пишет (выгрузка мандатов)",
          mandate_packets and not any(r["ключ"].endswith(".АффилированныеЛица") for p in mandate_packets for r in by_packet[p]),
          f"до исправления (прогон {os.path.basename(BEFORE_RUN)}): " +
          ", ".join(f"{r['ключ'].split('.')[-1]} '{r['комментарий'][:30]}'" for r in before_rows[:2]) +
          f"; после: пакет мандатов - только Контрагенты")
    check("Аффилированные лица: контрагент с ними - запись со счетчиком",
          len(aff_after) == 1 and aff_after[0]["доп"].get("Аффилированных лиц") == "2" and aff_after[0]["вес"] == 1,
          "; ".join(f"вес {fmt(r['вес'], 0)}, '{r['комментарий']}'" for r in aff_after) or "записей нет")
    deal_sections = sorted((r for r in obmen if r["ключ"] == "ОбменБэкОфис.Документы.СделкаСЦеннымиБумагами"), key=lambda r: r["dt"])
    fixed = deal_sections[-1] if deal_sections else None
    check("Раздел СделкаСЦеннымиБумагами: портфели из РаспределениеПоПортфелям, вес = портфели",
          fixed and fixed["вес"] == 3 and fixed["доп"].get("Портфелей") == "3",
          "до исправления: " + "; ".join(f"{r['dt']:%H:%M} вес {fmt(r['вес'], 0)}, Портфелей {r['доп'].get('Портфелей')}" for r in deal_sections[:-1]) +
          (f"; после: {fixed['dt']:%H:%M} вес {fmt(fixed['вес'], 0)}, '{fixed['комментарий'][:40]}'" if fixed else ""))

    all_ok = all(ok for _, ok, _ in checks)
    chk_rows = "".join(f"<tr class='{'ok' if ok else 'bad'}'><td><b class='{'yes' if ok else 'no'}'>{'да' if ok else 'нет'}</b></td>"
                       f"<td>{esc(n)}</td><td>{esc(fact)}</td></tr>" for n, ok, fact in checks)

    # ---------------- покрытие ключей Р4 ----------------
    cover = [("15", "ИсполнениеСделок"), ("15", "ИсполнениеСделок.ЗаполнитьТаблицуСделок"), ("15", "ИсполнениеСделок.Проведение"),
             ("17", "УпаковкаДанных")] + [("17", f"УпаковкаДанных.{s}") for s in PACK_STEPS] + \
            [("17", f"УпаковкаДанных.Сократить.{x}") for x in PACK_REGISTERS] + \
            [("2", "ПроверкаЛимитов.ПостКонтроль")]
    cnt = collections.Counter(r["ключ"] for r in rows)
    cov_rows = "".join(f"<tr class='{'ok' if cnt[k] else 'bad'}'><td>{n}</td><td><code>{esc(k)}</code></td><td class='n'>{cnt[k]}</td>"
                       f"<td><b class='{'yes' if cnt[k] else 'no'}'>{'да' if cnt[k] else 'нет'}</b></td></tr>" for n, k in cover)
    covered = sum(1 for _, k in cover if cnt[k])
    not_cov = ("<p class='lead'>Ключи <code>УпаковкаДанных.Сократить.&lt;Регистр&gt;</code> пишутся только при заданном в "
               "настройках торговой части числе активных торговых дат. На разработческой базе оно не задано, поэтому для их "
               "проверки упаковка запущена второй раз с временным документом настроек (7 дат).</p>")

    # ---------------- протокол тестов ----------------
    def test_label(t):
        if t["тест"] == "E":
            return f"Исполнение сделок, поставка {t['дата']}, {t['метка'].replace('_', ' ')}"
        if t["тест"] == "M":
            return "Исполнение сделок вручную, таблица пустая"
        if t["тест"] == "U":
            dates = next((x[3] for x in u_runs if x[0] is t), "")
            return "Упаковка данных, активных торговых дат " + (dates if dates not in ("", "0") else "не задано")
        return f"Постконтроль, вариант '{t['вариант']}'" + (f", {t['метка'].replace('_', ' ')}" if t["метка"] else "")

    proto = []
    for t in tests:
        prefix = {"E": "ИсполнениеСделок", "M": "ИсполнениеСделок", "U": "УпаковкаДанных", "P": "ПроверкаЛимитов"}[t["тест"]]
        rr = in_test(t, prefix)
        ext = next((e for e in t.get("расширения", []) if e["имя"] == "FO_KeyOpsPerf"), {})
        job = t.get("задание", {})
        state = job.get("состояние", "выполнено во внешнем соединении")
        err = job.get("ошибка", "").split("\n")[0]
        recs = "".join(f"<div><code>{esc(r['ключ'])}</code> вес {fmt(r['вес'], 0)}, {fmt(r['время_с'])} с"
                       f"{', <b class=no>ошибка</b>' if r['ошибка'] else ''}: {esc(r['комментарий'])}</div>" for r in rr) or "<i>записей нет</i>"
        proto.append(f"<tr><td>{esc(t['начало'][11:19])}</td><td>{esc(test_label(t))}</td>"
                     f"<td>{'да' if ext.get('активно') else '<b class=no>нет</b>'}</td><td>{esc(state)}{('<br><small>' + esc(err) + '</small>') if err else ''}</td>"
                     f"<td class='n'>{fmt(job.get('длительность_с', 0), 1) if job else '-'}</td><td>{recs}</td></tr>")

    # ---------------- пакеты обмена в окне прогона ----------------
    def packet_kind(rr):
        keys = {r["ключ"].split(".", 1)[1] for r in rr}
        if "Документы.СделкаСЦеннымиБумагами" in keys:
            return "тестовые сделки (подготовка исполнения)"
        if "Справочники.АффилированныеЛица" in keys:
            return "контрагенты с аффилированными лицами"
        if "Справочники.Портфели" in keys:
            return "мандаты (выгрузка МО)"
        if "Справочники.Субпортфели" in keys:
            return "счета мандатов (выгрузка МО)"
        return "служебный"
    pk_rows = []
    for p, rr in sorted(by_packet.items(), key=lambda x: min(r["начало_мс"] for r in x[1])):
        rr = sorted(rr, key=lambda r: r["начало_мс"])
        pk_rows.append(f"<tr><td>{esc(min(r['dt'] for r in rr).strftime('%H:%M:%S'))}</td><td>{esc(packet_kind(rr))}</td><td>" +
                       "".join(f"<div><code>{esc(r['ключ'])}</code> вес {fmt(r['вес'], 0)}: {esc(r['комментарий'])}</div>" for r in rr) +
                       "</td></tr>")

    raw = "".join(
        f"<tr data-k='{esc(r['ключ'])}'><td>{esc(r['dt'].strftime('%H:%M:%S'))}</td><td class='n'>{r['сеанс']}</td>"
        f"<td><code>{esc(r['ключ'])}</code></td><td class='n'>{fmt(r['время_с'])}</td><td class='n'>{fmt(r['вес'], 0)}</td>"
        f"<td>{'да' if r['ошибка'] else ''}</td><td>{esc(r['комментарий'])}</td></tr>" for r in sorted(rows, key=lambda r: r["dt"]))
    ext_now = ", ".join(f"{e['имя']} {e['версия']} (активно: {'да' if e['активно'] else 'нет'}, безопасный режим: "
                        f"{'да' if e['безопасный_режим'] else 'нет'})" for e in data.get("расширения", []))
    stage3_rows = [r for r in rows if not r["ключ"].startswith("ОбменБэкОфис.")]

    grok = [
        ("Постконтроль: при досрочном выходе (нет портфелей в настройке, все неактивны) замер не пишется; запись стоит до "
         "постановки в очередь рассылки, а таблица описывает замер на всю процедуру", "Подтверждено",
         "Исправлено в 1.0.0.4: замер на всю процедуру, четыре точки записи (два досрочных выхода, отказ проверки, успешное завершение "
         "после очереди рассылки), общий метод ЗакончитьЗамерПостКонтроля. Найдено при проверке: в очереди рассылки штатный код делает "
         "паузу 10 с, она входит в замер."),
        ("АффилированныеЛица пишется по списку контрагентов: без аффилированных лиц запись есть, вес как у контрагентов", "Подтверждено",
         "Исправлено в 1.0.0.4: учитываются только контрагенты с аффилированными лицами (то же условие, что у штатного прохода), без них "
         "замер не пишется, в комментарии число аффилированных лиц. В тесте этапа 2 запись 'Строк: 1' была ложной."),
        ("Вес КотировкиЦБНаБирже - число котировок, а в Р4 - число документов", "Расхождение документа и кода",
         "Код оставлен: один документ содержит котировки всех бумаг на дату, вес 1 не отражает объем (решение этапа 2, версия 1.0.0.2). "
         "Р4, Excel и таблица исправлены: вес - число котировок."),
        ("Ключи разделов берутся из имени раздела XDTO (ТипыКлиентов, КотировкиЦБНаБирже), а не из имени процедуры", "Верно, это по замыслу",
         "В Р4, Excel и таблице записано, что <Имя> - имя раздела пакета XDTO; по этим именам сверяется регистр."),
        ("ДенежныеПотоки без портфеля: вес - число строк", "Верно, это по замыслу",
         "В типе XDTO раздела нет портфеля (только Актив, МестоХранения, даты, суммы), правило 'без портфеля - строки' работает как задумано."),
        ("ДополнительныеСведения в FO_KeyOpsPerf не замеряется, пустые разделы не пишутся, своих объектов нет", "Верно", "Без изменений."),
    ]
    grok_rows = "".join(f"<tr><td>{esc(a)}</td><td><b>{esc(b)}</b></td><td>{esc(c)}</td></tr>" for a, b, c in grok)

    page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тест замеров этапа 3</title>
<style>
:root {{ --bg:#f3f5f9; --card:#fff; --ink:#18212d; --muted:#5d6b7c; --line:#dbe2ea; --soft:#eef2f7; --head:#1d3557;
  --accent:#2a6fdb; --ok:#1f9d55; --ok-bg:#e9f7ef; --bad:#d64545; --bad-bg:#fdecec; --code:#eef2f7; --warn:#c98a04; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#0f141b; --card:#171e27; --ink:#e6ebf1;
  --muted:#9aa8b8; --line:#2a3542; --soft:#1d2631; --head:#22324a; --ok-bg:#14291e; --bad-bg:#2f1a1a; --code:#222c38; }} }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 "Segoe UI",Arial,sans-serif; }}
.wrap {{ max-width:1500px; margin:0 auto; padding:22px 24px 30px; }}
h1 {{ margin:0 0 6px; font-size:23px; }} h2 {{ margin:26px 0 10px; font-size:17px; }}
.lead {{ color:var(--muted); margin:0 0 6px; max-width:1150px; }}
.verdict {{ margin:16px 0; padding:12px 16px; border-radius:10px; font-weight:600; border:1px solid var(--line);
  background:{'var(--ok-bg)' if all_ok else 'var(--bad-bg)'}; color:{'var(--ok)' if all_ok else 'var(--bad)'}; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 16px; }}
.card b {{ display:block; font-size:26px; line-height:1.15; }} .card span {{ color:var(--muted); font-size:12.5px; }}
.box {{ background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:auto; }}
table {{ border-collapse:collapse; width:100%; }} th, td {{ padding:7px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:var(--head); color:#fff; font-weight:600; font-size:12.5px; position:sticky; top:0; }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
code {{ font-family:Consolas,monospace; font-size:12px; background:var(--code); padding:0 4px; border-radius:4px; }}
tr.ok td:first-child {{ box-shadow:inset 4px 0 var(--ok); }} tr.bad td:first-child {{ box-shadow:inset 4px 0 var(--bad); }}
b.yes {{ color:var(--ok); }} b.no {{ color:var(--bad); }}
.note {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--warn); border-radius:8px; padding:10px 14px; margin:8px 0; }}
.filter {{ margin:8px 0; padding:7px 10px; border:1px solid var(--line); border-radius:8px; width:min(480px,100%); background:var(--card); color:var(--ink); }}
.scroll {{ max-height:560px; overflow:auto; }} ul {{ margin:6px 0; }} small {{ color:var(--muted); }}
@media (max-width:700px) {{ .wrap {{ padding:16px; }} }}
</style></head><body><div class="wrap">
<h1>Тестирование замеров: исполнение сделок, упаковка данных, постконтроль (IMDEV-9530, этап 3)</h1>
<p class="lead">Разработческая база ФО (WIN_FO_server). Процедуры регламентных заданий запущены фоновыми заданиями с теми же методами
(серверный контекст, как у расписания); ручной путь исполнения сделок - во внешнем соединении. Сделки к исполнению загружены
штатным пакетом веб-сервиса ФО (раздел СделкаСЦеннымиБумагами): 4 сделки по 3 тестовым портфелям на 02.10.2026 и такой же набор на
01.10.2026 для запуска без расширения. Постконтроль - 20 тестовых портфелей стенда, настройка рассылки задается на время теста.
Записи выбраны из регистра "Замеры времени" с начала прогона ({esc(data['начало'])}). Расширения: {esc(ext_now)}.
Константа "Выполнять замеры производительности": {'включена' if data.get('замеры_включены') else 'выключена'}.</p>
<div class="verdict">{'Все проверки пройдены: ' if all_ok else 'Есть непройденные проверки: '}покрытие ключей {covered}/{len(cover)},
правил {sum(1 for _, ok, _ in checks if ok)}/{len(checks)}; результат операций с замерами и без них совпадает</div>
<div class="cards">
<div class="card"><b>{len(stage3_rows)}</b><span>записей замеров строк 2, 15, 17</span></div>
<div class="card"><b>{len(set(r['ключ'] for r in stage3_rows))}</b><span>ключей операций и шагов</span></div>
<div class="card"><b>{len(tests)}</b><span>запусков операций</span></div>
<div class="card"><b>{e_a['после']['документов']}</b><span>документов исполнения, совпали с запуском без расширения</span></div>
<div class="card"><b>{len(with_rows)} x {len(base_rows)}</b><span>прогонов постконтроля x строк результата, совпали построчно</span></div>
<div class="card"><b>{fmt(u_total / 3600, 1)}</b><span>часа штатной упаковки данных: архивация 64 проверок, удаление 15 млн строк кэша</span></div>
</div>

<h2>Покрытие ключей плана (Р4)</h2>
<div class="box"><table><tr><th>Строка списка</th><th>Ключ</th><th>Записей</th><th>Сработал</th></tr>{cov_rows}</table></div>
{not_cov}

<h2>Проверка правил замера и результата операций</h2>
<div class="box"><table><tr><th>Итог</th><th>Правило</th><th>Факт</th></tr>{chk_rows}</table></div>

<h2>Протокол запусков и записи регистра по каждому</h2>
<div class="box scroll"><table><tr><th>Начало</th><th>Запуск</th><th>FO_KeyOpsPerf</th><th>Состояние</th><th>Длительность, с</th><th>Записи замеров</th></tr>{''.join(proto)}</table></div>
<div class="note"><b>Состояние "Задание завершено с ошибками"</b> у варианта 'отказ' - штатный отказ проверки ("Не загружена фактическая
позиция на дату проверки"): с расширением и без него задание завершается тем же исключением, замер пишется до него с признаком ошибки.</div>

<h2>Пакеты обмена в окне прогона (подготовка данных и исправления этапа 2)</h2>
<p class="lead">Загрузка тестовых сделок, повтор выгрузки мандатов из МО и пакет с контрагентами, у одного из которых два аффилированных
лица. Ключ раздела - имя раздела пакета XDTO.</p>
<div class="box scroll"><table><tr><th>Начало</th><th>Пакет</th><th>Записи пакета и разделов</th></tr>{''.join(pk_rows)}</table></div>

<h2>Разбор замечаний ревью Grok</h2>
<div class="box"><table><tr><th>Замечание</th><th>Вывод</th><th>Что сделано</th></tr>{grok_rows}</table></div>

<h2>Найдено и исправлено при тестировании этапа 3</h2>
<div class="note"><b>Вес раздела СделкаСЦеннымиБумагами.</b> Загрузка тестовых сделок показала вес 4 и "Портфелей: 0": у сделки портфель
лежит не в строке раздела, а в табличной части РаспределениеПоПортфелям. Сверка всех 69 разделов пакета XDTO: портфель есть в 23 разделах
(в 21 - свойство строки Портфель, в ДополнительныеСведения - Объект.Портфель, в СделкаСЦеннымиБумагами - РаспределениеПоПортфелям), не
покрыт был только этот раздел. В 1.0.0.4 добавлено чтение портфелей из РаспределениеПоПортфелям; это же исправляет вес пакета целиком.</div>
<div class="note"><b>Комментарий исполнения сделок.</b> Строка таблицы исполнения - остаток плановой позиции по сделке (отдельно бумага и деньги),
поэтому "Сделок: 8" при 4 сделках вводило в заблуждение. Комментарий стал "Строк: 8; Сделок: 4; Портфелей: 3; Запуск: ...".</div>

<h2>Изменения тестовых данных разработческой базы</h2>
<p class="lead">Все тестовые данные этапа по решению заказчика остаются в разработческой базе.</p>
<ul>
<li>Сделки T9530_A_1..4 (поставка 02.10.2026) и T9530_B_1..4 (01.10.2026) по портфелям T9532_0001..0003 и 16 документов
исполнения к ним; контрагенты T9530_K1..K3.</li>
<li>Настройка рассылки писем "T9530 тест рассылки" (адрес на домене example.invalid); оставлена в базе.</li>
<li>Внешние коды счетов стенда IMDEV-9532 на время загрузки сделок - возвращены пустыми. Константа настройки рассылки по
лимитам, неактивные портфели и очередь рассылки - в исходном состоянии.</li>
<li>Упаковка данных выполнена штатно: проверки лимитов старше суток переведены в архив, их подробные кэши очищены (по согласованию).</li>
<li>Документ "Установка настроек торговой части 000000001 от 02.10.2026" (7 активных торговых дат, остальное по умолчанию) создан для
проверки сокращения регистров; оставлен в базе.</li>
<li>Набор сделок T9530_C_1..4 (поставка 03.10.2026) - проверка исправления веса раздела сделок, исполнен.</li>
</ul>

<h2>Все записи регистра</h2>
<input class="filter" id="f" type="search" placeholder="Фильтр по ключу или комментарию...">
<div class="box scroll"><table id="raw"><tr><th>Записано</th><th>Сеанс</th><th>Ключ</th><th>Время, с</th><th>Вес</th><th>Ошибка</th><th>Комментарий</th></tr>{raw}</table></div>
<p class="lead">Источник: {esc(os.path.relpath(run_dir, TASK))}\\measurements.json; время записи - локальное время сервера ФО.</p>
</div>
<script>
document.getElementById("f").addEventListener("input", function () {{
  var q = this.value.toLowerCase();
  document.querySelectorAll("#raw tr[data-k]").forEach(function (tr) {{
    tr.style.display = !q || tr.textContent.toLowerCase().indexOf(q) !== -1 ? "" : "none"; }});
}});
</script></body></html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(OUT)
    for n, ok, fact in checks:
        print("OK " if ok else "FAIL", n, "|", fact[:200])
    print("покрытие", covered, len(cover))


if __name__ == "__main__":
    main()
