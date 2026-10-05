# -*- coding: utf-8 -*-
"""Прогон тестов замеров этапа 3 (IMDEV-9530): исполнение сделок, упаковка данных, постконтроль лимитов.

База: разработческая ФО (WIN_FO_server) с расширением FO_KeyOpsPerf. Процедуры, которые в базе выполняют
регламентные задания, запускаются фоновыми заданиями с тем же методом, то есть в серверном контексте:
модули ТорговаяЧастьПовтИсп, ИсполнителиПолныеПрава и модуль документа ИсполнениеПоСделке во внешнем
соединении не компилируются.

  E <дата> <метка>  Исполнение сделок: фоновое задание ИсполнениеСделок(дата) (путь регламентного задания);
                    число документов исполнения, их проведение и остаток плановой позиции по тестовым сделкам
                    T9530 на дату до и после. Сделки загружает prepare_deals.py.
  M                 Ручной запуск обработки ГрупповоеИсполнениеСделок с пустой таблицей (путь формы).
  U                 Упаковка данных: фоновое задание УпаковкаДанных; число записей сокращаемых регистров и
                    архивированных проверок лимитов до и после.
  P <вариант> [N]   Постконтроль лимитов: фоновое задание ПроверкаПоЛимитам. На время теста в константу
                    НастройкиРассылкиПоЛимитам пишется тестовая настройка, после теста исходное значение
                    возвращается. Варианты:
                      пустая      - настройка без портфелей (досрочный выход с ошибкой настройки);
                      неактивные  - 2 портфеля T9532, временно отмеченные неактивными (досрочный выход);
                      отказ       - N портфелей, дата проверки 02.10.2026: позиция не загружена;
                      рассылка    - N портфелей, дата 29.09.2026, тестовая настройка рассылки писем
                                    "T9530 тест рассылки" (адрес на домене example.invalid): ведомость встает в
                                    очередь, запись очереди после теста удаляется;
                      успех       - N портфелей, дата 29.09.2026, без рассылки писем.
                    Для сравнения с расширением и без него сохраняются строки результата КэшВмКратко.
  collect           Записи ЗамерыВремени прогона (ключи этапа 3 и ОбменБэкОфис.*) в measurements.json.

    python run_stage3_tests.py start | E <дата> <метка> | M | U | P <вариант> [N] [метка] | collect
"""
import datetime
import glob
import json
import os
import sys
import time

STAND = glob.glob(r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО')[0]
sys.path.insert(0, STAND)
from stand_common import PREFIX, connect, date_1c, query  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
CURRENT = os.path.join(RESULTS, "current_stage3.json")
JOB_MODULE = "АванкорВыполнениеРегламентныхЗаданий"
PACK_REGISTERS = ["БиржевыеТранзакции", "БиржевыеТранзакцииНеторговые", "БиржевыеЗаявкиВнешние",
                  "СообщенияАдаптеров", "СведенияОБиржевыхДисконтах"]
MAILING_NAME = "T9530 тест рассылки"
MAILING_ADDRESS = "t9530-test@example.invalid"
KEY_FILTER = """
            (З.КлючеваяОперация.Имя ПОДОБНО "ИсполнениеСделок%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "УпаковкаДанных%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "ПроверкаЛимитов.%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "ОбменБэкОфис.%")"""


def log(*args):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *args, flush=True)


def now_1c(fo):
    return fo.XMLСтрока(fo.ТекущаяДатаСеанса())


def measurements(fo, since_xml):
    since = date_1c(fo, datetime.datetime.fromisoformat(since_xml))
    rows = query(fo, f"""
        ВЫБРАТЬ
            З.КлючеваяОперация.Имя КАК Ключ,
            З.ДатаНачалаЗамера КАК Начало,
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
            И {KEY_FILTER}
        УПОРЯДОЧИТЬ ПО
            Начало""", {"Начало": since})
    result = []
    for r in rows:
        comment = r["Комментарий"] or ""
        try:
            comment = json.loads(comment).get("ДопИнф", comment)
        except ValueError:
            pass
        result.append({"ключ": r["Ключ"], "начало_мс": float(r["Начало"]), "время_с": float(r["Время"]),
                       "вес": float(r["Вес"]), "комментарий": comment, "ошибка": bool(r["Ошибка"]),
                       "сеанс": int(r["Сеанс"]), "записано": str(r["Записано"])})
    return result


