# -*- coding: utf-8 -*-
"""Прогон тестов замеров этапа 5 (IMDEV-9530): внешние обработки загрузок на dev ФО.

Обработки: загрузка депозитов (внЗагрузкаДепозитовИзВнешнихИсточников), котировки ММВБ (внЗагрузкаКотировок),
индексы (внЗагрузкаИндексов), доп. реквизит TCRIS (ЗагрузкаДопРеквизитаTCRIS). Каждая сравнивается в двух версиях:
«ориг» (ОРИГИНАЛЫ) и «замеры» (ЗАМЕРЫ); обе версии регистрируются в один элемент справочника дополнительных
обработок, двоичные данные и настройки меняются перед прогоном. Перед каждым сценарием тестовая обработка
T9530_ТестРОСТ (сценарий СбросЗагрузок) возвращает данные загрузок в исходное состояние, после сценария снимается
результат загрузки, поэтому версии сравниваются на одинаковом исходном состоянии.

Внешние источники заменяет mock_load_services.py (депозиты ДУ/ПИФ, TIBCO котировок, MICROAPI индексов); для
котировок и индексов имена amaptibco и AMFLOW на время теста направлены в hosts на 127.0.0.1. Calipso и Rates
(SQL Server) с dev недоступны: депозиты Calipso - 0, TCRIS проверяется только веткой недоступности Rates.
Команды запускаются как регламентное задание: ДополнительныеОтчетыИОбработки.ВыполнитьКоманду в фоновом задании.

    python run_stage5_tests.py prep <серия>                тестовые справочники, регистрация обработок
    python run_stage5_tests.py run <серия> <ориг|замеры> [сценарии через запятую] [--off]
                                                            --off - константа замеров выключена на время прогона
    python run_stage5_tests.py collect <серия>             записи ЗамерыВремени по ключам загрузок
"""
import datetime
import glob
import json
import os
import shutil
import sys
import tempfile
import time

STAND = glob.glob(r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО')[0]
sys.path.insert(0, STAND)
from stand_common import connect, date_1c, query  # noqa: E402
from run_stage4_tests import (ensure_property, ensure_strategy, find_ref, log, now_iso, register_epf,  # noqa: E402
                              run_harness, test_epf)

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
RESULTS = os.path.join(HERE, "results")
RULES = os.path.join(RESULTS, "mock_load_rules.json")
EPF_DIRS = {"ориг": os.path.join(HERE, "epf", "ОРИГИНАЛЫ"), "замеры": os.path.join(TASK, "ЗАМЕРЫ")}
PREFIX = "T9530Z"
# Обработка: (файл EPF, имя объекта в справочнике)
EPF = {
    "депозиты": ("внЗагрузкаДепозитовИзВнешнихИсточников", "внЗагрузкаДепозитовИзВнешнихИсточников"),
    "котировки": ("внЗагрузкаКотировокММВБ", "внЗагрузкаКотировок"),
    "индексы": ("внЗагрузкаИндексовФО", "внЗагрузкаИндексов"),
    "tcris": ("ЗагрузкаДопРеквизитаTCRIS", "ЗагрузкаДопРеквизитаTCRIS"),
}
KEYS = ("ЗагрузкаДепозитов", "ЗагрузкаКотировокММВБ", "ЗагрузкаИндексов", "ЗагрузкаTCRIS")
KEY_FILTER = " ИЛИ ".join(f'З.КлючеваяОперация.Имя ПОДОБНО "{k}%"' for k in KEYS)
MOCK = "http://127.0.0.1:18540"
MOCK_DOWN = "http://127.0.0.1:18541"
SHARES = [f"{PREFIX}Q{i:02d}" for i in range(1, 6)]
INDEXES = [f"{PREFIX}IX1", f"{PREFIX}IX2"]
PORTFOLIOS = {"D1": "ДУ 1", "D2": "ДУ 2", "P1": "ПИФ 1"}
# Депозитные места хранения: номер -> (портфель, идентификатор депозита в источнике)
PLACES = {1: ("D1", f"{PREFIX}-DU-01"), 2: ("D1", f"{PREFIX}-DU-02"), 3: ("D2", f"{PREFIX}-DU-03"),
          4: ("P1", f"{PREFIX}-PIF-01"), 5: ("D2", f"{PREFIX}-DU-05")}
CLOSED_PLACE = 5  # закрытый депозит: позиция в ФО есть, в источнике нет - загрузка ее удаляет
SCENARIOS = ["Д.Успех", "Д.Рассылка", "Д.Сбой", "К.Успех", "К.Сбой", "К.НеПроведен", "И.Успех", "И.Сбой", "T.Недоступна"]
# Вызов процедур загрузки как из серверных методов форм (объект обработки без команды): общих замеров нет,
# замеры шагов пишутся из процедур.
FORM_SCENARIOS = ["Д.Форма", "К.Форма", "И.Форма"]
OFF_SCENARIOS = ["Д.Успех", "К.Успех", "И.Успех", "T.Недоступна"]


def state_path(series):
    return os.path.join(RESULTS, f"stage5_{series}.json")


def load_state(series):
    path = state_path(series)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"series": series, "runs": []}


