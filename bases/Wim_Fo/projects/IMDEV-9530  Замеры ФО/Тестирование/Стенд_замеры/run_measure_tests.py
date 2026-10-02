# -*- coding: utf-8 -*-
"""Прогон тестов замеров приема пакетов из МО (IMDEV-9530, этап 2) на стенде МО-ФО IMDEV-9532.

Все выгрузки идут штатно: обработка МО вызывает веб-сервис ФО (http://localhost/win_fo), пакет загружает
обработка ОбменДаннымиБэкОфис с расширениями FO_KeyOpsPerf и FO_PositionLoadOpt 1.0.0.5.

  A. Остатки: run_export.py стенда IMDEV-9532, 90 тестовых портфелей в 2 потока (по пакету на поток):
     пакеты 754 / 768 / 872 / удаление блокировок / перерасчет РСА. Проверяет ОбменБэкОфис.Пакет,
     РегистрыСведений.* (ФактическаяПозиция, СтоимостьЧистыхАктивов и др.), ДополнительныеСведения (замер
     в FO_PositionLoadOpt), ОперацииПослеОбмена, параллельность по сеансам.
  B. Мандаты: обработка МО внВыгрузкаСчетовМандатов_МО_ФО (версия ПРОД), 10 тестовых мандатов и их 20 счетов:
     Выгрузить("Мандаты"), Выгрузить("СчетаМандатов"). Проверяет Справочники.Портфели, Справочники.Субпортфели.
  C. Котировки: обработка МО внВыгрузкаКотировокМО_ФО (версия ПРОД), 3 тестовые ценные бумаги. Проверяет
     Документы.КотировкиЦБНаБирже и РегистрыСведений.ФинансовыеПоказателиОблигаций. На время теста очищается
     константа ФО "Операции после обмена", чтобы штатный вызов перерасчета РСА по всем портфелям базы не запускал
     фоновый пересчет; после теста значение возвращается.

После прогонов выбирает записи регистра ЗамерыВремени ФО с ключами ОбменБэкОфис.* и сохраняет их в
results/<время>/measurements.json; отчет строит build_report.py.
"""
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

STAND = glob.glob(r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО')[0]
sys.path.insert(0, STAND)
from stand_common import (EXTERNAL_IB_NAME, PREFIX, TEST_DATE, WS_BASE, WS_NAME, connect, query, date_1c, mandate_code,  # noqa: E402
                          share_code)

HERE = os.path.dirname(os.path.abspath(__file__))
EPF_DIR = os.path.join(HERE, "epf")
RESULTS = os.path.join(HERE, "results")


def log(*args):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *args, flush=True)


def create_mo_epf(mo, name):
    tmp = os.path.join(tempfile.gettempdir(), f"{name}_9530.epf")
    shutil.copyfile(os.path.join(EPF_DIR, f"{name}.epf"), tmp)
    protection = mo.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    return mo.ВнешниеОбработки.Создать(tmp, False, protection), tmp


def external_ib(mo):
    return query(mo, "ВЫБРАТЬ Сп.Ссылка КАК Ссылка ИЗ Справочник.ВнешниеИнформационныеБазы КАК Сп "
                     "ГДЕ Сп.Наименование = &Имя", {"Имя": EXTERNAL_IB_NAME})[0]["Ссылка"]