def run_job(fo, method, params=None, timeout=7200):
    """Фоновое задание с методом регламентного задания; ожидание завершения и состояние."""
    args = fo.NewObject("Массив")
    for value in params or []:
        args.Добавить(value)
    started = time.time()
    job = fo.ФоновыеЗадания.Выполнить(f"{JOB_MODULE}.{method}", args, "", f"IMDEV-9530 этап 3: {method}")
    uid = job.УникальныйИдентификатор
    while True:
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно or time.time() - started > timeout:
            break
        time.sleep(1)
    state = fo.String(job.Состояние)
    error = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке) if job.ИнформацияОбОшибке is not None else ""
    seconds = round(time.time() - started, 1)
    log(f"   фоновое задание {method}: {state}, {seconds} с", error.split("\n")[0][:300])
    return {"метод": method, "состояние": state, "ошибка": error, "длительность_с": seconds}


def count_records(fo, table, condition=""):
    return int(query(fo, f"ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Н ИЗ {table} КАК Т {condition}")[0]["Н"])


def execution_state(fo, day):
    """Документы исполнения и остаток плановой позиции по тестовым сделкам T9530 с датой поставки day."""
    params = {"Дата": date_1c(fo, day)}
    docs = query(fo, """
        ВЫБРАТЬ
            КОЛИЧЕСТВО(*) КАК Документов,
            СУММА(ВЫБОР КОГДА Д.Проведен ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК Проведено,
            КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Д.Сделка) КАК Сделок,
            КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Д.Портфель) КАК Портфелей
        ИЗ
            Документ.ИсполнениеПоСделке КАК Д
        ГДЕ
            Д.Сделка.ВнешнийКод ПОДОБНО "T9530%"
            И Д.Сделка.ДатаПоставки = &Дата""", params)[0]
    # Измерения выбираются явно: без них виртуальная таблица сворачивает остатки в одну строку с чистой суммой.
    balance = query(fo, """
        ВЫБРАТЬ
            О.Сделка КАК Сделка,
            О.Портфель КАК Портфель,
            О.Актив КАК Актив,
            О.КоличествоОстаток КАК Количество
        ИЗ
            РегистрНакопления.ПлановаяПозиция.Остатки(, Сделка.ВнешнийКод ПОДОБНО "T9530%"
                И Сделка.ДатаПоставки = &Дата) КАК О""", params)
    return {"документов": int(docs["Документов"]), "проведено": int(docs["Проведено"] or 0),
            "сделок": int(docs["Сделок"]), "портфелей": int(docs["Портфелей"]),
            "строк_остатка": len(balance), "сумма_модулей_остатка": sum(abs(float(r["Количество"])) for r in balance)}


def test_e_execution(fo, day, label):
    log(f"E. Исполнение сделок на {day:%d.%m.%Y} ({label})")
    before = execution_state(fo, day)
    job = run_job(fo, "ИсполнениеСделок", [date_1c(fo, day.replace(hour=18))])
    after = execution_state(fo, day)
    log("   до:", before, "после:", after)
    return {"тест": "E", "метка": label, "дата": day.strftime("%d.%m.%Y"), "задание": job,
            "до": before, "после": after}


def test_m_manual(fo):
    log("M. Ручной запуск, таблица сделок пустая")
    processor = fo.Обработки.ГрупповоеИсполнениеСделок.Создать()
    processor.СоздатьДокументыИсполнения(False)
    return {"тест": "M", "строк_сделок": processor.Сделки.Количество(), "адрес_результата": processor.АдресРезультата}


def packing_state(fo):
    state = {r: count_records(fo, f"РегистрСведений.{r}") for r in PACK_REGISTERS}
    for archived in (True, False):
        state[f"КэшВмОписания.Архив={archived}"] = count_records(
            fo, "РегистрСведений.КэшВмОписания", f"ГДЕ Т.Архив = {'ИСТИНА' if archived else 'ЛОЖЬ'}")
    state["КэшВмКратко.вместилищ"] = int(query(
        fo, "ВЫБРАТЬ КОЛИЧЕСТВО(РАЗЛИЧНЫЕ К.Вместилище) КАК Н ИЗ РегистрСведений.КэшВмКратко КАК К")[0]["Н"])
    return state


def test_u_packing(fo):
    log("U. Упаковка данных")
    before = packing_state(fo)
    log("   до:", before)
    job = run_job(fo, "УпаковкаДанных")
    after = packing_state(fo)
    log("   после:", after)
    return {"тест": "U", "задание": job, "до": before, "после": after}


def test_u_finish(fo, before):
    """Дожидается уже запущенного задания упаковки (если процесс ожидания был остановлен) и фиксирует итог."""
    log("U. Упаковка данных: ожидание запущенного задания")
    jobs = fo.ФоновыеЗадания.ПолучитьФоновыеЗадания(
        fo.NewObject("Структура", "Наименование", "IMDEV-9530 этап 3: УпаковкаДанных"))
    job = max((jobs.Получить(i) for i in range(jobs.Количество())), key=lambda j: fo.XMLСтрока(j.Начало))
    uid = job.УникальныйИдентификатор
    while job.Состояние == fo.СостояниеФоновогоЗадания.Активно:
        time.sleep(30)
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
    error = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке) if job.ИнформацияОбОшибке is not None else ""
    started, finished = fo.XMLСтрока(job.Начало), fo.XMLСтрока(job.Конец)
    seconds = (datetime.datetime.fromisoformat(finished) - datetime.datetime.fromisoformat(started)).total_seconds()
    after = packing_state(fo)
    log("   задание:", fo.String(job.Состояние), started, finished, "после:", after)
    return {"тест": "U", "задание": {"метод": "УпаковкаДанных", "состояние": fo.String(job.Состояние), "ошибка": error,
                                     "длительность_с": seconds},
            "до": before, "после": after, "начало": started, "окончание": finished}


