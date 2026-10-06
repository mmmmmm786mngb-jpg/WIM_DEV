# -*- coding: utf-8 -*-
"""Прогон тестов замеров этапа 4 (IMDEV-9530): внешние обработки РОСТ и распространения правил на dev ФО.

Обработки сравниваются в двух версиях: «ориг» (ОРИГИНАЛЫ, без замеров) и «замеры» (ЗАМЕРЫ). Обе версии
регистрируются в один элемент справочника дополнительных обработок (двоичные данные и настройки меняются перед
прогоном версии), у каждой версии свой набор тестовых портфелей и свое свойство статуса портфеля, поэтому
прогоны версий не видят данных друг друга. Тестовые данные остаются в базе (префикс T9530R, серия в имени).

Вызовы обработки РОСТ выполняет тестовая обработка T9530_ТестРОСТ в фоновом задании
ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки: модули документа Поручение и распорядителей во
внешнем соединении не компилируются.

    python run_stage4_tests.py prep <серия>               справочники: свойства и значения статусов, стратегия,
                                                         место хранения, облигация, портфели и субпортфели
    python run_stage4_tests.py data <серия>               документы и регистры обеих версий (тестовая обработка)
    python run_stage4_tests.py rost <серия> <ориг|замеры> сценарии обработки торговых поручений РОСТ
    python run_stage4_tests.py limits <серия> <ориг|замеры> распространение правил лимитов: эталон, новые клиенты,
                                                         вызов как из обработки «Операции после обмена»
    python run_stage4_tests.py nontrade <серия> <ориг|замеры> загрузка неторговых поручений РОСТ: успех, отказ
                                                         вызова сервиса, сервис недоступен (нужна заглушка
                                                         mock_dm_service.py)
    python run_stage4_tests.py collect <серия>            поручения, статусы, установки лимитов, ЗамерыВремени
    python run_stage4_tests.py close <серия>              конечные статусы портфелям серии: свойства статуса общие
                                                         для серий, без закрытия портфели серии попадают в отборы
                                                         следующей серии
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

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
RESULTS = os.path.join(HERE, "results")
EPF_TEST = os.path.join(HERE, "epf", "T9530_ТестРОСТ.epf")
EPF_FILES = {
    "ориг": os.path.join(HERE, "epf", "ОРИГИНАЛЫ"),
    "замеры": os.path.join(TASK, "ЗАМЕРЫ"),
}
ROST = "внСозданиеТорговыхПорученийРОСТ"
DISTRIBUTION = "внРаспространениеПравилСОдногоКлиентаНаСписокКлиентов"
NONTRADE = "внЗагрузкаНеторговыхПорученийРОСТ"
NONTRADE_OBJECT = "ЗагрузкаНеторговыхПорученийРОСТ"
ROST_OBJECT = "СозданиеТорговыхПорученийРОСТ"
TEST_OBJECT = "T9530_ТестРОСТ"
PREFIX = "T9530R"
VERSIONS = {"ориг": "O", "замеры": "M"}
# Группы портфелей: латинский код, число портфелей, сколько портфелей активны (со статусом) сразу после data.
# Ф - портфели реинвестирования для проверки кнопки формы в веб-клиенте: статус ставится перед проверкой.
GROUPS = {"П": ("P", 6, 3), "К": ("K", 2, 0), "С": ("S", 6, 3), "Р": ("R", 9, 9), "Б": ("B", 6, 6), "Ф": ("F", 3, 0)}
# Портфели распространения правил (Л) и неторговых поручений (Н): данные готовят шаги limits и nontrade.
EXTRA_GROUPS = {"Л": ("L", 6, 0), "Н": ("N", 6, 0)}
ALL_GROUPS = {**GROUPS, **EXTRA_GROUPS}
STATUSES = [("Поиск", "Поиск ДС"), ("Перевод", "Перевод в ОФЗ"), ("Окончание", "Окончание обработки"),
            ("Расторжение", "Расторжение инициировано"), ("ПродажаСформированы", "Ордера на продажу сформированы"),
            ("ПродажаОтправлены", "Ордера на продажу отправлены"), ("ПродажаИсполнены", "Ордера на продажу исполнены"),
            ("ВыводПоданы", "Поручения на вывод поданы"), ("ВыводИсполнены", "Поручения на вывод исполнены"),
            ("РеинвСформированы", "Ордера на реинвестирование сформированы")]
STRATEGY = f"{PREFIX} РОСТ"
PLACE = f"{PREFIX} Брокерский счет"
BOND = f"{PREFIX} ОФЗ"
BOND_SAMPLE = "FO_SHAPE OFZ RUB"
SHARE_BUY, SHARE_LIQUIDITY, SHARE_SALE2 = "T9532_SH1", "T9532_SH2", "T9532_SH3"
CLIENT_TYPE = "T9530R Розничный ДУ"
# Классы лимитов розничного ДУ: представление в обработке -> (класс в базе, число лимитов в установке эталона).
LIMIT_CLASSES = {"комплаенс": ("Compliance", 5), "риски": ("Регуляторные", 3)}
NT_STATUSES = [("Поиск", "Поиск ДС"), ("ОтправленыБрокеру", "ДС отправлены брокеру"), ("Перевод", "Перевод в ОФЗ"),
               ("ВыводПодан", "Подано поручение на вывод ДС с брокера"), ("Выведены", "ДС выведены")]
MOCK_URL = "http://127.0.0.1:18530/dm?wsdl"
MOCK_DOWN_URL = "http://127.0.0.1:18531/dm?wsdl"
KEY_FILTER = """(З.КлючеваяОперация.Имя ПОДОБНО "СозданиеТорговыхПорученийРОСТ%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "РаспространениеПравилЛимитов%"
                ИЛИ З.КлючеваяОперация.Имя ПОДОБНО "ЗагрузкаНеторговыхПорученийРОСТ%")"""


def log(*args):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *args, flush=True)


def today_1c(fo):
    """Начало текущего дня сеанса 1С (функции глобального контекста дат во внешнем соединении недоступны)."""
    return query(fo, "ВЫБРАТЬ НАЧАЛОПЕРИОДА(&Д, ДЕНЬ) КАК Д", {"Д": fo.ТекущаяДатаСеанса()})[0]["Д"]


def find_ref(fo, text, params=None):
    rows = query(fo, text, params)
    return rows[0]["Ссылка"] if rows else None


def state_path(series):
    return os.path.join(RESULTS, f"stage4_{series}.json")


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


def portfolio_name(series, version, group, i):
    return f"{PREFIX} {series} {version} {group}{i:02d}"


def portfolio_code(series, version, group, i):
    return f"{PREFIX}_{series}_{VERSIONS[version]}_{ALL_GROUPS[group][0]}{i:02d}"


# ---------------------------------------------------------------- справочники

def property_names(version):
    return f"{PREFIX} Статус портфеля ({version})", f"{PREFIX} Дата статуса портфеля ({version})"


def ensure_property(fo, name, type_name):
    ref = find_ref(fo, "ВЫБРАТЬ Св.Ссылка КАК Ссылка ИЗ ПланВидовХарактеристик.ДополнительныеРеквизитыИСведения КАК Св "
                       "ГДЕ Св.Наименование = &Имя", {"Имя": name})
    if ref is not None:
        return ref
    obj = fo.ПланыВидовХарактеристик.ДополнительныеРеквизитыИСведения.СоздатьЭлемент()
    obj.Наименование = name
    obj.Заголовок = name
    obj.Имя = name.replace(" ", "_").replace("(", "").replace(")", "")
    obj.ТипЗначения = fo.NewObject("ОписаниеТипов", type_name)
    obj.ЭтоДополнительноеСведение = True
    obj.Доступен = True
    obj.Виден = True
    obj.Записать()
    log(f"  создано свойство: {name}")
    return obj.Ссылка


def status_values(fo, prop):
    rows = query(fo, "ВЫБРАТЬ З.Наименование КАК Имя, З.Ссылка КАК Ссылка ИЗ Справочник.ЗначенияСвойствОбъектов КАК З "
                     "ГДЕ З.Владелец = &Свойство И НЕ З.ПометкаУдаления", {"Свойство": prop})
    return {r["Имя"]: r["Ссылка"] for r in rows}


def ensure_status_values(fo, prop, statuses=STATUSES):
    existing = status_values(fo, prop)
    result = {}
    for key, name in statuses:
        ref = existing.get(name)
        if ref is None:
            obj = fo.Справочники.ЗначенияСвойствОбъектов.СоздатьЭлемент()
            obj.Владелец = prop
            obj.Наименование = name
            obj.Записать()
            ref = obj.Ссылка
        result[key] = ref
    return result


def ensure_strategy(fo):
    ref = find_ref(fo, "ВЫБРАТЬ С.Ссылка КАК Ссылка ИЗ Справочник.Стратегии КАК С ГДЕ С.Наименование = &Имя",
                   {"Имя": STRATEGY})
    if ref is None:
        obj = fo.Справочники.Стратегии.СоздатьЭлемент()
        obj.Наименование = STRATEGY
        obj.Записать()
        ref = obj.Ссылка
        log(f"  создана стратегия {STRATEGY}")
    return ref


def ensure_place(fo):
    """Место хранения ФО - обертка над счетом (Объект обязателен): копия банковского счета, место хранения создает
    подписка СинхронизацияМестХранения. Вид места хранения - брокерский счет: его требуют отбор продаж под
    блокировки (остаток денежных средств на брокерских счетах) и неторговые поручения РОСТ (субпортфель брокера).
    Место хранения при записи берет вид из счета, поэтому вид ставится счету."""
    ref = find_ref(fo, "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.МестаХранения КАК М ГДЕ М.Наименование = &Имя",
                   {"Имя": PLACE})
    if ref is None:
        sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 Сч.Ссылка КАК Ссылка ИЗ Справочник.БанковскиеСчета КАК Сч "
                              "ГДЕ НЕ Сч.ПометкаУдаления И НЕ Сч.Наименование ПОДОБНО \"T95%\" УПОРЯДОЧИТЬ ПО Сч.Наименование")
        account = sample.Скопировать()
        account.Наименование = PLACE
        account.Записать()
        ref = find_ref(fo, "ВЫБРАТЬ М.Ссылка КАК Ссылка ИЗ Справочник.МестаХранения КАК М ГДЕ М.Объект = &Объект",
                       {"Объект": account.Ссылка})
        obj = ref.ПолучитьОбъект() if ref is not None else fo.Справочники.МестаХранения.СоздатьЭлемент()
        obj.Объект = account.Ссылка
        obj.Наименование = PLACE
        obj.ВнешнийКод = f"{PREFIX}_BROKER"
        obj.ВидМестаХранения = fo.ПланыВидовХарактеристик.ВидыМестХранения.БрокерскиеСчета
        obj.Записать()
        ref = obj.Ссылка
        log(f"  создано место хранения {PLACE}")
    kind = fo.String(query(fo, "ВЫБРАТЬ М.ВидМестаХранения КАК Вид ИЗ Справочник.МестаХранения КАК М ГДЕ М.Ссылка = &С",
                           {"С": ref})[0]["Вид"])
    if "Брокер" not in kind:
        broker = fo.ПланыВидовХарактеристик.ВидыМестХранения.БрокерскиеСчета
        place = ref.ПолучитьОбъект()
        account = place.Объект.ПолучитьОбъект()
        account.ВидМестаХранения = broker
        account.Записать()
        place = ref.ПолучитьОбъект()
        place.ВидМестаХранения = broker
        place.Записать()
        kind = fo.String(query(fo, "ВЫБРАТЬ М.ВидМестаХранения КАК Вид ИЗ Справочник.МестаХранения КАК М ГДЕ М.Ссылка = &С",
                               {"С": ref})[0]["Вид"])
        log(f"  месту хранения {PLACE} и его счету поставлен вид «брокерский счет», в базе: «{kind}»")
    return ref


def ensure_bond(fo):
    """Тестовая облигация - копия облигации стенда FO_SHAPE; актив создается, если подписка его не создала."""
    bond = find_ref(fo, "ВЫБРАТЬ О.Ссылка КАК Ссылка ИЗ Справочник.Облигации КАК О ГДЕ О.Наименование = &Имя", {"Имя": BOND})
    if bond is None:
        sample = find_ref(fo, "ВЫБРАТЬ О.Ссылка КАК Ссылка ИЗ Справочник.Облигации КАК О ГДЕ О.Наименование = &Имя",
                          {"Имя": BOND_SAMPLE})
        obj = sample.Скопировать()
        obj.Наименование = BOND
        obj.ВнешнийКод = f"{PREFIX}_OFZ"
        obj.ISIN = ""
        obj.НомерГосРегистрацииВыпуска = ""
        obj.Записать()
        bond = obj.Ссылка
        log(f"  создана облигация {BOND}")
    asset = find_ref(fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А ГДЕ А.Объект = &Объект", {"Объект": bond})
    if asset is None:
        obj = fo.Справочники.Активы.СоздатьЭлемент()
        obj.Объект = bond
        obj.ВидАктива = bond.ВидАктива
        obj.Наименование = BOND
        obj.ВнешнийКод = f"{PREFIX}_OFZ"
        obj.Записать()
        asset = obj.Ссылка
        log(f"  создан актив {BOND}")
    return bond, asset


def asset_by_code(fo, code):
    ref = find_ref(fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А ГДЕ А.ВнешнийКод = &Код", {"Код": code})
    if ref is None:
        raise SystemExit(f"Нет актива {code}: тестовые акции создает стенд IMDEV-9532")
    return ref


def rub_asset(fo):
    return find_ref(fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А "
                        "ГДЕ А.ВидАктива = ЗНАЧЕНИЕ(ПланВидовХарактеристик.ВидыАктивов.Валюты) И А.Наименование = \"RUB\"")


def ensure_portfolios(fo, series, strategy, place):
    existing = {r["Код"]: r for r in query(fo, "ВЫБРАТЬ П.ВнешнийКод КАК Код, П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                                               "ГДЕ П.ВнешнийКод ПОДОБНО &Маска", {"Маска": f"{PREFIX}_{series}_%"})}
    sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                          "ГДЕ НЕ П.ПометкаУдаления И НЕ П.Предопределенный И П.ВнешнийКод = \"\" УПОРЯДОЧИТЬ ПО П.Наименование")
    created = 0
    for version in VERSIONS:
        for group, (_, count, _) in ALL_GROUPS.items():
            for i in range(1, count + 1):
                code = portfolio_code(series, version, group, i)
                if code in existing:
                    continue
                name = portfolio_name(series, version, group, i)
                obj = sample.Скопировать()
                obj.Наименование = name
                obj.ВнешнийКод = code
                obj.НомерДоговора = code
                obj.Записать()
                sub = fo.Справочники.Субпортфели.СоздатьЭлемент()
                sub.Наименование = name
                sub.КодСчета = code
                sub.Портфель = obj.Ссылка
                sub.Стратегия = strategy
                sub.МестоХранения = place
                sub.Записать()
                created += 1
    log(f"  портфелей с субпортфелями создано {created}")


def step_prep(fo, series):
    for version in VERSIONS:
        status_name, date_name = property_names(version)
        prop = ensure_property(fo, status_name, "СправочникСсылка.ЗначенияСвойствОбъектов")
        ensure_property(fo, date_name, "Дата")
        ensure_status_values(fo, prop)
    strategy = ensure_strategy(fo)
    place = ensure_place(fo)
    ensure_bond(fo)
    ensure_portfolios(fo, series, strategy, place)


# ---------------------------------------------------------------- регистрация и тестовая обработка

def register_epf(fo, object_name, path, settings, safe_mode_off=True):
    """Регистрирует или обновляет элемент справочника дополнительных обработок по имени объекта."""
    tmp = os.path.join(tempfile.gettempdir(), object_name + ".epf")
    shutil.copyfile(path, tmp)
    processor = fo.ВнешниеОбработки.Создать(tmp, False)
    info = processor.СведенияОВнешнейОбработке()
    ref = find_ref(fo, "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                       "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления", {"Имя": object_name})
    item = ref.ПолучитьОбъект() if ref is not None else fo.Справочники.ДополнительныеОтчетыИОбработки.СоздатьЭлемент()
    item.Наименование = processor.Метаданные().Представление()
    item.ИмяОбъекта = object_name
    item.ИмяФайла = os.path.basename(path)
    item.Версия = info.Версия
    item.БезопасныйРежим = info.БезопасныйРежим if not safe_mode_off else False
    item.Вид = fo.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
    item.Публикация = fo.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    item.ХранилищеОбработки = fo.NewObject("ХранилищеЗначения", fo.NewObject("ДвоичныеДанные", path))
    item.Команды.Очистить()
    for i in range(info.Команды.Количество()):
        src = info.Команды.Получить(i)
        cmd = item.Команды.Добавить()
        cmd.Идентификатор = src.Идентификатор
        cmd.Представление = src.Представление
        cmd.ВариантЗапуска = fo.Перечисления.СпособыВызоваДополнительныхОбработок.ОткрытиеФормы
    if settings is not None:
        item.ХранилищеНастроек = fo.NewObject("ХранилищеЗначения", settings)
    item.ОбменДанными.Загрузка = True
    item.Записать()
    os.remove(tmp)
    log(f"  зарегистрирована обработка {object_name} версии {info.Версия}")
    return item.Ссылка


def test_epf(fo):
    return register_epf(fo, TEST_OBJECT, EPF_TEST, None)


def to_text(fo, value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return fo.String(value)


def run_harness(fo, test_ref, params, title, timeout=3600):
    """Фоновое задание тестовой обработки; возвращает словарь результата и длительность."""
    task = fo.NewObject("Структура")
    task.Вставить("ИмяОбработки", TEST_OBJECT)
    task.Вставить("ИмяМетода", "ВыполнитьСценарий")
    task.Вставить("ПараметрыВыполнения", params)
    task.Вставить("ЭтоВнешняяОбработка", True)
    task.Вставить("ДополнительнаяОбработкаСсылка", test_ref)
    address = fo.ПоместитьВоВременноеХранилище(None, fo.NewObject("УникальныйИдентификатор"))
    args = fo.NewObject("Массив")
    args.Добавить(task)
    args.Добавить(address)
    started = time.time()
    job = fo.ФоновыеЗадания.Выполнить("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", args, "",
                                      f"IMDEV-9530 этап 4: {title}")
    uid = job.УникальныйИдентификатор
    while True:
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно or time.time() - started > timeout:
            break
        time.sleep(1)
    seconds = round(time.time() - started, 1)
    out = {"сценарий": title, "состояние": fo.String(job.Состояние), "длительность_с": seconds,
           "ошибка_задания": fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
           if job.ИнформацияОбОшибке is not None else ""}
    messages = job.ПолучитьСообщенияПользователю(False)
    if messages is not None and messages.Количество():
        out["сообщения"] = [messages.Получить(i).Текст for i in range(messages.Количество())]
    res = fo.ПолучитьИзВременногоХранилища(address)
    if res is not None:
        out["лог"] = res.Лог
        out["ошибка"] = res.Ошибка
        out["поручений"] = res.КоличествоПоручений
        out["важность"] = res.ВажностьОшибки
        out["документы"] = [fo.String(res.Поручения.Получить(i)) for i in range(res.Поручения.Количество())]
        out["даты"] = {}
        for name in ["Сегодня", "Продажа", "Реинвест", "Блокировки"]:
            if res.Даты.Свойство(name):
                out["даты"][name] = fo.String(getattr(res.Даты, name))
        threads = []
        for i in range(res.Потоки.Количество()):
            t = res.Потоки.Получить(i)
            threads.append({"поток": t.НомерПотока, "портфелей": t.Портфели, "состояние": t.Состояние,
                            "поручений": t.Поручений, "ошибка": t.Ошибка, "лог": t.Лог})
        out["потоки"] = threads
    log(f"   {title}: {out['состояние']}, {seconds} с", (out.get("ошибка") or out["ошибка_задания"]).split("\n")[0][:300])
    return out


# ---------------------------------------------------------------- данные

def portfolios_of(fo, series, version, group=None):
    mask = f"{PREFIX}_{series}_{VERSIONS[version]}_" + (ALL_GROUPS[group][0] if group else "") + "%"
    rows = query(fo, """ВЫБРАТЬ П.ВнешнийКод КАК Код, П.Ссылка КАК Портфель, С.Ссылка КАК Субпортфель, С.МестоХранения КАК Место
        ИЗ Справочник.Портфели КАК П ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Субпортфели КАК С ПО С.Портфель = П.Ссылка
        ГДЕ П.ВнешнийКод ПОДОБНО &Маска УПОРЯДОЧИТЬ ПО П.ВнешнийКод""", {"Маска": mask})
    return rows


def version_context(fo, version):
    status_name, date_name = property_names(version)
    prop = find_ref(fo, "ВЫБРАТЬ Св.Ссылка КАК Ссылка ИЗ ПланВидовХарактеристик.ДополнительныеРеквизитыИСведения КАК Св "
                        "ГДЕ Св.Наименование = &Имя", {"Имя": status_name})
    prop_date = find_ref(fo, "ВЫБРАТЬ Св.Ссылка КАК Ссылка ИЗ ПланВидовХарактеристик.ДополнительныеРеквизитыИСведения КАК Св "
                             "ГДЕ Св.Наименование = &Имя", {"Имя": date_name})
    values = status_values(fo, prop)
    statuses = {key: values[name] for key, name in STATUSES}
    return prop, prop_date, statuses


def step_data(fo, series):
    state = load_state(series)
    test_ref = test_epf(fo)
    bond, bond_asset = ensure_bond(fo)
    rub = rub_asset(fo)
    today = today_1c(fo)
    if not query(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 К.Документ КАК Д ИЗ РегистрСведений.КупонноеРасписаниеПоОблигациям КАК К "
                     "ГДЕ К.Облигация = &Обл", {"Обл": bond}):
        params = fo.NewObject("Структура")
        params.Вставить("Сценарий", "Купоны")
        params.Вставить("Облигация", bond)
        params.Вставить("ДатаКупона", today)
        params.Вставить("РазмерКупона", 40)
        params.Вставить("КупоновВперед", 10)
        state["coupons"] = run_harness(fo, test_ref, params, "купонное расписание")
    for version in VERSIONS:
        prop, prop_date, statuses = version_context(fo, version)
        rows = fo.NewObject("Массив")
        for group, (_, count, active) in GROUPS.items():
            for idx, r in enumerate(portfolios_of(fo, series, version, group), start=1):
                row = fo.NewObject("Структура")
                row.Вставить("Портфель", r["Портфель"])
                row.Вставить("Субпортфель", r["Субпортфель"])
                row.Вставить("МестоХранения", r["Место"])
                row.Вставить("Группа", group)
                row.Вставить("Активен", idx <= active)
                amount = {"П": 1000000 + idx * 10000, "К": 1000000 + idx * 10000, "С": 100 + idx,
                          "Р": 1000 + idx * 100, "Б": 50000 + idx * 1000, "Ф": 1000 + idx * 100}[group]
                row.Вставить("Сумма", amount)
                rows.Добавить(row)
        st = fo.NewObject("Структура")
        for key, ref in statuses.items():
            st.Вставить(key, ref)
        sale_assets = fo.NewObject("Массив")
        sale_assets.Добавить(asset_by_code(fo, SHARE_BUY))
        sale_assets.Добавить(asset_by_code(fo, SHARE_SALE2))
        params = fo.NewObject("Структура")
        params.Вставить("Сценарий", "Данные")
        params.Вставить("Портфели", rows)
        params.Вставить("Свойство", prop)
        params.Вставить("СвойствоДата", prop_date)
        params.Вставить("Статусы", st)
        params.Вставить("АктивРубли", rub)
        params.Вставить("АктивОблигация", bond_asset)
        params.Вставить("АктивЛиквидность", asset_by_code(fo, SHARE_LIQUIDITY))
        params.Вставить("АктивыПродажи", sale_assets)
        state[f"data_{version}"] = run_harness(fo, test_ref, params, f"данные версии {version}")
        save_state(state)


# ---------------------------------------------------------------- прогоны РОСТ

def strategy_settings_xml(fo, strategy, bond_asset):
    tz = fo.NewObject("ТаблицаЗначений")
    for col in ["Стратегия", "ГоризонтИнвестирования", "ОсновнойАктивДляПокупки", "ДополнительныйАктивДляПокупки",
                "ПроцентКомиссияУправляющий", "СтавкаРеинвест", "СтавкаДисконтаЦены", "ПроцентПотерьАкции"]:
        tz.Колонки.Добавить(col)
    row = tz.Добавить()
    row.Стратегия = strategy
    row.ГоризонтИнвестирования = 3
    row.ОсновнойАктивДляПокупки = bond_asset
    row.ДополнительныйАктивДляПокупки = asset_by_code(fo, SHARE_BUY)
    row.ПроцентКомиссияУправляющий = 2
    row.СтавкаРеинвест = 10
    row.СтавкаДисконтаЦены = 12
    row.ПроцентПотерьАкции = 30
    return fo.XMLСтрока(fo.NewObject("ХранилищеЗначения", tz))


def rost_settings(fo, version):
    prop, prop_date, statuses = version_context(fo, version)
    strategy = ensure_strategy(fo)
    _, bond_asset = ensure_bond(fo)
    admin = find_ref(fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Пользователи КАК П ГДЕ П.Наименование = \"admin\"")
    s = fo.NewObject("Структура")
    s.Вставить("ДопРеквизитСтатусПортфеля", prop)
    s.Вставить("ДопРеквизитДатаОперации", prop_date)
    s.Вставить("СтатусДляПоиска", statuses["Поиск"])
    s.Вставить("СтатусДляПеревода", statuses["Перевод"])
    s.Вставить("СтатусОкончаниеОбработки", statuses["Окончание"])
    s.Вставить("СтатусРасторжениеИнициировано", statuses["Расторжение"])
    s.Вставить("СтатусОрдераНаПродажуСформированы", statuses["ПродажаСформированы"])
    s.Вставить("СтатусОрдераНаПродажуОтправлены", statuses["ПродажаОтправлены"])
    s.Вставить("СтатусОрдераНаПродажуИсполнены", statuses["ПродажаИсполнены"])
    s.Вставить("СтатусПорученияНаВыводПоданы", statuses["ВыводПоданы"])
    s.Вставить("СтатусПорученияНаВыводИсполнены", statuses["ВыводИсполнены"])
    s.Вставить("СтатусОрдераНаРеИнвСформированы", statuses["РеинвСформированы"])
    s.Вставить("АктивРубли", rub_asset(fo))
    s.Вставить("АвторЗаявок", admin)
    s.Вставить("АктивВимЛиквидность", asset_by_code(fo, SHARE_LIQUIDITY))
    s.Вставить("ПроцентКомиссияБрокер", 0.2)
    s.Вставить("КонтрольПоЦенеЗакрытия", False)
    s.Вставить("ВыключитьПокупки", False)
    s.Вставить("ВыключитьПродажи", False)
    s.Вставить("АдресWS", "")
    s.Вставить("ЛогинWS", "")
    s.Вставить("ПарольWS", "")
    s.Вставить("НастройкаСтратегий", strategy_settings_xml(fo, strategy, bond_asset))
    return s, prop, prop_date, statuses


def rost_params(fo, scenario, rost_ref, test_ref, version, extra=None):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", scenario)
    p.Вставить("ОбработкаСсылка", rost_ref)
    p.Вставить("ТестоваяОбработкаСсылка", test_ref)
    p.Вставить("ЭтоТест", True)
    p.Вставить("ДатаКупона", today_1c(fo))
    p.Вставить("Портфели", fo.NewObject("Массив"))
    p.Вставить("ПередаватьПортфелейВПакете", version == "замеры")
    for key, value in (extra or {}).items():
        p.Вставить(key, value)
    return p


def refs_array(fo, refs):
    arr = fo.NewObject("Массив")
    for r in refs:
        arr.Добавить(r)
    return arr


def set_statuses(fo, test_ref, refs, prop, prop_date, status, title):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "Статусы")
    p.Вставить("Портфели", refs_array(fo, refs))
    p.Вставить("Свойство", prop)
    p.Вставить("Статус", status)
    p.Вставить("СвойствоДата", prop_date)
    return run_harness(fo, test_ref, p, title)


def ofz_orders(fo, portfolios, bond_asset):
    rows = query(fo, """ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Документ.Поручение КАК П
        ГДЕ П.Портфель В (&Портфели) И П.Актив = &Актив И П.Проведен И НЕ П.ПометкаУдаления
            И П.Дата >= &Начало""", {"Портфели": refs_array(fo, portfolios), "Актив": bond_asset,
                                      "Начало": today_1c(fo)})
    return [r["Ссылка"] for r in rows]


def run_bsp_command(fo, rost_ref, command, title, timeout=3600):
    """Команда обработки через БСП ДополнительныеОтчетыИОбработки.ВыполнитьКоманду - путь регламентного задания
    (обработка создается из справочника, тестовый режим выключен)."""
    params = fo.NewObject("Структура")
    params.Вставить("ДополнительнаяОбработкаСсылка", rost_ref)
    params.Вставить("ИдентификаторКоманды", command)
    args = fo.NewObject("Массив")
    args.Добавить(params)
    args.Добавить(None)
    started = time.time()
    job = fo.ФоновыеЗадания.Выполнить("ДополнительныеОтчетыИОбработки.ВыполнитьКоманду", args, "",
                                      f"IMDEV-9530 этап 4: {title}")
    uid = job.УникальныйИдентификатор
    while True:
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно or time.time() - started > timeout:
            break
        time.sleep(1)
    seconds = round(time.time() - started, 1)
    error = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке) if job.ИнформацияОбОшибке is not None else ""
    log(f"   {title}: {fo.String(job.Состояние)}, {seconds} с", error.split("\n")[0][:300])
    return {"сценарий": title, "состояние": fo.String(job.Состояние), "длительность_с": seconds, "ошибка_задания": error,
            "журнал": event_log(fo, job.Начало)}


def event_log(fo, since):
    """Записи журнала регистрации дополнительных обработок с момента since: команда через БСП пишет туда текст
    ошибки (ВажностьОшибки = 2), лог обработки при этом не возвращается."""
    table = fo.NewObject("ТаблицаЗначений")
    filt = fo.NewObject("Структура")
    filt.Вставить("ДатаНачала", since)
    fo.ВыгрузитьЖурналРегистрации(table, filt)
    result = []
    for i in range(table.Количество()):
        row = table.Получить(i)
        event = row.Событие or ""
        if not any(mark in event for mark in ("Дополнительные отчеты и обработки", "RetailDU", "Рассылка поручений")):
            continue
        result.append({"дата": fo.String(row.Дата), "событие": event, "уровень": fo.String(row.Уровень),
                       "комментарий": row.Комментарий})
    return result


def now_iso(fo):
    return fo.XMLСтрока(fo.ТекущаяДатаСеанса())


def step_rost(fo, series, version, only=None):
    state = load_state(series)
    test_ref = test_epf(fo)
    settings, prop, prop_date, statuses = rost_settings(fo, version)
    rost_ref = register_epf(fo, ROST_OBJECT, os.path.join(EPF_FILES[version], ROST + ".epf"), settings)
    _, bond_asset = ensure_bond(fo)
    group = {g: [r["Портфель"] for r in portfolios_of(fo, series, version, g)] for g in GROUPS}
    run = {"версия": version, "начало": now_iso(fo), "шаги": []}
    steps = run["шаги"]

    def scenario(name, title, extra=None):
        if only and name not in only:
            return
        p = rost_params(fo, name, rost_ref, test_ref, version, extra)
        out = run_harness(fo, test_ref, p, f"{title} ({version})")
        out["шаг"] = name
        out["начало"], out["конец"] = start, now_iso(fo)
        steps.append(out)

    start = now_iso(fo)
    scenario("Покупка.Команда", "покупка, команда регламентного задания")
    if not only or "Покупка.Форма" in only:
        start = now_iso(fo)
        orders = ofz_orders(fo, group["П"][:3], bond_asset)
        p = fo.NewObject("Структура")
        p.Вставить("Сценарий", "ГотовностьПоручений")
        p.Вставить("Поручения", refs_array(fo, orders))
        steps.append(dict(run_harness(fo, test_ref, p, f"статус Ready поручениям ОФЗ ({len(orders)})"), шаг="Ready"))
        steps.append(dict(set_statuses(fo, test_ref, group["П"][3:], prop, prop_date, statuses["Поиск"],
                                       "статус «Поиск ДС» портфелям П04-П06"), шаг="Статусы"))
    start = now_iso(fo)
    scenario("Покупка.Форма", "покупка, кнопки формы")
    start = now_iso(fo)
    scenario("Продажа.Команда", "продажа, команда регламентного задания")
    if not only or "Продажа.Форма" in only:
        steps.append(dict(set_statuses(fo, test_ref, group["С"][3:], prop, prop_date, statuses["Расторжение"],
                                       "статус «Расторжение инициировано» портфелям С04-С06"), шаг="Статусы"))
    start = now_iso(fo)
    scenario("Продажа.Форма", "продажа, кнопки формы")
    start = now_iso(fo)
    scenario("Реинвест.Форма", "реинвестирование, кнопка формы без потоков",
             {"Портфели": refs_array(fo, group["Р"][:3])})
    start = now_iso(fo)
    scenario("Реинвест.Потоки", "реинвестирование, потоки формы и отправка пачки")
    start = now_iso(fo)
    scenario("Блокировки.Потоки", "продажи под блокировки, потоки формы и отправка пачки")
    if not only or "Покупка.БСП" in only:
        steps.append(dict(set_statuses(fo, test_ref, group["К"], prop, prop_date, statuses["Поиск"],
                                       "статус «Поиск ДС» портфелям К01-К02"), шаг="Статусы"))
        start = now_iso(fo)
        out = run_bsp_command(fo, rost_ref, "ФоновоеВыполнениеПокупка", f"покупка через БСП ВыполнитьКоманду ({version})")
        out["шаг"] = "Покупка.БСП"
        out["начало"], out["конец"] = start, now_iso(fo)
        steps.append(out)
    run["конец"] = now_iso(fo)
    state["runs"].append(run)
    save_state(state)


# ---------------------------------------------------------------- распространение правил лимитов

def limit_props(fo):
    props = {}
    for cls in LIMIT_CLASSES:
        suffix = "Комплаенс" if cls == "комплаенс" else "Риски"
        props["ДатаАвтоустановкиЛимитов" + suffix] = ensure_property(
            fo, f"{PREFIX} Дата автоустановки лимитов ({cls})", "Дата")
        props["ВнешнийКодЭталонногоПортфеля" + suffix] = ensure_property(
            fo, f"{PREFIX} Внешний код эталонного портфеля ({cls})", "Строка")
        props["ЛимитыЗаведены" + suffix] = ensure_property(fo, f"{PREFIX} Лимиты заведены ({cls})", "Булево")
        props["Эталонный_портфель_лимитов_" + cls] = ensure_property(
            fo, f"{PREFIX} Эталонный портфель лимитов ({cls})", "СправочникСсылка.Портфели")
        props["Дата_распространения_правил_" + cls] = ensure_property(
            fo, f"{PREFIX} Дата распространения правил ({cls})", "Дата")
    return props


def ensure_client_type(fo):
    ref = find_ref(fo, "ВЫБРАТЬ Т.Ссылка КАК Ссылка ИЗ Справочник.ТипыКлиентов КАК Т ГДЕ Т.Наименование = &Имя",
                   {"Имя": CLIENT_TYPE})
    if ref is None:
        obj = fo.Справочники.ТипыКлиентов.СоздатьЭлемент()
        obj.Наименование = CLIENT_TYPE
        obj.Записать()
        ref = obj.Ссылка
        log(f"  создан тип клиента {CLIENT_TYPE}")
    return ref


def limit_class(fo, name):
    return find_ref(fo, "ВЫБРАТЬ К.Ссылка КАК Ссылка ИЗ Справочник.КлассыЛимитов КАК К ГДЕ К.Наименование = &Имя",
                    {"Имя": name})


def limit_sample(fo, klass, min_limits):
    """Проведенная установка лимитов по портфелю (не тестовому) с наименьшим числом лимитов не меньше min_limits."""
    return find_ref(fo, """ВЫБРАТЬ ПЕРВЫЕ 1 У.Ссылка КАК Ссылка, КОЛИЧЕСТВО(Л.Лимит) КАК Лимитов
        ИЗ Документ.УстановкаЛимитов КАК У
            ВНУТРЕННЕЕ СОЕДИНЕНИЕ Документ.УстановкаЛимитов.Лимиты КАК Л ПО Л.Ссылка = У.Ссылка
        ГДЕ У.Проведен И У.КлассЛимита = &Класс
            И У.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыОперацийУстановкиЛимитов.ПоПортфелю)
            И НЕ ВЫРАЗИТЬ(У.ОбъектНазначения КАК Справочник.Портфели).ВнешнийКод ПОДОБНО "T95%"
        СГРУППИРОВАТЬ ПО У.Ссылка
        ИМЕЮЩИЕ КОЛИЧЕСТВО(Л.Лимит) >= &Мин
        УПОРЯДОЧИТЬ ПО Лимитов, У.Ссылка""", {"Класс": klass, "Мин": min_limits})


def has_limits(fo, portfolio, klass):
    return bool(query(fo, """ВЫБРАТЬ ПЕРВЫЕ 1 Д.Регистратор КАК Р
        ИЗ РегистрСведений.ДействующиеЛимитыПоПортфелю.СрезПоследних(, Портфель = &П И КлассЛимита = &К) КАК Д""",
                      {"П": portfolio, "К": klass}))


def create_limit_docs(fo, test_ref, items, title):
    docs = fo.NewObject("Массив")
    for sample, portfolio, count in items:
        d = fo.NewObject("Структура")
        d.Вставить("Образец", sample)
        d.Вставить("Портфель", portfolio)
        d.Вставить("ЧислоЛимитов", count)
        docs.Добавить(d)
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "УстановкиЛимитов")
    p.Вставить("Документы", docs)
    return run_harness(fo, test_ref, p, title)


def ensure_etalon(fo, series, strategy, place, test_ref):
    """Эталонный портфель серии: внешний код, по которому новые клиенты находят эталон, и действующие установки
    лимитов обоих классов (копии существующих установок с ограниченным числом лимитов)."""
    code = f"{PREFIX}_{series}_ETALON"
    ref = find_ref(fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П ГДЕ П.ВнешнийКод = &Код", {"Код": code})
    if ref is None:
        sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                              "ГДЕ НЕ П.ПометкаУдаления И НЕ П.Предопределенный И П.ВнешнийКод = \"\" УПОРЯДОЧИТЬ ПО П.Наименование")
        obj = sample.Скопировать()
        obj.Наименование = f"{PREFIX} {series} Эталон"
        obj.Стратегия = strategy
        obj.ВнешнийКод = code
        obj.НомерДоговора = code
        obj.Записать()
        ref = obj.Ссылка
        sub = fo.Справочники.Субпортфели.СоздатьЭлемент()
        sub.Наименование = obj.Наименование
        sub.КодСчета = code
        sub.Портфель = ref
        sub.Стратегия = strategy
        sub.МестоХранения = place
        sub.Записать()
        log(f"  создан эталонный портфель {code}")
    items = []
    for class_name, count in LIMIT_CLASSES.values():
        klass = limit_class(fo, class_name)
        if not has_limits(fo, ref, klass):
            items.append((limit_sample(fo, klass, count), ref, count))
    if items:
        out = create_limit_docs(fo, test_ref, items, "установки лимитов эталонного портфеля")
        if out.get("ошибка") or out["ошибка_задания"]:
            raise SystemExit(out.get("ошибка") or out["ошибка_задания"])
    return ref, code


def set_client_type(fo, portfolios, client_type):
    for ref in portfolios:
        obj = ref.ПолучитьОбъект()
        obj.ТипКлиента = client_type
        obj.Записать()


def distribution_settings(fo, props, client_type):
    s = fo.NewObject("Структура")
    for key, ref in props.items():
        s.Вставить(key, ref)
    # Признак стратегии установки лимитов: сведение установки со значением - стратегией эталонного портфеля.
    s.Вставить("Эталонный_портфель_лимитов", ensure_property(fo, f"{PREFIX} Эталонный портфель лимитов (стратегия)",
                                                             "СправочникСсылка.Стратегии"))
    s.Вставить("КлассЛимитовКомплаенс", limit_class(fo, LIMIT_CLASSES["комплаенс"][0]))
    s.Вставить("КлассЛимитовРиски", limit_class(fo, LIMIT_CLASSES["риски"][0]))
    empty_mailing = fo.Справочники.НастройкиРассылкиПисем.ПустаяСсылка()
    for key in ["НастройкаРассылкиКомплаенс", "НастройкаРассылкиРиски", "НастройкаРассылкиПриУспешномАвтораспространении"]:
        s.Вставить(key, empty_mailing)
    s.Вставить("СписокСервисныхПользователей", fo.NewObject("СписокЗначений"))
    for key in ["СписокТиповКлиентовКомплаенс", "СписокТиповКлиентовРиски"]:
        types = fo.NewObject("СписокЗначений")
        types.Добавить(client_type)
        s.Вставить(key, types)
    s.Вставить("ЭтоБазаРозничногоДУ", True)
    return s


def wait_jobs(fo, name, timeout=300):
    """Ожидает завершения активных фоновых заданий с наименованием name; возвращает длительность ожидания и число
    заданий, оставшихся активными."""
    started = time.time()
    filt = fo.NewObject("Структура")
    filt.Вставить("Наименование", name)
    while True:
        jobs = fo.ФоновыеЗадания.ПолучитьФоновыеЗадания(filt)
        active = [jobs.Получить(i) for i in range(jobs.Количество())
                  if jobs.Получить(i).Состояние == fo.СостояниеФоновогоЗадания.Активно]
        if not active or time.time() - started > timeout:
            break
        time.sleep(2)
    return round(time.time() - started, 1), len(active)


def step_limits(fo, series, version):
    """Константа ИспользоватьКлассыЛимитов на dev выключена: тогда проведение второй установки лимитов портфеля
    (класс «риски» после «комплаенс») запрещено без даты окончания первой. В базе розничного ДУ классы используются,
    поэтому на время шага константа включается и затем возвращается к исходному значению."""
    original = fo.Константы.ИспользоватьКлассыЛимитов.Получить()
    fo.Константы.ИспользоватьКлассыЛимитов.Установить(True)
    try:
        run_limits(fo, series, version)
    finally:
        fo.Константы.ИспользоватьКлассыЛимитов.Установить(original)
        log(f"  константа ИспользоватьКлассыЛимитов возвращена: {original}")


def run_limits(fo, series, version):
    state = load_state(series)
    test_ref = test_epf(fo)
    props = limit_props(fo)
    client_type = ensure_client_type(fo)
    strategy, place = ensure_strategy(fo), ensure_place(fo)
    etalon, etalon_code = ensure_etalon(fo, series, strategy, place, test_ref)
    clients = [r["Портфель"] for r in portfolios_of(fo, series, version, "Л")]
    run = {"версия": version, "обработка": "распространение", "начало": now_iso(fo), "шаги": []}

    # Л01-Л03 - внешний код эталона (распространение по обоим классам), Л04 - без кода, Л05 - код несуществующего
    # портфеля, Л06 - код эталона и уже есть установка лимитов комплаенс (по рискам - распространение).
    codes = [etalon_code, etalon_code, etalon_code, None, f"{PREFIX}_NOT_FOUND", etalon_code]
    records = fo.NewObject("Массив")
    for ref, code in zip(clients, codes):
        if code is None:
            continue
        for suffix in ("Комплаенс", "Риски"):
            rec = fo.NewObject("Структура")
            rec.Вставить("Объект", ref)
            rec.Вставить("Свойство", props["ВнешнийКодЭталонногоПортфеля" + suffix])
            rec.Вставить("Значение", code)
            records.Добавить(rec)
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "Сведения")
    p.Вставить("Записи", records)
    run["шаги"].append(dict(run_harness(fo, test_ref, p, "внешний код эталона новым клиентам"), шаг="Данные"))
    compliance = limit_class(fo, LIMIT_CLASSES["комплаенс"][0])
    if not has_limits(fo, clients[5], compliance):
        out = create_limit_docs(fo, test_ref, [(limit_sample(fo, compliance, 3), clients[5], 3)],
                                "установка лимитов комплаенс клиенту Л06")
        run["шаги"].append(dict(out, шаг="Данные"))

    # Новыми клиентами считаются только портфели тестового типа клиента: включаются клиенты этой версии.
    others = [r["Ссылка"] for r in query(fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П ГДЕ П.ТипКлиента = &Т",
                                         {"Т": client_type}) if r["Ссылка"] not in clients]
    set_client_type(fo, others, fo.Справочники.ТипыКлиентов.ПустаяСсылка())
    set_client_type(fo, clients, client_type)

    ref = register_epf(fo, DISTRIBUTION, os.path.join(EPF_FILES[version], DISTRIBUTION + ".epf"),
                       distribution_settings(fo, props, client_type))
    start = now_iso(fo)
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "Распространение")
    p.Вставить("ОбработкаСсылка", ref)
    out = run_harness(fo, test_ref, p, f"распространение правил после обмена ({version})")
    out["шаг"] = "Распространение"
    out["начало"], out["конец"] = start, now_iso(fo)
    seconds, left = wait_jobs(fo, "Запись версий лимитов")
    out["запись_версий_лимитов"] = {"ожидание_с": seconds, "активных_после_ожидания": left}
    run["шаги"].append(out)
    set_client_type(fo, clients, fo.Справочники.ТипыКлиентов.ПустаяСсылка())
    run["конец"] = now_iso(fo)
    state["runs"].append(run)
    save_state(state)


# ---------------------------------------------------------------- неторговые поручения РОСТ

def nontrade_context(fo, version):
    prop = ensure_property(fo, f"{PREFIX} Статус неторговых ({version})", "СправочникСсылка.ЗначенияСвойствОбъектов")
    prop_date = ensure_property(fo, f"{PREFIX} Дата статуса неторговых ({version})", "Дата")
    statuses = ensure_status_values(fo, prop, NT_STATUSES)
    flag_loaded = ensure_property(fo, f"{PREFIX} Позиция выгружена", "Булево")
    flag_recalc = ensure_property(fo, f"{PREFIX} Дата пересчета РСА", "Дата")
    return prop, prop_date, statuses, flag_loaded, flag_recalc


def nontrade_settings(fo, version, url):
    prop, prop_date, statuses, flag_loaded, flag_recalc = nontrade_context(fo, version)
    s = fo.NewObject("Структура")
    s.Вставить("АдресWS", url)
    s.Вставить("Логин", "")
    s.Вставить("Пароль", "")
    s.Вставить("НеКонтролироватьДостаточностьДС", True)
    s.Вставить("КодСчетаБрокер", PREFIX)
    s.Вставить("ДопРеквизитСтатусПортфеля", prop)
    s.Вставить("СтатусДляПоиска", statuses["Поиск"])
    s.Вставить("СтатусДСОтправленыБрокеру", statuses["ОтправленыБрокеру"])
    s.Вставить("СтатусДляПеревода", statuses["Перевод"])
    s.Вставить("СтатусПоданоПоручениеНаВыводДС_СБрокера", statuses["ВыводПодан"])
    s.Вставить("СтатусДСВыведены", statuses["Выведены"])
    s.Вставить("ДопРеквизитДатаОперации", prop_date)
    s.Вставить("АктивРубли", rub_asset(fo))
    s.Вставить("ПризнакПозицияВыгружена", flag_loaded)
    s.Вставить("ПризнакДатаПересчетаРСА", flag_recalc)
    return s


def write_mock_rules(rules):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "mock_dm_rules.json"), "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def step_nontrade(fo, series, version):
    state = load_state(series)
    test_ref = test_epf(fo)
    prop, prop_date, statuses, _, _ = nontrade_context(fo, version)
    rows = portfolios_of(fo, series, version, "Н")
    clients = [r["Портфель"] for r in rows]
    codes = [r["Код"] for r in rows]
    run = {"версия": version, "обработка": "неторговые", "начало": now_iso(fo), "шаги": []}

    # Ответы заглушки 1С:ДО: Н01-Н03 - деньги на брокерском счете, Н04 - деньги поступили, но не отправлены
    # брокеру, Н05 - сумма 0 (портфель пропускается), Н06 - отказ сервиса (только в прогоне «отказ»).
    rules = {codes[i]: {"Сумма": 100000 * (i + 1), "ОтправленоНаБрокерский": True} for i in range(3)}
    rules[codes[3]] = {"Сумма": 50000, "ОтправленоНаБрокерский": False}
    write_mock_rules(rules)
    run["шаги"].append(dict(set_statuses(fo, test_ref, clients[:5], prop, prop_date, statuses["Поиск"],
                                         "статус «Поиск ДС» портфелям Н01-Н05"), шаг="Статусы"))

    def run_command(name, title, url):
        ref = register_epf(fo, NONTRADE_OBJECT, os.path.join(EPF_FILES[version], NONTRADE + ".epf"),
                           nontrade_settings(fo, version, url))
        start = now_iso(fo)
        p = fo.NewObject("Структура")
        p.Вставить("Сценарий", "Неторговые")
        p.Вставить("ОбработкаСсылка", ref)
        p.Вставить("ЭтоТест", True)
        out = run_harness(fo, test_ref, p, f"{title} ({version})")
        out["шаг"] = name
        out["начало"], out["конец"] = start, now_iso(fo)
        out["журнал"] = event_log(fo, date_1c(fo, datetime.datetime.fromisoformat(start)))
        run["шаги"].append(out)

    run_command("Неторговые.Успех", "неторговые поручения, сервис отвечает", MOCK_URL)
    rules[codes[5]] = "fail"
    write_mock_rules(rules)
    run["шаги"].append(dict(set_statuses(fo, test_ref, clients[5:], prop, prop_date, statuses["Поиск"],
                                         "статус «Поиск ДС» портфелю Н06"), шаг="Статусы"))
    run_command("Неторговые.ОтказВызова", "неторговые поручения, отказ вызова сервиса", MOCK_URL)
    run_command("Неторговые.СервисНедоступен", "неторговые поручения, сервис недоступен", MOCK_DOWN_URL)
    run["конец"] = now_iso(fo)
    state["runs"].append(run)
    save_state(state)

# ---------------------------------------------------------------- закрытие серии

def step_close(fo, series):
    """Статус «Поручения на вывод исполнены» не входит ни в отборы покупки и продажи, ни в списки реинвестирования
    и продаж под блокировки (исключается ими); статус неторговых «ДС выведены» не входит в отбор неторговых."""
    test_ref = test_epf(fo)
    for version in VERSIONS:
        prop, prop_date, statuses = version_context(fo, version)
        refs = [r["Портфель"] for r in portfolios_of(fo, series, version)]
        set_statuses(fo, test_ref, refs, prop, prop_date, statuses["ВыводИсполнены"],
                     f"серия {series} ({version}): статус «Поручения на вывод исполнены», {len(refs)} портфелей")
        nt_prop, nt_date, nt_statuses, _, _ = nontrade_context(fo, version)
        nt_refs = [r["Портфель"] for r in portfolios_of(fo, series, version, "Н")]
        if nt_refs:
            set_statuses(fo, test_ref, nt_refs, nt_prop, nt_date, nt_statuses["Выведены"],
                         f"серия {series} ({version}): статус неторговых «ДС выведены», {len(nt_refs)} портфелей")
    client_type = ensure_client_type(fo)
    others = [r["Ссылка"] for r in query(fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П ГДЕ П.ТипКлиента = &Т",
                                         {"Т": client_type})]
    set_client_type(fo, others, fo.Справочники.ТипыКлиентов.ПустаяСсылка())
    state = load_state(series)
    state["закрыта"] = now_iso(fo)
    save_state(state)


# ---------------------------------------------------------------- сбор

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
            Начало, Ключ""", {"Начало": since})
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