def save_state(state):
    os.makedirs(RESULTS, exist_ok=True)
    with open(state_path(state["series"]), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def write_rules(rules):
    os.makedirs(RESULTS, exist_ok=True)
    with open(RULES, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def s(fo, value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return fo.String(value)


# ---------------------------------------------------------------- справочники

def ensure_shares(fo):
    """Тестовые акции с тикером на ММВБ (ДополнитьТаблицуСсылками котировок и АктивыПоТикеру индексов ищут бумагу
    по БиржиЛистинга.Тикер) и активы для них."""
    sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 А.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК А ГДЕ НЕ А.ПометкаУдаления "
                          "И А.Эмитент <> ЗНАЧЕНИЕ(Справочник.Контрагенты.ПустаяСсылка) И НЕ А.Наименование ПОДОБНО \"T95%\" "
                          "УПОРЯДОЧИТЬ ПО А.Наименование")
    mmvb = fo.Справочники.Биржи.ММВБ
    for code in SHARES:
        name = f"{PREFIX} Акция {code}"
        ref = find_ref(fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК А ГДЕ А.Наименование = &Имя", {"Имя": name})
        if ref is None:
            obj = sample.Скопировать()
            obj.Наименование = name
            obj.НаименованиеПолное = name
            obj.КраткоеНаименование = code
            obj.ВнешнийКод = code
            obj.ISIN = ""
            obj.НомерГосРегистрацииВыпуска = ""
            obj.СобиратьНаименованиеАвтоматически = False
            obj.БиржиЛистинга.Очистить()
            row = obj.БиржиЛистинга.Добавить()
            row.Биржа = mmvb
            row.Тикер = code
            obj.Записать()
            ref = obj.Ссылка
            log(f"  создана акция {name}")
        asset = find_ref(fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А ГДЕ А.Объект = &Объект", {"Объект": ref})
        if asset is None:
            obj = fo.Справочники.Активы.СоздатьЭлемент()
            obj.Объект = ref
            obj.ВидАктива = ref.ВидАктива
            obj.Эмитент = ref.Эмитент
            obj.ВалютаНоминальнойСтоимости = ref.ВалютаНоминальнойСтоимости
            obj.Наименование = name
            obj.ВнешнийКод = code
            obj.Записать()
            log(f"  создан актив {name}")


def ensure_indexes(fo):
    rub = fo.Справочники.Валюты.НайтиПоНаименованию("RUB")
    refs = []
    for i, code in enumerate(INDEXES, 1):
        ref = find_ref(fo, "ВЫБРАТЬ Инд.Ссылка КАК Ссылка ИЗ Справочник.Индексы КАК Инд ГДЕ Инд.КодИндекса = &Код", {"Код": code})
        if ref is None:
            obj = fo.Справочники.Индексы.СоздатьЭлемент()
            obj.Наименование = f"{PREFIX} Индекс {i}"
            obj.КодИндекса = code
            obj.ВнешнийКод = code
            obj.Валюта = rub
            obj.Биржа = fo.Справочники.Биржи.ММВБ
            obj.Записать()
            ref = obj.Ссылка
            log(f"  создан индекс {code}")
        refs.append(ref)
    return refs


def ensure_portfolios(fo, strategy):
    sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                          "ГДЕ НЕ П.ПометкаУдаления И НЕ П.Предопределенный И П.ВнешнийКод = \"\" УПОРЯДОЧИТЬ ПО П.Наименование")
    refs = {}
    for key, title in PORTFOLIOS.items():
        code = f"{PREFIX}{key}"
        ref = find_ref(fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П ГДЕ П.ВнешнийКод = &Код", {"Код": code})
        if ref is None:
            obj = sample.Скопировать()
            obj.Наименование = f"{PREFIX} депозиты {title}"
            obj.ВнешнийКод = code
            obj.НомерДоговора = code
            obj.КодПортфеля = code
            obj.Записать()
            ref = obj.Ссылка
            log(f"  создан портфель {code}")
        refs[key] = ref
    return refs


def ensure_deposit_places(fo, portfolios, strategy, id_property, test_ref):
    """Депозитные счета (копии счета FO_FO депозит RUB), места хранения (создает подписка синхронизации мест хранения),
    идентификатор депозита в доп. сведениях места хранения и субпортфели тестовых портфелей."""
    sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 Сч.Ссылка КАК Ссылка ИЗ Справочник.БанковскиеСчета КАК Сч "
                          "ГДЕ Сч.ВидСчета = ЗНАЧЕНИЕ(Перечисление.ВидБанковскогоСчета.Депозитный) И НЕ Сч.ПометкаУдаления "
                          "И Сч.Наименование ПОДОБНО \"%RUB%\"")
    places = {}
    records = fo.NewObject("Массив")
    for n, (portfolio_key, deposit_id) in PLACES.items():
        name = f"{PREFIX} депозит {n:02d}"
        account = find_ref(fo, "ВЫБРАТЬ Сч.Ссылка КАК Ссылка ИЗ Справочник.БанковскиеСчета КАК Сч ГДЕ Сч.Наименование = &Имя",
                           {"Имя": name})
        if account is None:
            obj = sample.Скопировать()
            obj.Наименование = name
            obj.ВнешнийКод = f"{PREFIX}_DEP{n:02d}"
            obj.Записать()
            account = obj.Ссылка
            log(f"  создан депозитный счет {name}")
        place = find_ref(fo, "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.МестаХранения КАК М ГДЕ М.Объект = &Объект",
                         {"Объект": account})
        if place is None:
            obj = fo.Справочники.МестаХранения.СоздатьЭлемент()
            obj.Объект = account
            obj.Наименование = name
            obj.ВнешнийКод = f"{PREFIX}_DEP{n:02d}"
            obj.Записать()
            place = obj.Ссылка
            log(f"  создано место хранения {name}")
        record = fo.NewObject("Структура")
        record.Вставить("Объект", place)
        record.Вставить("Свойство", id_property)
        record.Вставить("Значение", deposit_id)
        records.Добавить(record)
        sub =find_ref(fo, "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Справочник.Субпортфели КАК С ГДЕ С.МестоХранения = &М",
                       {"М": place})
        if sub is None:
            obj = fo.Справочники.Субпортфели.СоздатьЭлемент()
            obj.Наименование = name
            obj.КодСчета = f"{PREFIX}_DEP{n:02d}"
            obj.Портфель = portfolios[portfolio_key]
            obj.МестоХранения = place
            obj.Стратегия = strategy
            obj.Записать()
            sub = obj.Ссылка
            log(f"  создан субпортфель {name}")
        places[n] = {"счет": account, "место": place, "субпортфель": sub, "портфель": portfolios[portfolio_key]}
    # Доп. сведения пишет тестовая обработка: подписка на запись регистра во внешнем соединении не компилируется.
    params = fo.NewObject("Структура")
    params.Вставить("Сценарий", "Сведения")
    params.Вставить("Записи", records)
    out = run_harness(fo, test_ref, params, "идентификаторы депозитов")
    if out.get("ошибка") or out["ошибка_задания"]:
        raise SystemExit("Идентификаторы депозитов не записаны: " + (out.get("ошибка") or out["ошибка_задания"]))
    return places


def context(fo, test_ref):
    """Ссылки тестовых данных (после prep)."""
    strategy = ensure_strategy(fo)
    id_property = ensure_property(fo, "ИдентификаторДепозита", "Строка")
    portfolios = ensure_portfolios(fo, strategy)
    places = ensure_deposit_places(fo, portfolios, strategy, id_property, test_ref)
    return {"portfolios": portfolios, "places": places, "indexes": ensure_indexes(fo),
            "rub_asset": find_ref(fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А "
                                      "ГДЕ А.Объект = &В", {"В": fo.Справочники.Валюты.НайтиПоНаименованию("RUB")})}


def step_prep(fo, series):
    ensure_shares(fo)
    test_ref = test_epf(fo)
    ctx = context(fo, test_ref)
    for key, (file_name, object_name) in EPF.items():
        register_epf(fo, object_name, os.path.join(EPF_DIRS["ориг"], file_name + ".epf"), None)
    state = load_state(series)
    state["prep"] = {"акции": SHARES, "индексы": INDEXES, "портфели": {k: s(fo, v) for k, v in ctx["portfolios"].items()},
                     "места": {str(n): {k: s(fo, v) for k, v in p.items()} for n, p in ctx["places"].items()},
                     "тестовая": s(fo, test_ref)}
    save_state(state)


# ---------------------------------------------------------------- настройки и правила заглушек

def deposit_rules():
    def du(n, value, prefix):
        return {"id": PLACES[n][1] if n else f"{PREFIX}-DU-99", "name": f"{PREFIX} депозит ДУ {n:02d}" if n else
                f"{PREFIX} депозит ДУ неизвестный", "marketvalue": value + 15.5, "day_interest": 1.25,
                "initialvalue": value, "currentvalue": value + 15.5, "currency": "RUB", "datestart": "2026-09-01",
                "datematurity": "2026-12-31", "interest": 12.5 + (n or 0) / 10, "agreements_prefix": prefix}
    return {
        "du": [du(1, 1000000, f"{PREFIX}D1"), du(2, 2000000, f"{PREFIX}D1"), du(3, 3000000, f"{PREFIX}D2"),
               du(0, 4000000, f"{PREFIX}D2")],
        "pif": [{"id": PLACES[4][1], "name": f"{PREFIX} депозит ПИФ 04", "marketvalue": 5000100, "day_interest": 2,
                 "initialvalue": 5000000, "currentvalue": 5000100, "currency": "RUB", "datestart": "2026-09-15",
                 "datematurity": "2027-03-15", "interest": 13.1},
                {"id": f"{PREFIX}-PIF-99", "name": f"{PREFIX} депозит ПИФ неизвестный", "marketvalue": 600000,
                 "day_interest": 0.5, "initialvalue": 590000, "currentvalue": 600000, "currency": "RUB",
                 "datestart": "2026-09-15", "datematurity": "2027-03-15", "interest": 11}],
    }


def quote_rules():
    rows = [{"code": c, "currency": "RUB", "close": 100 + i * 10.25, "market2": 100 + i * 10.2}
            for i, c in enumerate(SHARES, 1)]
    rows.append({"code": f"{PREFIX}Q99", "currency": "RUB", "close": 55.5, "market2": 55.4})
    return {"docs": [{"exchange": "ММВБ", "rows": rows},
                     {"exchange": "BLOOMBERG", "rows": [{"code": SHARES[0], "currency": "USD", "close": 1.5,
                                                         "market2": 1.5}]}]}


def index_rules():
    return {"data": [{"index": INDEXES[0], "currency": "RUB", "open": 2900.5, "max": 2950.75, "min": 2880.25,
                      "close": 2930.1, "volume": 123456789.5, "duration": 0, "yield": 0},
                     {"index": INDEXES[1], "currency": "RUB", "open": 1500.5, "max": 1510.5, "min": 1490.5,
                      "close": 1505.5, "volume": 98765432.1, "duration": 3.2, "yield": 11.5}],
            "composition": [{"index": INDEXES[0], "rows": [
                {"ticker": SHARES[0], "weight": 0.45, "freefloat": 0.3, "coeff": 1, "emission": 1000000, "cap": 2500000},
                {"ticker": SHARES[1], "weight": 0.55, "freefloat": 0.4, "coeff": 1, "emission": 2000000, "cap": 3500000},
                {"ticker": f"{PREFIX}Q99", "weight": 0.1, "freefloat": 0.1, "coeff": 1, "emission": 10, "cap": 10}]}]}


def deposit_settings(fo, test_ref, url, mail):
    settings = fo.NewObject("Структура")
    settings.Вставить("ОчищатьДепозитыПередЗагрузкой", False)
    settings.Вставить("ВебСервисДУ", f"{url}/du?wsdl")
    settings.Вставить("ВебСервисПИФ", f"{url}/pif?wsdl")
    settings.Вставить("Логин", "")
    settings.Вставить("Пароль", "")
    settings.Вставить("ОбработкаПерерасчетаСтоимости", test_ref)
    if mail:
        # Системная учетная запись dev не настроена (нет сервера исходящей почты): отправка падает в обработке.
        boxes = fo.NewObject("ТаблицаЗначений")
        boxes.Колонки.Добавить("ПочтовыйЯщик")
        boxes.Колонки.Добавить("Представление")
        row = boxes.Добавить()
        row.ПочтовыйЯщик = "t9530@example.invalid"
        row.Представление = "t9530@example.invalid"
        settings.Вставить("ПочтовыйЛогин", fo.Справочники.УчетныеЗаписиЭлектроннойПочты.СистемнаяУчетнаяЗаписьЭлектроннойПочты)
        settings.Вставить("СписокРассылки", fo.XMLСтрока(fo.NewObject("ХранилищеЗначения", boxes)))
    return settings


def quote_settings(fo):
    settings = fo.NewObject("Структура")
    settings.Вставить("ОбработкаЗагрузкиАктивов", fo.Справочники.ДополнительныеОтчетыИОбработки.ПустаяСсылка())
    settings.Вставить("КомандаЗагрузкиАктивов", "")
    settings.Вставить("ОсновнаяБиржаРепрайсинга", fo.Справочники.Биржи.ПустаяСсылка())
    return settings


def index_settings(fo):
    settings = fo.NewObject("Структура")
    settings.Вставить("ТестовыйРежим", False)
    settings.Вставить("СервисИсточник", 0)
    return settings


def set_settings(fo, ref, settings):
    item = ref.ПолучитьОбъект()
    item.ХранилищеНастроек = fo.NewObject("ХранилищеЗначения", settings)
    item.ОбменДанными.Загрузка = True
    item.Записать()


# ---------------------------------------------------------------- запуск и снимки

def epf_ref(fo, key):
    return find_ref(fo, "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления", {"Имя": EPF[key][1]})


def event_log(fo, since):
    table = fo.NewObject("ТаблицаЗначений")
    filt = fo.NewObject("Структура")
    filt.Вставить("ДатаНачала", since)
    fo.ВыгрузитьЖурналРегистрации(table, filt)
    out = []
    for i in range(table.Количество()):
        row = table.Получить(i)
        event = row.Событие or ""
        level = fo.String(row.Уровень)
        if not (any(m in event for m in ("IMDEV-9530", "Загрузка котировок", "Дополнительные отчеты и обработки"))
                or level == "Ошибка"):
            continue
        out.append({"дата": fo.String(row.Дата), "событие": event, "уровень": level,
                    "комментарий": (row.Комментарий or "")[:2000]})
    return out


def run_command(fo, ref, title, timeout=900):
    params = fo.NewObject("Структура")
    params.Вставить("ДополнительнаяОбработкаСсылка", ref)
    params.Вставить("ИдентификаторКоманды", "ФоновоеВыполнение")
    args = fo.NewObject("Массив")
    args.Добавить(params)
    args.Добавить(None)
    started = time.time()
    job = fo.ФоновыеЗадания.Выполнить("ДополнительныеОтчетыИОбработки.ВыполнитьКоманду", args, "",
                                      f"IMDEV-9530 этап 5: {title}")
    uid = job.УникальныйИдентификатор
    while True:
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно or time.time() - started > timeout:
            break
        time.sleep(1)
    seconds = round(time.time() - started, 1)
    error = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке) if job.ИнформацияОбОшибке is not None else ""
    messages = job.ПолучитьСообщенияПользователю(False)
    texts = [messages.Получить(i).Текст for i in range(messages.Количество())] if messages is not None else []
    log(f"   {title}: {fo.String(job.Состояние)}, {seconds} с", error.split("\n")[0][:300])
    return {"состояние": fo.String(job.Состояние), "длительность_с": seconds, "ошибка_задания": error,
            "сообщения": texts, "журнал": event_log(fo, job.Начало)}


def previous_working_day():
    day = datetime.date.today() - datetime.timedelta(days=1)
    while day.weekday() >= 5:
        day -= datetime.timedelta(days=1)
    return datetime.datetime(day.year, day.month, day.day)


def run_form_procedures(fo, test_ref, ref, loader, title):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "ПроцедурыЗагрузки")
    p.Вставить("ОбработкаСсылка", ref)
    p.Вставить("Вид", {"депозиты": "Депозиты", "котировки": "Котировки", "индексы": "Индексы"}[loader])
    day = previous_working_day()
    p.Вставить("ДатаНачала", date_1c(fo, day))
    p.Вставить("ДатаОкончания", date_1c(fo, day + datetime.timedelta(hours=23, minutes=59, seconds=59)))
    out = run_harness(fo, test_ref, p, title)
    return {"состояние": out["состояние"], "длительность_с": out["длительность_с"],
            "ошибка_задания": out.get("ошибка") or out["ошибка_задания"], "сообщения": out.get("сообщения", []),
            "журнал": []}


def quote_conflict(fo, test_ref, day):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "КонфликтКотировок")
    p.Вставить("Дата", date_1c(fo, day))
    p.Вставить("Актив", find_ref(fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А ГДЕ А.ВнешнийКод = &Код",
                                 {"Код": SHARES[0]}))
    p.Вставить("Биржа", find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 Б.Ссылка КАК Ссылка ИЗ Справочник.Биржи КАК Б "
                                     "ГДЕ Б.Ссылка <> ЗНАЧЕНИЕ(Справочник.Биржи.ММВБ) И НЕ Б.ПометкаУдаления "
                                     "УПОРЯДОЧИТЬ ПО Б.Наименование"))
    out = run_harness(fo, test_ref, p, "конфликт котировок")
    if out.get("ошибка") or out["ошибка_задания"]:
        raise SystemExit("Конфликт котировок не создан: " + (out.get("ошибка") or out["ошибка_задания"]))