def cache_containers(fo):
    rows = query(fo, "ВЫБРАТЬ РАЗЛИЧНЫЕ К.Вместилище КАК Вместилище ИЗ РегистрСведений.КэшВмКратко КАК К")
    return {fo.String(r["Вместилище"]) for r in rows}


def cache_rows(fo, container):
    """Строки результата проверки одного вместилища в виде, пригодном для сравнения прогонов.

    Поле Замер не берется: это хронометраж самой проверки (миллисекунды на строку результата,
    ПроверкаЛимитов.ОбработатьОписаниеКраткое), он меняется от прогона к прогону.
    """
    rows = query(fo, """
        ВЫБРАТЬ
            К.Фокус КАК Фокус,
            К.Лимит КАК Лимит,
            К.Зона КАК Зона,
            К.Отказ КАК Отказ,
            К.Базис КАК Базис,
            К.ПустаяПозиция КАК ПустаяПозиция,
            К.ОшибкаСбораДанных КАК ОшибкаСбораДанных,
            К.ПроверкаПропущена КАК ПроверкаПропущена
        ИЗ
            РегистрСведений.КэшВмКратко КАК К
        ГДЕ
            К.Вместилище = &Вместилище""", {"Вместилище": fo.NewObject("УникальныйИдентификатор", container)})
    return sorted("|".join([fo.String(r["Фокус"]), fo.String(r["Лимит"]), fo.String(r["Зона"]), str(bool(r["Отказ"])),
                            fo.String(r["Базис"]), str(bool(r["ПустаяПозиция"])),
                            str(bool(r["ОшибкаСбораДанных"])), str(bool(r["ПроверкаПропущена"]))]) for r in rows)


def test_portfolios(fo, count):
    return [r["Ссылка"] for r in query(fo, f"""
        ВЫБРАТЬ ПЕРВЫЕ {count} П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П
        ГДЕ П.ВнешнийКод ПОДОБНО "{PREFIX}%" УПОРЯДОЧИТЬ ПО П.ВнешнийКод""")]


def mailing_setting(fo):
    rows = query(fo, "ВЫБРАТЬ Н.Ссылка КАК Ссылка ИЗ Справочник.НастройкиРассылкиПисем КАК Н ГДЕ Н.Наименование = &Имя",
                 {"Имя": MAILING_NAME})
    if rows:
        return rows[0]["Ссылка"]
    item = fo.Справочники.НастройкиРассылкиПисем.СоздатьЭлемент()
    item.Наименование = MAILING_NAME
    item.РежимРассылки = 0
    address = item.СписокАдресов.Добавить()
    address.Адрес = MAILING_ADDRESS
    address.ВключенВРассылку = True
    item.Записать()
    log("   создана настройка рассылки", MAILING_NAME)
    return item.Ссылка


def set_inactive(fo, portfolios, inactive):
    for portfolio in portfolios:
        record_set = fo.РегистрыСведений.НеактивныеПортфели.СоздатьНаборЗаписей()
        record_set.Отбор.Портфель.Установить(portfolio)
        if inactive:
            record = record_set.Добавить()
            record.Портфель = portfolio
            record.НеАктивен = True
        record_set.Записать()


def remove_mailing_queue(fo, containers):
    removed = 0
    for container in containers:
        record_set = fo.РегистрыСведений.КэшВмРассылка.СоздатьНаборЗаписей()
        record_set.Отбор.Вместилище.Установить(fo.NewObject("УникальныйИдентификатор", container))
        record_set.Прочитать()
        removed += record_set.Количество()
        record_set.Очистить()
        record_set.Записать()
    return removed