def orders_snapshot(fo, series, version):
    rows = query(fo, """ВЫБРАТЬ
            П.Портфель.ВнешнийКод КАК Портфель,
            П.ВидОперации КАК Вид,
            П.ВидОперацииНеторговогоПоручения КАК ВидНеторг,
            П.Направление КАК Направление,
            П.Актив КАК Актив,
            П.Количество КАК Количество,
            П.ЦенаВВалютеРасчетов КАК Цена,
            П.СуммаПоручения КАК Сумма,
            П.Проведен КАК Проведен,
            П.ПометкаУдаления КАК Удален,
            ЕСТЬNULL(С.СтатусРасш, ЗНАЧЕНИЕ(Перечисление.СтатусыПорученийБлоттер.ПустаяСсылка)) КАК Статус,
            П.Дата КАК Дата
        ИЗ Документ.Поручение КАК П
            ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.СтатусыПоручений КАК С ПО С.Поручение = П.Ссылка
        ГДЕ П.Портфель.ВнешнийКод ПОДОБНО &Маска
        УПОРЯДОЧИТЬ ПО П.Портфель.ВнешнийКод, П.Дата, П.Номер""",
                 {"Маска": f"{PREFIX}_{series}_{VERSIONS[version]}_%"})
    return [{k: (to_text(fo, v) if k not in ("Количество", "Цена", "Сумма") else float(v)) for k, v in r.items()}
            for r in rows]