def reset(fo, ctx, test_ref):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "СбросЗагрузок")
    today = query(fo, "ВЫБРАТЬ НАЧАЛОПЕРИОДА(&Д, ДЕНЬ) КАК Д", {"Д": fo.ТекущаяДатаСеанса()})[0]["Д"]
    p.Вставить("Дата", today)
    subs = fo.NewObject("Массив")
    accounts = fo.NewObject("Массив")
    for n, place in ctx["places"].items():
        subs.Добавить(place["субпортфель"])
        accounts.Добавить(place["счет"])
    p.Вставить("Субпортфели", subs)
    p.Вставить("Счета", accounts)
    closed = ctx["places"][CLOSED_PLACE]
    c = fo.NewObject("Структура")
    c.Вставить("Субпортфель", closed["субпортфель"])
    c.Вставить("МестоХранения", closed["место"])
    c.Вставить("Портфель", closed["портфель"])
    c.Вставить("Актив", ctx["rub_asset"])
    c.Вставить("Сумма", 700000)
    p.Вставить("ЗакрытыйДепозит", c)
    p.Вставить("НачалоКотировок", date_1c(fo, datetime.datetime.now() - datetime.timedelta(days=15)))
    p.Вставить("КонецКотировок", date_1c(fo, datetime.datetime.now() + datetime.timedelta(days=1)))
    idx = fo.NewObject("Массив")
    for ref in ctx["indexes"]:
        idx.Добавить(ref)
    p.Вставить("Индексы", idx)
    out = run_harness(fo, test_ref, p, "сброс данных загрузок")
    if out.get("ошибка") or out["ошибка_задания"]:
        raise SystemExit("Сброс данных не выполнен: " + (out.get("ошибка") or out["ошибка_задания"]))


