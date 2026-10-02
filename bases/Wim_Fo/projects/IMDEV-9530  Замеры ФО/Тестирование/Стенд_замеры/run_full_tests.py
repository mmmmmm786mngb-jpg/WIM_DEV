# -*- coding: utf-8 -*-
"""Полное тестирование расширения FO_KeyOpsPerf (IMDEV-9530, строки 2, 6, 7, 8, 15, 17) на разработческих базах.

Один прогон, шаги выполняются по отдельности (состояние в results/current_full.json), отчет строит
build_report_full.py. Для каждой операции есть запуск с расширением и сравнение с запуском без него.

  start
  A_meas / A_base   строки 6-8: выгрузка остатков МО -> ФО, 450 тестовых портфелей в 5 потоков (стенд IMDEV-9532,
                    run_export.py), с FO_KeyOpsPerf и без; снимки данных ФО сверяются
  B / C             строка 7: мандаты и счета; строка 8: котировки (штатные обработки МО ПРОД)
  packets           строки 7-8: пакеты веб-сервиса ФО - тестовые сделки (раздел СделкаСЦеннымиБумагами,
                    портфели в РаспределениеПоПортфелям) и контрагенты с аффилированными лицами
  E                 строка 15: исполнение сделок - набор D (05.10.2026) с замерами, повторный запуск, набор F
                    (06.10.2026) без расширения, ручной запуск; документы наборов сверяются построчно
  P                 строка 2: постконтроль - пустая настройка, неактивные портфели, отказ, рассылка, успех;
                    успех и рассылка без расширения; строки результата сверяются
  U                 строка 17: упаковка данных с расширением и без
  collect           записи регистра ЗамерыВремени прогона и сводки в measurements.json

    python run_full_tests.py <шаг>
"""
import datetime
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import prepare_deals as deals  # noqa: E402
import run_measure_tests as stage2  # noqa: E402
import run_stage3_tests as stage3  # noqa: E402
from stand_common import connect, query  # noqa: E402

STAND = stage2.STAND
RESULTS = os.path.join(HERE, "results")
CURRENT = os.path.join(RESULTS, "current_full.json")
EXT_PROPS = os.path.join(TASK, "Скрипты", "extension_props.py")
KEY_FILTER = """
            (З.КлючеваяОперация.Имя ПОДОБНО "ИсполнениеСделок%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "УпаковкаДанных%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "ПроверкаЛимитов.%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "ОбменБэкОфис.%")"""
log = stage3.log