def statuses_snapshot(fo, series, version):
    prop, prop_date, _ = version_context(fo, version)
    rows = query(fo, """ВЫБРАТЬ Д.Объект.ВнешнийКод КАК Портфель, ПРЕДСТАВЛЕНИЕ(Д.Значение) КАК Статус
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ Д.Свойство = &Свойство УПОРЯДОЧИТЬ ПО Портфель""", {"Свойство": prop})
    mask = f"{PREFIX}_{series}_{VERSIONS[version]}_"
    return {r["Портфель"]: r["Статус"] for r in rows if (r["Портфель"] or "").startswith(mask)}


def limits_snapshot(fo, series, version):
    """Установки лимитов и сведения распространения правил по портфелям группы Л версии."""
    mask = f"{PREFIX}_{series}_{VERSIONS[version]}_L%"
    docs = query(fo, """ВЫБРАТЬ
            ВЫРАЗИТЬ(У.ОбъектНазначения КАК Справочник.Портфели).ВнешнийКод КАК Портфель,
            У.КлассЛимита.Наименование КАК Класс,
            У.Проведен КАК Проведен,
            КОЛИЧЕСТВО(Л.Лимит) КАК Лимитов
        ИЗ Документ.УстановкаЛимитов КАК У
            ЛЕВОЕ СОЕДИНЕНИЕ Документ.УстановкаЛимитов.Лимиты КАК Л ПО Л.Ссылка = У.Ссылка
        ГДЕ ВЫРАЗИТЬ(У.ОбъектНазначения КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &Маска
        СГРУППИРОВАТЬ ПО У.ОбъектНазначения, У.КлассЛимита, У.Проведен
        УПОРЯДОЧИТЬ ПО Портфель, Класс""", {"Маска": mask})
    props = query(fo, """ВЫБРАТЬ
            ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод КАК Портфель,
            Д.Свойство.Наименование КАК Свойство,
            Д.Значение КАК Значение
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &Маска
            И Д.Свойство.Наименование ПОДОБНО "T9530R %"
        УПОРЯДОЧИТЬ ПО Портфель, Свойство""", {"Маска": mask})
    return {"установки": [{k: to_text(fo, v) for k, v in r.items()} for r in docs],
            "сведения": [{k: to_text(fo, v) for k, v in r.items()} for r in props]}