def deposits_snapshot(fo, ctx):
    subs = fo.NewObject("Массив")
    accounts = fo.NewObject("Массив")
    for place in ctx["places"].values():
        subs.Добавить(place["субпортфель"])
        accounts.Добавить(place["счет"])
    rows = query(fo, """ВЫБРАТЬ Р.Дата КАК Дата, Р.МестоХранения КАК Место, Р.Субпортфель КАК Субпортфель,
            Р.Портфель КАК Портфель, Р.Актив КАК Актив, Р.Количество КАК Количество, Р.Стоимость КАК Стоимость,
            Р.НКД КАК НКД, Р.СуммаДенежныхСредствСЗадолженностью КАК Сумма
        ИЗ РегистрСведений.ВТБ_ФактическаяПозицияДепозитов КАК Р
        ГДЕ Р.Субпортфель В (&С) И Р.Дата >= НАЧАЛОПЕРИОДА(&Д, ДЕНЬ)
        УПОРЯДОЧИТЬ ПО Р.Субпортфель.Наименование""", {"С": subs, "Д": fo.ТекущаяДатаСеанса()})
    rates = query(fo, """ВЫБРАТЬ Сч.Наименование КАК Счет, Сч.ПроцентнаяСтавка КАК Ставка
        ИЗ Справочник.БанковскиеСчета КАК Сч ГДЕ Сч.Ссылка В (&Сч) УПОРЯДОЧИТЬ ПО Сч.Наименование""", {"Сч": accounts})
    return {"позиции": [{k: s(fo, v) for k, v in r.items()} for r in rows],
            "ставки": [{k: s(fo, v) for k, v in r.items()} for r in rates]}