def extension(active):
    """Включает или выключает FO_KeyOpsPerf и возвращает НОВОЕ подключение к ФО.

    Фоновое задание получает набор расширений сеанса, из которого запущено, поэтому после переключения
    расширения задания запускаются только из нового сеанса.
    """
    command = "prepare" if active else "deactivate"
    out = subprocess.run([sys.executable, EXT_PROPS, command, "FO_KeyOpsPerf"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    log("   FO_KeyOpsPerf", "включено" if active else "выключено", out.stdout.strip().split("\n")[-1])
    return connect("wim_fo")


def load_state():
    with open(CURRENT, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(CURRENT, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def add(state, entry, fo):
    entry["расширения"] = stage3.extensions_info(fo)
    state["тесты"].append(entry)
    save_state(state)


def timed(fo, func, *args):
    started = stage3.now_1c(fo)
    entry = func(*args)
    entry["начало"] = started
    entry["окончание"] = stage3.now_1c(fo)
    return entry


def export_positions(label, count=450, threads=5):
    scenario = f"IMDEV9530_FULL_{label}_{count}_{threads}t"
    log(f"A. Остатки ({label}): {count} портфелей, {threads} потоков")
    cmd = [sys.executable, os.path.join(STAND, "run_export.py"), "--scenario", scenario,
           "--count", str(count), "--threads", str(threads)]
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=STAND, capture_output=True, text=True, encoding="utf-8", errors="replace")
    runs = sorted(glob.glob(os.path.join(STAND, "results", f"*_{scenario}")))
    log(f"   завершено за {time.perf_counter() - started:.0f} с, код {proc.returncode}, прогон {os.path.basename(runs[-1]) if runs else '-'}")
    return {"тест": "A", "метка": label, "портфелей": count, "потоков": threads, "код": proc.returncode,
            "секунд": round(time.perf_counter() - started, 1), "прогон_стенда": runs[-1] if runs else "",
            "вывод": proc.stdout[-3000:] + proc.stderr[-2000:]}


def send_packet(fo, builder, label):
    ws = deals.proxy(fo)
    factory = ws.ФабрикаXDTO
    packet = builder(factory)
    answer = ws.DownloadPosition(packet)
    text = deals.xml_text(fo, factory, answer)
    code = text.split("<Код>")[1].split("</Код>")[0] if "<Код>" in text else "?"
    log(f"   пакет '{label}': код ответа {code}")
    return {"тест": "пакет", "метка": label, "код_ответа": code, "ответ": text[:4000]}


def execution_documents(fo, series):
    rows = query(fo, """
        ВЫБРАТЬ
            Д.Сделка.ВнешнийКод КАК Сделка,
            Д.Портфель.ВнешнийКод КАК Портфель,
            ПРЕДСТАВЛЕНИЕ(Д.Актив) КАК Актив,
            Д.Количество КАК Количество,
            ПРЕДСТАВЛЕНИЕ(Д.МестоХранения) КАК МестоХранения,
            ПРЕДСТАВЛЕНИЕ(Д.ТипПортфеля) КАК ТипПортфеля,
            ПРЕДСТАВЛЕНИЕ(Д.СчетУчета) КАК СчетУчета,
            Д.Проведен КАК Проведен
        ИЗ
            Документ.ИсполнениеПоСделке КАК Д
        ГДЕ
            Д.Сделка.ВнешнийКод ПОДОБНО &Маска""", {"Маска": f"T9530_{series}_%"})
    return sorted("|".join([r["Сделка"].split("_")[2], r["Портфель"], r["Актив"], f"{float(r['Количество']):g}",
                            r["МестоХранения"], r["ТипПортфеля"], r["СчетУчета"], str(bool(r["Проведен"]))]) for r in rows)


def step_e(state, fo):
    day_d, day_f = datetime.datetime(2026, 10, 5), datetime.datetime(2026, 10, 6)
    deals.set_place_codes(fo)
    try:
        factory_packet = lambda series, day: (lambda factory: deals.build_packet(fo, factory, day, series))  # noqa: E731
        add(state, timed(fo, send_packet, fo, factory_packet("D", day_d), "сделки D 05.10"), fo)
        add(state, timed(fo, send_packet, fo, factory_packet("F", day_f), "сделки F 06.10"), fo)
    finally:
        deals.set_place_codes(fo, restore=True)
    add(state, timed(fo, stage3.test_e_execution, fo, day_d, "с_замерами"), fo)
    add(state, timed(fo, stage3.test_e_execution, fo, day_d, "повторный_запуск"), fo)
    fo_off = extension(False)
    try:
        add(state, timed(fo_off, stage3.test_e_execution, fo_off, day_f, "без_замеров"), fo_off)
    finally:
        fo = extension(True)
    add(state, timed(fo, stage3.test_m_manual, fo), fo)
    a, b = execution_documents(fo, "D"), execution_documents(fo, "F")
    state["сравнение_исполнения"] = {"с_замерами": a, "без_замеров": b, "совпадают": a == b,
                                     "расхождений": len(set(a) ^ set(b))}
    save_state(state)
    log("   документы D/F:", len(a), len(b), "совпадают", a == b)


def step_p(state, fo):
    for variant in ("пустая", "неактивные", "отказ", "рассылка", "успех"):
        add(state, timed(fo, stage3.test_p_postcontrol, fo, variant, 20, "с_замерами"), fo)
    fo_off = extension(False)
    try:
        for variant in ("успех", "рассылка"):
            add(state, timed(fo_off, stage3.test_p_postcontrol, fo_off, variant, 20, "без_замеров"), fo_off)
    finally:
        extension(True)


def step_u(state, fo):
    entry = timed(fo, stage3.test_u_packing, fo)
    entry["метка"] = "с_замерами"
    add(state, entry, fo)
    fo_off = extension(False)
    try:
        entry = timed(fo_off, stage3.test_u_packing, fo_off)
        entry["метка"] = "без_замеров"
        add(state, entry, fo_off)
    finally:
        extension(True)


def measurements(fo, since_xml):
    stage3.KEY_FILTER = KEY_FILTER
    rows = stage3.measurements(fo, since_xml)
    # окончание замера нужно для дорожек пакетов
    since = stage3.date_1c(fo, datetime.datetime.fromisoformat(since_xml))
    ends = query(fo, f"""
        ВЫБРАТЬ З.ДатаНачалаЗамера КАК Начало, З.ДатаОкончания КАК Окончание, З.НомерСеанса КАК Сеанс
        ИЗ РегистрСведений.ЗамерыВремени КАК З
        ГДЕ З.ДатаЗаписиЛокальная >= &Начало И {KEY_FILTER}""", {"Начало": since})
    by_start = {(float(r["Начало"]), int(r["Сеанс"])): float(r["Окончание"] or 0) for r in ends}
    for r in rows:
        r["окончание_мс"] = by_start.get((r["начало_мс"], r["сеанс"]), r["начало_мс"] + r["время_с"] * 1000)
    return rows


def step_collect(state, fo):
    sys.path.insert(0, STAND)
    import snapshot  # noqa: E402
    a_runs = {t["метка"]: t for t in state["тесты"] if t["тест"] == "A"}
    summaries = {}
    for label, t in a_runs.items():
        path = t["прогон_стенда"]
        with open(os.path.join(path, "summary.json"), encoding="utf-8") as f:
            summaries[label] = json.load(f)
    snaps = {}
    for label, t in a_runs.items():
        with open(os.path.join(t["прогон_стенда"], "snapshot.json"), encoding="utf-8") as f:
            snaps[label] = json.load(f)
    diffs = snapshot.compare(snaps["base"], snaps["meas"]) if len(snaps) == 2 else []
    data = {**{k: v for k, v in state.items() if k not in ("out_dir",)},
            "сводки_стенда": summaries,
            "сверка_снимков": {"строк": snapshot.summary(snaps.get("meas", {})) if snaps else {},
                               "расхождений": len(diffs), "примеры": [str(d)[:200] for d in diffs[:10]]},
            "расширения": stage3.extensions_info(fo),
            "замеры_включены": bool(fo.Константы.ВыполнятьЗамерыПроизводительности.Получить()),
            "замеры": measurements(fo, state["начало"])}
    with open(os.path.join(state["out_dir"], "measurements.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    log(f"Записей замеров: {len(data['замеры'])}; сверка снимков: {data['сверка_снимков']['расхождений']} расхождений; "
        f"результаты: {state['out_dir']}")


def main():
    step = sys.argv[1]
    if step == "start":
        fo = connect("wim_fo")
        out_dir = os.path.join(RESULTS, "full_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(out_dir, exist_ok=True)
        save_state({"out_dir": out_dir, "начало": stage3.now_1c(fo), "тесты": []})
        log("Прогон начат:", out_dir)
        return
    state = load_state()
    fo = connect("wim_fo")
    if step == "A_meas":
        add(state, timed(fo, export_positions, "meas"), fo)
    elif step == "A_base":
        extension(False)
        try:
            add(state, timed(fo, export_positions, "base"), fo)
        finally:
            extension(True)
    elif step in ("B", "C"):
        runner = {"B": stage2.test_b_mandates, "C": stage2.test_c_quotes}[step]
        add(state, timed(fo, runner, state["out_dir"]), fo)
    elif step == "packets":
        add(state, timed(fo, send_packet, fo, lambda factory: deals.build_affiliates_packet(fo, factory),
                         "контрагенты с аффилированными лицами"), fo)
    elif step == "E":
        step_e(state, fo)
    elif step == "P":
        step_p(state, fo)
    elif step == "U":
        step_u(state, fo)
    elif step == "redo_off":
        # повтор прогонов без расширения после исправления (новый сеанс после выключения) и упаковки
        state["тесты"] = [t for t in state["тесты"] if not (t["тест"] in ("E", "P", "U") and t.get("метка") == "без_замеров")
                          and t["тест"] != "U"]
        save_state(state)
        day_f2 = datetime.datetime(2026, 10, 7)
        if not any(t.get("метка") == "сделки G 07.10" for t in state["тесты"]):
            deals.set_place_codes(fo)
            try:
                add(state, timed(fo, send_packet, fo, lambda factory: deals.build_packet(fo, factory, day_f2, "G"),
                                 "сделки G 07.10"), fo)
            finally:
                deals.set_place_codes(fo, restore=True)
        fo_off = extension(False)
        try:
            add(state, timed(fo_off, stage3.test_e_execution, fo_off, day_f2, "без_замеров"), fo_off)
            for variant in ("успех", "рассылка"):
                add(state, timed(fo_off, stage3.test_p_postcontrol, fo_off, variant, 20, "без_замеров"), fo_off)
        finally:
            fo = extension(True)
        a, b = execution_documents(fo, "D"), execution_documents(fo, "G")
        state["сравнение_исполнения"] = {"с_замерами": a, "без_замеров": b, "совпадают": a == b,
                                         "расхождений": len(set(a) ^ set(b)), "наборы": "D (05.10) и G (07.10)"}
        save_state(state)
        log("   документы D/G:", len(a), len(b), "совпадают", a == b)
        step_u(state, fo)
    elif step == "collect":
        step_collect(state, fo)
    else:
        raise SystemExit(f"неизвестный шаг {step}")


if __name__ == "__main__":
    main()