def nontrade_snapshot(fo, series, version):
    """Статусы и признаки портфелей группы Н версии (свойства неторговых поручений РОСТ)."""
    mask = f"{PREFIX}_{series}_{VERSIONS[version]}_N%"
    rows = query(fo, """ВЫБРАТЬ
            ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод КАК Портфель,
            Д.Свойство.Наименование КАК Свойство,
            Д.Значение КАК Значение
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &Маска
            И Д.Свойство.Наименование ПОДОБНО "T9530R %"
        УПОРЯДОЧИТЬ ПО Портфель, Свойство""", {"Маска": mask})
    return [{k: to_text(fo, v) for k, v in r.items()} for r in rows]


def step_collect(fo, series):
    state = load_state(series)
    if not state["runs"]:
        raise SystemExit("Нет прогонов серии")
    since = min(r["начало"] for r in state["runs"])
    state["measurements"] = measurements(fo, since)
    state["orders"] = {v: orders_snapshot(fo, series, v) for v in VERSIONS}
    state["statuses"] = {v: statuses_snapshot(fo, series, v) for v in VERSIONS}
    state["limits"] = {v: limits_snapshot(fo, series, v) for v in VERSIONS}
    state["nontrade"] = {v: nontrade_snapshot(fo, series, v) for v in VERSIONS}
    save_state(state)
    log(f"  записей замеров {len(state['measurements'])}, поручений: "
        + ", ".join(f"{v} {len(o)}" for v, o in state["orders"].items()))


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, series = sys.argv[1], sys.argv[2]
    fo = connect("wim_fo")
    if cmd == "prep":
        step_prep(fo, series)
    elif cmd == "data":
        step_data(fo, series)
    elif cmd == "rost":
        only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
        step_rost(fo, series, sys.argv[3], only)
    elif cmd == "limits":
        step_limits(fo, series, sys.argv[3])
    elif cmd == "nontrade":
        step_nontrade(fo, series, sys.argv[3])
    elif cmd == "collect":
        step_collect(fo, series)
    elif cmd == "close":
        step_close(fo, series)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