def quotes_snapshot(fo):
    rows = query(fo, """ВЫБРАТЬ Стр.Ссылка.Дата КАК Дата, Стр.Ссылка.Проведен КАК Проведен, Стр.Актив КАК Актив,
            Стр.ПризнаваемаяКотировка КАК Признаваемая, Стр.ЦенаЗакрытия КАК Закрытие, Стр.РыночнаяЦена2 КАК Рыночная2,
            Стр.Валюта КАК Валюта
        ИЗ Документ.КотировкиЦБНаБирже.Котировки КАК Стр
        ГДЕ Стр.Ссылка.Биржа = ЗНАЧЕНИЕ(Справочник.Биржи.ММВБ) И НЕ Стр.Ссылка.ПометкаУдаления
        УПОРЯДОЧИТЬ ПО Стр.Ссылка.Дата, Стр.Актив.Наименование""")
    return [{k: s(fo, v) for k, v in r.items()} for r in rows]


def indexes_snapshot(fo, ctx):
    idx = fo.NewObject("Массив")
    for ref in ctx["indexes"]:
        idx.Добавить(ref)
    data = query(fo, """ВЫБРАТЬ Р.Индекс КАК Индекс, Р.ДатаИндекса КАК Дата, Р.Открытие КАК Открытие,
            Р.Максимум КАК Максимум, Р.Минимум КАК Минимум, Р.Закрытие КАК Закрытие, Р.Объем КАК Объем,
            Р.Дюрация КАК Дюрация, Р.Доходность КАК Доходность, Р.Комментарий КАК Комментарий
        ИЗ РегистрСведений.ДанныеИндекса КАК Р ГДЕ Р.Индекс В (&И) УПОРЯДОЧИТЬ ПО Р.Индекс.КодИндекса""", {"И": idx})
    comp = query(fo, """ВЫБРАТЬ Стр.Ссылка.Индекс КАК Индекс, Стр.Ссылка.Дата КАК Дата, Стр.Ссылка.Проведен КАК Проведен,
            Стр.Актив КАК Актив, Стр.Вес КАК Вес, Стр.Капитализация КАК Капитализация
        ИЗ Документ.УстановкаСоставаИндекса.СоставИндекса КАК Стр
        ГДЕ Стр.Ссылка.Индекс В (&И) И НЕ Стр.Ссылка.ПометкаУдаления
        УПОРЯДОЧИТЬ ПО Стр.Актив.Наименование""", {"И": idx})
    return {"данные": [{k: s(fo, v) for k, v in r.items()} for r in data],
            "составы": [{k: s(fo, v) for k, v in r.items()} for r in comp]}