def test_p_postcontrol(fo, variant, count=20, label=""):
    log(f"P. Постконтроль лимитов: вариант {variant}, {count} портфелей {label}")
    portfolios = test_portfolios(fo, 2 if variant == "неактивные" else count)
    # Позиция тестовых портфелей стенда загружена на 29.09.2026; календарь смещения фактической позиции на dev не
    # задан, поэтому смещение - число календарных дней от текущей даты сеанса до 29.09.2026.
    today = datetime.datetime.fromisoformat(now_1c(fo)).date()
    offset = -(today - datetime.date(2026, 9, 29)).days if variant in ("рассылка", "успех") else 0
    constant = fo.Константы.НастройкиРассылкиПоЛимитам
    original = constant.Получить()
    original_value = original.Получить() if original is not None else None
    settings = fo.NewObject("Структура")
    focus = fo.NewObject("СписокЗначений")
    if variant != "пустая":
        for portfolio in portfolios:
            focus.Добавить(portfolio)
    settings.Вставить("СписокПортфелейГруппПортфелей", focus)
    settings.Вставить("Смещение", offset)
    if variant == "рассылка":
        settings.Вставить("НастройкаРассылкиПисем", mailing_setting(fo))
    mailing_before = count_records(fo, "РегистрСведений.КэшВмРассылка")
    containers_before = cache_containers(fo)
    if variant == "неактивные":
        set_inactive(fo, portfolios, True)
    constant.Установить(fo.NewObject("ХранилищеЗначения", settings))
    try:
        job = run_job(fo, "ПроверкаПоЛимитам")
    finally:
        constant.Установить(original)
        if variant == "неактивные":
            set_inactive(fo, portfolios, False)
    restored = constant.Получить()
    restored_value = restored.Получить() if restored is not None else None
    new_containers = cache_containers(fo) - containers_before
    mailing_after = count_records(fo, "РегистрСведений.КэшВмРассылка")
    removed = remove_mailing_queue(fo, new_containers) if variant == "рассылка" else 0
    return {"тест": "P", "вариант": variant, "метка": label, "портфелей_в_настройке": focus.Количество(),
            "смещение": offset, "задание": job,
            "константа_восстановлена": (original_value is None and restored_value is None)
                                       or fo.String(original_value) == fo.String(restored_value),
            "неактивных_после_теста": count_records(fo, "РегистрСведений.НеактивныеПортфели"),
            "очередь_рассылки_до": mailing_before, "очередь_рассылки_после_проверки": mailing_after,
            "удалено_из_очереди": removed,
            "очередь_рассылки_после_очистки": count_records(fo, "РегистрСведений.КэшВмРассылка"),
            "строки_результата": {name: cache_rows(fo, name) for name in new_containers}}


def extensions_info(fo):
    items = fo.РасширенияКонфигурации.Получить()
    info = []
    for i in range(items.Количество()):
        ext = items.Получить(i)
        if ext.Имя in ("FO_KeyOpsPerf", "FO_PositionLoadOpt"):
            info.append({"имя": ext.Имя, "версия": ext.Версия, "активно": bool(ext.Активно),
                         "безопасный_режим": bool(ext.БезопасныйРежим)})
    return info


def main():
    step = sys.argv[1]
    if step == "start":
        fo = connect("wim_fo")
        out_dir = os.path.join(RESULTS, "stage3_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(out_dir, exist_ok=True)
        state = {"out_dir": out_dir, "начало": now_1c(fo), "тесты": []}
        with open(CURRENT, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        log("Прогон начат:", state["начало"], out_dir)
        return
    with open(CURRENT, encoding="utf-8") as f:
        state = json.load(f)
    fo = connect("wim_fo")
    if step == "Ufinish":
        before = json.loads(sys.argv[2])
        entry = test_u_finish(fo, before)
        entry["расширения"] = extensions_info(fo)
        state["тесты"].append(entry)
        with open(CURRENT, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        return
    if step in ("E", "M", "U", "P"):
        started = now_1c(fo)
        if step == "E":
            entry = test_e_execution(fo, datetime.datetime.fromisoformat(sys.argv[2]), sys.argv[3])
        elif step == "M":
            entry = test_m_manual(fo)
        elif step == "U":
            entry = test_u_packing(fo)
        else:
            count = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            label = sys.argv[4] if len(sys.argv) > 4 else ""
            entry = test_p_postcontrol(fo, sys.argv[2], count, label)
        entry["начало"] = started
        entry["окончание"] = now_1c(fo)
        entry["расширения"] = extensions_info(fo)
        state["тесты"].append(entry)
        with open(CURRENT, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        return
    data = {**{k: v for k, v in state.items() if k not in ("out_dir", "начало", "тесты")},
            "начало": state["начало"], "тесты": state["тесты"], "расширения": extensions_info(fo),
            "замеры_включены": bool(fo.Константы.ВыполнятьЗамерыПроизводительности.Получить()),
            "замеры": measurements(fo, state["начало"])}
    with open(os.path.join(state["out_dir"], "measurements.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    log(f"Записей замеров: {len(data['замеры'])}; результаты: {state['out_dir']}")
    for m in data["замеры"]:
        log(f"   {m['ключ']:50} вес {m['вес']:>6g} {m['время_с']:>9.3f} с  ошибка={m['ошибка']}  {m['комментарий']}")


if __name__ == "__main__":
    main()