def test_a_positions(out_dir, count=90, threads=2):
    log(f"A. Остатки: {count} портфелей, {threads} потоков")
    cmd = [sys.executable, os.path.join(STAND, "run_export.py"), "--scenario", f"IMDEV9530_A_{count}_{threads}t",
           "--count", str(count), "--threads", str(threads)]
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=STAND, capture_output=True, text=True, encoding="utf-8", errors="replace")
    with open(os.path.join(out_dir, "test_a_stdout.txt"), "w", encoding="utf-8") as f:
        f.write(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    log(f"A. завершено за {time.perf_counter() - started:.0f} с, код {proc.returncode}")
    runs = sorted(glob.glob(os.path.join(STAND, "results", f"*_IMDEV9530_A_{count}_{threads}t")))
    return {"тест": "A", "портфелей": count, "потоков": threads, "код": proc.returncode,
            "секунд": round(time.perf_counter() - started, 1), "прогон_стенда": runs[-1] if runs else ""}


def test_b_mandates(out_dir, count=10):
    log(f"B. Мандаты: {count} мандатов и их счета")
    mo = connect("wim_mo")
    epf, tmp = create_mo_epf(mo, "внВыгрузкаСчетовМандатов_МО_ФО")
    # В этой обработке АдресWS - строка с адресом WSDL, а не ссылка на внешнюю информационную базу.
    epf.АдресWS = f"{WS_BASE}/ws/{WS_NAME}.1cws?wsdl"
    epf.РозничноеДУ = True
    codes = [mandate_code(i) for i in range(1, count + 1)]
    arr = mo.NewObject("Массив")
    for c in codes:
        arr.Добавить(c)
    mandates = query(mo, "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.Мандаты КАК М ГДЕ М.КодМандата В (&Коды) "
                         "УПОРЯДОЧИТЬ ПО М.КодМандата", {"Коды": arr})
    for m in mandates:
        row = epf.Мандаты.Добавить()
        mo.ЗаполнитьЗначенияСвойств(row, m["Ссылка"])
        row.Ссылка = m["Ссылка"]
        row.Выгружать = True
        row.Ref = m["Ссылка"].УникальныйИдентификатор()
    accounts = query(mo, "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Справочник.СчетаМандатов КАК С "
                         "ГДЕ С.Владелец.КодМандата В (&Коды) УПОРЯДОЧИТЬ ПО С.КодСчета", {"Коды": arr})
    for a in accounts:
        row = epf.СчетаМандатов.Добавить()
        mo.ЗаполнитьЗначенияСвойств(row, a["Ссылка"])
        row.Ссылка = a["Ссылка"]
        row.Выгружать = True
        row.Ref = a["Ссылка"].УникальныйИдентификатор()
    result = {"тест": "B", "мандатов": len(mandates), "счетов": len(accounts)}
    started = time.perf_counter()
    for part in ("Мандаты", "СчетаМандатов"):
        try:
            epf.Выгрузить(part)
        except Exception as exc:  # noqa: BLE001 - фиксируем и продолжаем
            result[f"исключение_{part}"] = str(exc)[:400]
    result["секунд"] = round(time.perf_counter() - started, 1)
    result["есть_ошибки_МО"] = bool(epf.ЕстьОшибки)
    with open(os.path.join(out_dir, "test_b_mo_log.txt"), "w", encoding="utf-8") as f:
        f.write(epf.ТекстовыйЛог.ПолучитьТекст())
    os.remove(tmp)
    log("B.", result)
    return result


def test_c_quotes(out_dir):
    log("C. Котировки: 3 ценные бумаги")
    fo = connect("wim_fo")
    saved = fo.ЗначениеВСтрокуВнутр(fo.Константы.ОперацииПослеОбмена.Получить())
    fo.Константы.ОперацииПослеОбмена.Установить(fo.Справочники.ДополнительныеОтчетыИОбработки.ПустаяСсылка())
    result = {"тест": "C"}
    try:
        mo = connect("wim_mo")
        epf, tmp = create_mo_epf(mo, "внВыгрузкаКотировокМО_ФО")
        epf.АдресWS = external_ib(mo)
        epf.Период = date_1c(mo, TEST_DATE)
        calendars = query(mo, "ВЫБРАТЬ ПЕРВЫЕ 1 К.Ссылка КАК Ссылка ИЗ Справочник.ПроизводственныеКалендари КАК К "
                              "УПОРЯДОЧИТЬ ПО К.Код")
        if calendars:
            epf.ПроизводственныйКалендарь = calendars[0]["Ссылка"]
        rub = query(mo, 'ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = "643"')[0]["Ссылка"]
        for k in range(1, 4):
            # Колонка Актив - справочник Активы МО; тестовые активы стенда имеют внешний код T9532_SHn.
            sec = query(mo, "ВЫБРАТЬ Ак.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК Ак "
                            "ГДЕ Ак.ВнешнийКод = &Код", {"Код": share_code(k)})[0]["Ссылка"]
            row = epf.Котировки.Добавить()
            row.Период = date_1c(mo, TEST_DATE)
            row.Актив = sec
            row.Валюта = rub
            row.ВнешнийКод = share_code(k)
            row.РыночнаяЦена = 100 + k
            row.Доходность = 10 + k
        started = time.perf_counter()
        try:
            epf.Опубликовать()
        except Exception as exc:  # noqa: BLE001
            result["исключение"] = str(exc)[:400]
        result["секунд"] = round(time.perf_counter() - started, 1)
        with open(os.path.join(out_dir, "test_c_mo_log.txt"), "w", encoding="utf-8") as f:
            f.write(epf.ТекстовыйЛог.ПолучитьТекст())
        os.remove(tmp)
    finally:
        fo.Константы.ОперацииПослеОбмена.Установить(fo.ЗначениеИзСтрокиВнутр(saved))
    log("C.", result)
    return result


def collect(fo, since):
    rows = query(fo, """
        ВЫБРАТЬ
            З.КлючеваяОперация.Имя КАК Ключ,
            З.ДатаНачалаЗамера КАК Начало,
            З.ДатаОкончания КАК Окончание,
            З.ВремяВыполнения КАК Время,
            З.ВесЗамера КАК Вес,
            З.Комментарий КАК Комментарий,
            З.ВыполненСОшибкой КАК Ошибка,
            З.НомерСеанса КАК Сеанс,
            З.ДатаЗаписиЛокальная КАК Записано
        ИЗ
            РегистрСведений.ЗамерыВремени КАК З
        ГДЕ
            З.ДатаЗаписиЛокальная >= &Начало
            И З.КлючеваяОперация.Имя ПОДОБНО "ОбменБэкОфис.%"
        УПОРЯДОЧИТЬ ПО
            Начало""", {"Начало": since})
    result = []
    for r in rows:
        comment = r["Комментарий"] or ""
        extra = comment
        try:
            extra = json.loads(comment).get("ДопИнф", comment)
        except ValueError:
            pass
        result.append({
            "ключ": r["Ключ"], "начало_мс": float(r["Начало"]), "окончание_мс": float(r["Окончание"] or 0),
            "время_с": float(r["Время"]), "вес": float(r["Вес"]), "комментарий": extra,
            "ошибка": bool(r["Ошибка"]), "сеанс": int(r["Сеанс"]), "записано": str(r["Записано"]),
        })
    return result


def main():
    """python run_measure_tests.py start | A [портфелей потоков] | B | C | collect - шаги одного прогона."""
    step = sys.argv[1]
    current = os.path.join(RESULTS, "current.json")
    if step == "start":
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(RESULTS, stamp)
        os.makedirs(out_dir, exist_ok=True)
        fo = connect("wim_fo")
        state = {"out_dir": out_dir, "начало": fo.XMLСтрока(fo.ТекущаяДатаСеанса()), "тесты": []}
        with open(current, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        log("Прогон начат:", state["начало"], out_dir)
        return
    with open(current, encoding="utf-8") as f:
        state = json.load(f)
    out_dir = state["out_dir"]
    if step in ("A", "B", "C"):
        if step == "A" and len(sys.argv) >= 4:
            state["тесты"].append(test_a_positions(out_dir, int(sys.argv[2]), int(sys.argv[3])))
        else:
            runner = {"A": test_a_positions, "B": test_b_mandates, "C": test_c_quotes}[step]
            state["тесты"].append(runner(out_dir))
        with open(current, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        return
    fo = connect("wim_fo")
    since = date_1c(fo, datetime.datetime.fromisoformat(state["начало"]))
    exts = fo.РасширенияКонфигурации.Получить()
    ext_info = []
    for i in range(exts.Количество()):
        e = exts.Получить(i)
        if e.Имя in ("FO_KeyOpsPerf", "FO_PositionLoadOpt"):
            ext_info.append({"имя": e.Имя, "версия": e.Версия, "активно": bool(e.Активно),
                             "безопасный_режим": bool(e.БезопасныйРежим)})
    data = {"начало": state["начало"], "тесты": state["тесты"], "расширения": ext_info,
            "замеры_включены": bool(fo.Константы.ВыполнятьЗамерыПроизводительности.Получить()),
            "замеры": collect(fo, since)}
    with open(os.path.join(out_dir, "measurements.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    log(f"Записей замеров: {len(data['замеры'])}; результаты: {out_dir}")


if __name__ == "__main__":
    main()