def tcris_snapshot(fo):
    rows = query(fo, """ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Записей ИЗ РегистрСведений.ДополнительныеСведения КАК Св
        ГДЕ Св.Свойство.Наименование = "TCRIS" """)
    return {"сведений_TCRIS": rows[0]["Записей"]}


def scenario(fo, ctx, test_ref, version, name, refs):
    """Один сценарий: сброс данных, правила заглушек и настройки, команда, снимок результата."""
    reset(fo, ctx, test_ref)
    rules = {"du": [], "pif": [], "quotes": {"docs": []}, "indexes": {"data": [], "composition": []}}
    loader = {"Д": "депозиты", "К": "котировки", "И": "индексы", "T": "tcris"}[name[0]]
    if loader == "депозиты":
        rules.update(deposit_rules())
        url = MOCK_DOWN if name == "Д.Сбой" else MOCK
        set_settings(fo, refs[loader], deposit_settings(fo, test_ref, url, mail=(name == "Д.Рассылка")))
    elif loader == "котировки":
        rules["quotes"] = "fail" if name == "К.Сбой" else quote_rules()
        if name == "К.НеПроведен":
            # Документ ММВБ на день раньше не проводится (конфликт записи регистра), следующий проводится.
            first = dict(rules["quotes"]["docs"][0], day_offset=-1)
            rules["quotes"]["docs"].insert(0, first)
            quote_conflict(fo, test_ref, previous_working_day() - datetime.timedelta(days=1))
        set_settings(fo, refs[loader], quote_settings(fo))
    elif loader == "индексы":
        rules["indexes"] = "fail" if name == "И.Сбой" else index_rules()
        set_settings(fo, refs[loader], index_settings(fo))
    write_rules(rules)
    out = {"сценарий": name, "обработка": loader, "версия": version, "начало": now_iso(fo)}
    if name.endswith(".Форма"):
        out.update(run_form_procedures(fo, test_ref, refs[loader], loader, f"{version} {name}"))
    else:
        out.update(run_command(fo, refs[loader], f"{version} {name}"))
    out["конец"] = now_iso(fo)
    if loader == "депозиты":
        out["результат"] = deposits_snapshot(fo, ctx)
    elif loader == "котировки":
        out["результат"] = quotes_snapshot(fo)
    elif loader == "индексы":
        out["результат"] = indexes_snapshot(fo, ctx)
    else:
        out["результат"] = tcris_snapshot(fo)
    return out


def step_run(fo, series, version, only=None, off=False):
    test_ref = test_epf(fo)
    ctx = context(fo, test_ref)
    refs = {}
    for key, (file_name, object_name) in EPF.items():
        refs[key] = register_epf(fo, object_name, os.path.join(EPF_DIRS[version], file_name + ".epf"), None)
    names = only or (OFF_SCENARIOS if off else SCENARIOS)
    state = load_state(series)
    run = {"версия": version, "замеры_выключены": off, "начало": now_iso(fo), "сценарии": []}
    constant = fo.Константы.ВыполнятьЗамерыПроизводительности
    initial = constant.Получить()
    if off:
        constant.Установить(False)
        log("  константа ВыполнятьЗамерыПроизводительности выключена на время прогона")
    try:
        for name in names:
            run["сценарии"].append(scenario(fo, ctx, test_ref, version, name, refs))
    finally:
        if off:
            constant.Установить(initial)
            log(f"  константа ВыполнятьЗамерыПроизводительности возвращена: {constant.Получить()}")
    run["конец"] = now_iso(fo)
    state["runs"].append(run)
    save_state(state)


def measurements(fo, since_xml):
    since = date_1c(fo, datetime.datetime.fromisoformat(since_xml))
    rows = query(fo, f"""
        ВЫБРАТЬ
            З.КлючеваяОперация.Имя КАК Ключ, З.ДатаНачалаЗамера КАК Начало, З.ВремяВыполнения КАК Время,
            З.ВесЗамера КАК Вес, З.Комментарий КАК Комментарий, З.ВыполненСОшибкой КАК Ошибка,
            З.НомерСеанса КАК Сеанс, З.ДатаЗаписиЛокальная КАК Записано
        ИЗ РегистрСведений.ЗамерыВремени КАК З
        ГДЕ З.ДатаЗаписиЛокальная >= &Начало И ({KEY_FILTER})
        УПОРЯДОЧИТЬ ПО Начало, Ключ""", {"Начало": since})
    result = []
    for r in rows:
        comment = r["Комментарий"] or ""
        try:
            comment = json.loads(comment).get("ДопИнф", comment)
        except ValueError:
            pass
        result.append({"ключ": r["Ключ"], "начало_мс": float(r["Начало"]), "время_с": float(r["Время"]),
                       "вес": float(r["Вес"]), "комментарий": comment, "ошибка": bool(r["Ошибка"]),
                       "сеанс": int(r["Сеанс"]), "записано": fo.String(r["Записано"])})
    return result


def step_collect(fo, series):
    state = load_state(series)
    if not state["runs"]:
        raise SystemExit("Нет прогонов серии")
    since = min(r["начало"] for r in state["runs"])
    state["measurements"] = measurements(fo, since)
    save_state(state)
    log(f"  записей замеров {len(state['measurements'])}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, series = sys.argv[1], sys.argv[2]
    fo = connect("wim_fo")
    if cmd == "prep":
        step_prep(fo, series)
    elif cmd == "run":
        args = [a for a in sys.argv[4:] if not a.startswith("--")]
        step_run(fo, series, sys.argv[3], args[0].split(",") if args else None, "--off" in sys.argv)
    elif cmd == "collect":
        step_collect(fo, series)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
