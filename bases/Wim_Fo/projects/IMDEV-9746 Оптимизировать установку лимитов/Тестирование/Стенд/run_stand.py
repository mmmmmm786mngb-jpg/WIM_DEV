# -*- coding: utf-8 -*-
"""IMDEV-9746. Стенд распространения правил лимитов на разработческой ФО (WIN_FO_server): обычный ФО и розница.

Цель - распределение времени шага "создание установок" по действиям, которые на ПРОД отдельно не замеряются.
Вызывается стендовая копия обработки 1.16 (epf/T9746_СтендРаспространения.epf, отдельный элемент справочника
дополнительных обработок): логика та же, добавлены замеры действий. Все записи стенда выполняет сама обработка в фоновом
задании (сценарии ВыполнитьСценарийСтенда): модули регистров и подписок во внешнем соединении не компилируются.

Данные как на Т-1 (диагностика 28.10.2026): обычный ФО - один класс Compliance, 31 лимит в установке эталона, пороги
эталона по 25 лимитам, один клиент за запуск; розница - классы Compliance и Регуляторные (вместо "Рисковый"), по 7
лимитов в установке, по 2 порога эталона на класс, 2 клиента за запуск. Лимиты стенда - копии лимитов базы с префиксом
T9746. Пороги других портфелей по лимитам стенда (объем Т-1 неизвестен) задаются командой volume.
На время стенда включаются константа ИспользоватьКлассыЛимитов (на Т-1 Да) и версионирование справочника Лимиты
при записи (на Т-1 версии лимитов пишутся на каждый набор порогов); restore возвращает исходные значения.
Почта - заглушка mock_smtp.py (127.0.0.1:18525), запускается отдельно.

    python run_stand.py prep                    справочники, лимиты, эталоны, клиенты, рассылка, версионирование
    python run_stand.py volume <N> [o|r]        пороги N других портфелей по каждому лимиту обычного (o) или розницы (r)
    python run_stand.py ordinary <запусков>     запуски обычного ФО, по одному новому клиенту
    python run_stand.py retail <запусков> [клиентов]  запуски розницы (по умолчанию 2 клиента)
    python run_stand.py bench <повторов> [лимитов]   раскладка записи набора порогов по действиям обработчиков
    python run_stand.py report                  сводка results/*.jsonl -> results/summary.json
    python run_stand.py restore                 константа и версионирование лимитов - как до стенда
"""
import datetime
import glob
import json
import os
import shutil
import statistics as st
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
STAND = glob.glob(r"C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО")[0]
sys.path.insert(0, STAND)
from stand_common import connect, date_1c, query  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
STATE = os.path.join(RESULTS, "state.json")
EPF = os.path.join(HERE, "epf", "T9746_СтендРаспространения.epf")
OBJECT = "T9746_СтендРаспространения"
PREFIX = "T9746"
MODES = {
    "o": {"имя": "обычный", "тип": f"{PREFIX} Обычный ДУ", "эталон": f"{PREFIX}_ETALON_O", "клиенты": f"{PREFIX}_O_",
          "классы": {"комплаенс": ("Compliance", 31, 25)}, "розница": False},
    "r": {"имя": "розница", "тип": f"{PREFIX} Розничный ДУ", "эталон": f"{PREFIX}_ETALON_R", "клиенты": f"{PREFIX}_R_",
          "классы": {"комплаенс": ("Compliance", 7, 2), "риски": ("Регуляторные", 7, 2)}, "розница": True},
}
CLIENTS = {"o": 40, "r": 60}
STRATEGY = f"{PREFIX} Стратегия"
MAIL_ACCOUNT = "T9748 Тестовая почта"
MAILING = f"{PREFIX} тест рассылки"
MAIL_TO = "limits@t9746.test"
VOLUME_PERIOD = datetime.datetime(2026, 1, 12)


def log(*args):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *args, flush=True)


def find_ref(fo, text, params=None):
    rows = query(fo, text, params)
    return rows[0]["Ссылка"] if rows else None


def array(fo, values):
    result = fo.NewObject("Массив")
    for value in values:
        result.Добавить(value)
    return result


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(RESULTS, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def append(name, record):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, name), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- обработка стенда

def register(fo, settings=None):
    """Регистрирует стендовую обработку отдельным элементом справочника (ИмяОбъекта T9746_СтендРаспространения)."""
    tmp = os.path.join(tempfile.gettempdir(), OBJECT + ".epf")
    shutil.copyfile(EPF, tmp)
    info = fo.ВнешниеОбработки.Создать(tmp, False).СведенияОВнешнейОбработке()
    os.remove(tmp)
    ref = find_ref(fo, "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                       "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления", {"Имя": OBJECT})
    item = ref.ПолучитьОбъект() if ref is not None else fo.Справочники.ДополнительныеОтчетыИОбработки.СоздатьЭлемент()
    item.Наименование = info.Наименование
    item.ИмяОбъекта = OBJECT
    item.ИмяФайла = os.path.basename(EPF)
    item.Версия = info.Версия
    item.БезопасныйРежим = False
    item.Вид = fo.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
    item.Публикация = fo.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    item.ХранилищеОбработки = fo.NewObject("ХранилищеЗначения", fo.NewObject("ДвоичныеДанные", EPF))
    if settings is not None:
        item.ХранилищеНастроек = fo.NewObject("ХранилищеЗначения", settings)
    item.ОбменДанными.Загрузка = True
    item.Записать()
    return item.Ссылка


def stand_ref(fo):
    ref = find_ref(fo, "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                       "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления", {"Имя": OBJECT})
    return ref if ref is not None else register(fo)


def scenario(fo, params, title, timeout=3600, retry=False):
    """Сценарий стенда в фоновом задании; возвращает словарь: ошибка, лог, замеры {ключ: (количество, мс)}, данные.
    retry - повторить один раз, если задание завершилось без результата (первый запуск после смены обработки);
    только для сценариев, которые можно выполнить повторно."""
    out = run_job(fo, params, title, timeout)
    if retry and out["ошибка"].startswith("нет результата"):
        out = run_job(fo, params, title + " (повтор)", timeout)
    return out


def run_job(fo, params, title, timeout):
    ref = stand_ref(fo)
    task = fo.NewObject("Структура")
    task.Вставить("ИмяОбработки", OBJECT)
    task.Вставить("ИмяМетода", "ВыполнитьСценарийСтенда")
    task.Вставить("ПараметрыВыполнения", params)
    task.Вставить("ЭтоВнешняяОбработка", True)
    task.Вставить("ДополнительнаяОбработкаСсылка", ref)
    address = fo.ПоместитьВоВременноеХранилище(None, fo.NewObject("УникальныйИдентификатор"))
    started = time.time()
    job = fo.ФоновыеЗадания.Выполнить("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки",
                                      array(fo, [task, address]), "", f"IMDEV-9746 стенд: {title}")
    uid = job.УникальныйИдентификатор
    while True:
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно or time.time() - started > timeout:
            break
        time.sleep(0.5)
    out = {"сценарий": title, "длительность_с": round(time.time() - started, 2), "ошибка": "", "лог": "",
           "замеры": {}, "данные": None}
    if job.ИнформацияОбОшибке is not None:
        out["ошибка"] = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
    res = fo.ПолучитьИзВременногоХранилища(address)
    for _ in range(5):
        if res is not None or job.ИнформацияОбОшибке is not None:
            break
        # результат фонового задания иногда виден в хранилище с задержкой после смены состояния
        time.sleep(1)
        res = fo.ПолучитьИзВременногоХранилища(address)
    if res is not None:
        out["ошибка"] = out["ошибка"] or res.Ошибка
        out["лог"] = res.Лог
        for i in range(res.Замеры.Количество()):
            z = res.Замеры.Получить(i)
            out["замеры"][z.Ключ] = (int(z.Вызовов), int(z.Мс))
        out["данные"] = res.Данные
    elif not out["ошибка"]:
        out["ошибка"] = f"нет результата, состояние задания {fo.String(job.Состояние)}"
    log(f"   {title}: {out['длительность_с']} с", out["ошибка"].split("\n")[0][:300])
    return out


def checked(out):
    if out["ошибка"]:
        raise SystemExit(out["ошибка"])
    return out


def wait_jobs(fo, name, timeout=600):
    started = time.time()
    filt = fo.NewObject("Структура")
    filt.Вставить("Наименование", name)
    while True:
        jobs = fo.ФоновыеЗадания.ПолучитьФоновыеЗадания(filt)
        active = [jobs.Получить(i) for i in range(jobs.Количество())
                  if jobs.Получить(i).Состояние == fo.СостояниеФоновогоЗадания.Активно]
        if not active or time.time() - started > timeout:
            return round(time.time() - started, 1), len(active)
        time.sleep(1)


# ---------------------------------------------------------------- справочники стенда

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
    log(f"  создано свойство {name}")
    return obj.Ссылка


def properties(fo):
    props = {}
    for cls, suffix in (("комплаенс", "Комплаенс"), ("риски", "Риски")):
        props["ДатаАвтоустановкиЛимитов" + suffix] = ensure_property(fo, f"{PREFIX} Дата автоустановки лимитов ({cls})", "Дата")
        props["ВнешнийКодЭталонногоПортфеля" + suffix] = ensure_property(
            fo, f"{PREFIX} Внешний код эталонного портфеля ({cls})", "Строка")
        props["ЛимитыЗаведены" + suffix] = ensure_property(fo, f"{PREFIX} Лимиты заведены ({cls})", "Булево")
        props["Эталонный_портфель_лимитов_" + cls] = ensure_property(
            fo, f"{PREFIX} Эталонный портфель лимитов ({cls})", "СправочникСсылка.Портфели")
        props["Дата_распространения_правил_" + cls] = ensure_property(
            fo, f"{PREFIX} Дата распространения правил ({cls})", "Дата")
    props["Эталонный_портфель_лимитов"] = ensure_property(fo, f"{PREFIX} Эталонный портфель лимитов (стратегия)",
                                                          "СправочникСсылка.Стратегии")
    return props


def ensure_named(fo, catalog, table, name):
    ref = find_ref(fo, f"ВЫБРАТЬ Т.Ссылка КАК Ссылка ИЗ Справочник.{table} КАК Т ГДЕ Т.Наименование = &Имя", {"Имя": name})
    if ref is None:
        obj = getattr(fo.Справочники, catalog).СоздатьЭлемент()
        obj.Наименование = name
        obj.Записать()
        ref = obj.Ссылка
        log(f"  создан элемент {table}: {name}")
    return ref


def limit_class(fo, name):
    return find_ref(fo, "ВЫБРАТЬ К.Ссылка КАК Ссылка ИЗ Справочник.КлассыЛимитов КАК К ГДЕ К.Наименование = &Имя", {"Имя": name})


def portfolio(fo, code):
    return find_ref(fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П ГДЕ П.ВнешнийКод = &Код", {"Код": code})


def ensure_portfolio(fo, code, name, strategy):
    ref = portfolio(fo, code)
    if ref is not None:
        return ref
    sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                          "ГДЕ НЕ П.ПометкаУдаления И НЕ П.Предопределенный И П.ВнешнийКод = \"\" "
                          "УПОРЯДОЧИТЬ ПО П.Наименование")
    obj = sample.Скопировать()
    obj.Наименование = name
    obj.ВнешнийКод = code
    obj.НомерДоговора = code
    obj.Стратегия = strategy
    obj.ТипКлиента = fo.Справочники.ТипыКлиентов.ПустаяСсылка()
    obj.Записать()
    return obj.Ссылка


def sample_doc(fo, klass):
    """Проведенная установка лимитов по портфелю класса с наибольшим числом лимитов (не стендовая)."""
    return find_ref(fo, """ВЫБРАТЬ ПЕРВЫЕ 1 У.Ссылка КАК Ссылка, КОЛИЧЕСТВО(Л.Лимит) КАК Лимитов
        ИЗ Документ.УстановкаЛимитов КАК У ВНУТРЕННЕЕ СОЕДИНЕНИЕ Документ.УстановкаЛимитов.Лимиты КАК Л ПО Л.Ссылка = У.Ссылка
        ГДЕ У.Проведен И У.КлассЛимита = &Класс И НЕ У.ПометкаУдаления
            И У.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыОперацийУстановкиЛимитов.ПоПортфелю)
            И НЕ ВЫРАЗИТЬ(У.ОбъектНазначения КАК Справочник.Портфели).ВнешнийКод ПОДОБНО "T97%"
        СГРУППИРОВАТЬ ПО У.Ссылка УПОРЯДОЧИТЬ ПО Лимитов УБЫВ, У.Ссылка""", {"Класс": klass})


def originals(fo, doc, count):
    """Первые count лимитов образца: элементы с внутренней настройкой, без пометки удаления, не стендовые."""
    rows = query(fo, """ВЫБРАТЬ Л.Лимит КАК Лимит, Л.НомерСтроки КАК Н ИЗ Документ.УстановкаЛимитов.Лимиты КАК Л
        ГДЕ Л.Ссылка = &Д И НЕ Л.Лимит.ЭтоГруппа И НЕ Л.Лимит.ПометкаУдаления
            И Л.Лимит.СпособНастройкиЛимита = ЗНАЧЕНИЕ(Перечисление.СпособыНастройкиЛимита.Внутренний)
            И НЕ Л.Лимит.Наименование ПОДОБНО "T97%"
        УПОРЯДОЧИТЬ ПО Л.НомерСтроки""", {"Д": doc})
    if len(rows) < count:
        raise SystemExit(f"в образце {fo.String(doc)} {len(rows)} лимитов, нужно {count}")
    return [r["Лимит"] for r in rows[:count]]


def mode_limits(fo, mode, cls):
    """Копии лимитов стенда режима и класса в порядке строк установки эталона."""
    name = MODES[mode]["классы"][cls][0]
    return [r["Лимит"] for r in query(fo, """ВЫБРАТЬ Л.Лимит КАК Лимит ИЗ Документ.УстановкаЛимитов.Лимиты КАК Л
        ГДЕ Л.Ссылка.Проведен И Л.Ссылка.ОбъектНазначения = &Эталон И Л.Ссылка.КлассЛимита = &Класс
        УПОРЯДОЧИТЬ ПО Л.Ссылка.Дата УБЫВ, Л.НомерСтроки""",
                                      {"Эталон": portfolio(fo, MODES[mode]["эталон"]), "Класс": limit_class(fo, name)})]


def threshold_setting(fo):
    return find_ref(fo, """ВЫБРАТЬ ПЕРВЫЕ 1 Н.Ссылка КАК Ссылка ИЗ Справочник.НастройкиПороговДляПроверкиЛимитов КАК Н
        ГДЕ НЕ Н.ПометкаУдаления И НЕ Н.ИспользоватьРасширеннуюУстановкуПорогов УПОРЯДОЧИТЬ ПО Н.Наименование""")


def has_doc(fo, etalon, klass):
    return bool(query(fo, """ВЫБРАТЬ ПЕРВЫЕ 1 Д.Регистратор КАК Р
        ИЗ РегистрСведений.ДействующиеЛимитыПоПортфелю.СрезПоследних(, Портфель = &П И КлассЛимита = &К) КАК Д""",
                      {"П": etalon, "К": klass}))


def mailing(fo):
    account = find_ref(fo, "ВЫБРАТЬ У.Ссылка КАК Ссылка ИЗ Справочник.УчетныеЗаписиЭлектроннойПочты КАК У "
                           "ГДЕ У.Наименование = &Имя", {"Имя": MAIL_ACCOUNT})
    if account is None:
        raise SystemExit(f"нет учетной записи почты {MAIL_ACCOUNT} (127.0.0.1:18525)")
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "Рассылка")
    p.Вставить("Наименование", MAILING)
    p.Вставить("УчетнаяЗапись", account)
    p.Вставить("Адрес", MAIL_TO)
    return checked(scenario(fo, p, "настройка рассылки"))["данные"].Настройка


def settings(fo, mode, props, mail):
    m = MODES[mode]
    s = fo.NewObject("Структура")
    for key, ref in props.items():
        s.Вставить(key, ref)
    s.Вставить("КлассЛимитовКомплаенс", limit_class(fo, "Compliance"))
    s.Вставить("КлассЛимитовРиски", limit_class(fo, "Регуляторные"))
    for key in ["НастройкаРассылкиКомплаенс", "НастройкаРассылкиРиски", "НастройкаРассылкиПриУспешномАвтораспространении"]:
        s.Вставить(key, mail)
    users = fo.NewObject("СписокЗначений")
    users.Добавить(fo.ПараметрыСеанса.ТекущийПользователь)
    s.Вставить("СписокСервисныхПользователей", users)
    client_type = ensure_named(fo, "ТипыКлиентов", "ТипыКлиентов", m["тип"])
    for key in ["СписокТиповКлиентовКомплаенс", "СписокТиповКлиентовРиски"]:
        types = fo.NewObject("СписокЗначений")
        types.Добавить(client_type)
        s.Вставить(key, types)
    s.Вставить("ЭтоБазаРозничногоДУ", m["розница"])
    return s


# ---------------------------------------------------------------- команды

def ensure_conditions(fo, state):
    """Константа и версионирование лимитов как на Т-1. Исходные значения читаются и сохраняются до первого изменения:
    холодный запуск сценария может выполнить изменение и не вернуть результата."""
    if "исходно" not in state:
        rows = query(fo, """ВЫБРАТЬ Н.Вариант КАК Вариант ИЗ РегистрСведений.НастройкиВерсионированияОбъектов КАК Н
            ГДЕ Н.ТипОбъекта.ПолноеИмя = "Справочник.Лимиты" """)
        state["исходно"] = {"ИспользоватьКлассыЛимитов": bool(fo.Константы.ИспользоватьКлассыЛимитов.Получить()),
                            "ВерсионированиеЛимитов": fo.String(rows[0]["Вариант"]) if rows else ""}
        save_state(state)
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "Версионирование")
    p.Вставить("Включить", True)
    checked(scenario(fo, p, "версионирование лимитов при записи", retry=True))
    if not fo.Константы.ИспользоватьКлассыЛимитов.Получить():
        fo.Константы.ИспользоватьКлассыЛимитов.Установить(True)
        log("  константа ИспользоватьКлассыЛимитов = Да")


def step_prep(fo):
    state = load_state()
    register(fo)
    ensure_conditions(fo, state)
    props = properties(fo)
    strategy = ensure_named(fo, "Стратегии", "Стратегии", STRATEGY)
    mail = mailing(fo)
    setting = threshold_setting(fo)
    for mode, m in MODES.items():
        ensure_named(fo, "ТипыКлиентов", "ТипыКлиентов", m["тип"])
        etalon = ensure_portfolio(fo, m["эталон"], f"{PREFIX} Эталон {m['имя']}", strategy)
        for cls, (class_name, count, with_threshold) in m["классы"].items():
            klass = limit_class(fo, class_name)
            if has_doc(fo, etalon, klass):
                continue
            doc = sample_doc(fo, klass)
            src = originals(fo, doc, count)
            p = fo.NewObject("Структура")
            p.Вставить("Сценарий", "КопииЛимитов")
            p.Вставить("Образцы", array(fo, src))
            p.Вставить("Префикс", f"{PREFIX} {mode.upper()}")
            copies = checked(scenario(fo, p, f"копии лимитов {m['имя']} {class_name}"))["данные"].Лимиты
            p = fo.NewObject("Структура")
            p.Вставить("Сценарий", "УстановкаЛимитов")
            p.Вставить("Образец", doc)
            p.Вставить("Портфель", etalon)
            p.Вставить("Лимиты", copies)
            p.Вставить("Исходные", array(fo, src))
            checked(scenario(fo, p, f"установка лимитов эталона {m['имя']} {class_name}"))
        if mode == "o":
            p = fo.NewObject("Структура")
            p.Вставить("Сценарий", "ЭталонСтратегии")
            p.Вставить("Стратегия", strategy)
            p.Вставить("Эталон", etalon)
            p.Вставить("Авто", True)
            checked(scenario(fo, p, "эталон стратегии"))
        created = 0
        for i in range(1, CLIENTS[mode] + 1):
            code = f"{m['клиенты']}{i:03d}"
            if portfolio(fo, code) is None:
                ensure_portfolio(fo, code, f"{PREFIX} {m['имя']} клиент {i:03d}", strategy)
                created += 1
        log(f"  {m['имя']}: клиентов создано {created}")
        if mode == "r":
            records = fo.NewObject("Массив")
            for i in range(1, CLIENTS[mode] + 1):
                for suffix in ("Комплаенс", "Риски"):
                    rec = fo.NewObject("Структура")
                    rec.Вставить("Объект", portfolio(fo, f"{m['клиенты']}{i:03d}"))
                    rec.Вставить("Свойство", props["ВнешнийКодЭталонногоПортфеля" + suffix])
                    rec.Вставить("Значение", m["эталон"])
                    records.Добавить(rec)
            p = fo.NewObject("Структура")
            p.Вставить("Сценарий", "Сведения")
            p.Вставить("Записи", records)
            checked(scenario(fo, p, "внешний код эталона клиентам розницы"))
        # пороги эталона без фона (объем фона - команда volume)
        if state.get("объем", {}).get(mode) is None:
            set_volume(fo, mode, 0, setting)
    log("prep: готово")


def set_volume(fo, mode, count, setting=None):
    m = MODES[mode]
    etalon = portfolio(fo, m["эталон"])
    limits, with_threshold = [], []
    for cls, (class_name, total, thresholds) in m["классы"].items():
        cls_limits = mode_limits(fo, mode, cls)[:total]
        limits += cls_limits
        with_threshold += cls_limits[:thresholds]
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "ПорогиФон")
    p.Вставить("Лимиты", array(fo, limits))
    p.Вставить("ЛимитыЭталона", array(fo, with_threshold))
    p.Вставить("Эталон", etalon)
    p.Вставить("Количество", count)
    p.Вставить("Настройка", setting or threshold_setting(fo))
    p.Вставить("Период", date_1c(fo, VOLUME_PERIOD))
    p.Вставить("ИсключитьМаска", f"{PREFIX}%")
    out = checked(scenario(fo, p, f"пороги {m['имя']}: {count} портфелей на лимит"))
    d = out["данные"]
    log(f"  записей {d.Записей}, запись {d.МсЗаписи} мс, версии и кэш {d.МсВерсийИКэша} мс")
    state = load_state()
    state.setdefault("объем", {})[mode] = count
    save_state(state)


def next_clients(fo, mode, count):
    """Следующие клиенты режима без установки лимитов и без даты автоустановки."""
    m = MODES[mode]
    props = properties(fo)
    rows = query(fo, """ВЫБРАТЬ П.ВнешнийКод КАК Код, П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П
        ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.ДополнительныеСведения КАК Д ПО Д.Объект = П.Ссылка И Д.Свойство = &Свойство
        ГДЕ П.ВнешнийКод ПОДОБНО &Маска И Д.Объект ЕСТЬ NULL УПОРЯДОЧИТЬ ПО П.ВнешнийКод""",
                 {"Маска": m["клиенты"] + "%", "Свойство": props["ДатаАвтоустановкиЛимитовКомплаенс"]})
    if len(rows) < count:
        raise SystemExit(f"{m['имя']}: свободных клиентов {len(rows)}, нужно {count} - добавьте CLIENTS и prep")
    return rows[:count]


def set_client_type(fo, refs, client_type):
    for ref in refs:
        obj = ref.ПолучитьОбъект()
        obj.ТипКлиента = client_type
        obj.Записать()


def step_runs(fo, mode, runs, clients_per_run):
    state = load_state()
    m = MODES[mode]
    props = properties(fo)
    mail = mailing(fo)
    ref = register(fo, settings(fo, mode, props, mail))
    ensure_conditions(fo, state)
    client_type = ensure_named(fo, "ТипыКлиентов", "ТипыКлиентов", m["тип"])
    volume = load_state().get("объем", {}).get(mode)
    for run in range(runs):
        batch = next_clients(fo, mode, clients_per_run)
        set_client_type(fo, [r["Ссылка"] for r in batch], client_type)
        p = fo.NewObject("Структура")
        p.Вставить("Сценарий", "Распространение")
        p.Вставить("ОбработкаСсылка", ref)
        started = datetime.datetime.now()
        out = scenario(fo, p, f"распространение {m['имя']} ({', '.join(r['Код'] for r in batch)})")
        record = {"режим": mode, "объем": volume, "начало": started.isoformat(timespec="seconds"),
                  "клиенты": [r["Код"] for r in batch], "длительность_с": out["длительность_с"],
                  "ошибка": out["ошибка"], "замеры": out["замеры"], "лог": out["лог"][-2000:]}
        if m["розница"]:
            record["ожидание_записи_версий_с"], record["активных_заданий"] = wait_jobs(fo, "Запись версий лимитов")
        append("runs.jsonl", record)
        pairs = out["замеры"].get("СоздатьУстановкиЛимитов.Всего", (0, 0))[0]
        total = out["замеры"].get("Запуск.Всего", (0, 0))[1]
        log(f"  пар {pairs}, запуск {total} мс, порогов {out['замеры'].get('Пороги.ЗаписьНабора', (0, 0))}")
        if out["ошибка"]:
            raise SystemExit("остановлено по ошибке")


def step_bench(fo, repeats, limits_count):
    state = load_state()
    register(fo)
    ensure_conditions(fo, state)
    limits = mode_limits(fo, "o", "комплаенс")[:limits_count]
    probe = ensure_portfolio(fo, f"{PREFIX}_BENCH", f"{PREFIX} разбор записи порогов", ensure_named(
        fo, "Стратегии", "Стратегии", STRATEGY))
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "РазборЗаписиПорогов")
    p.Вставить("Лимиты", array(fo, limits))
    p.Вставить("Портфель", probe)
    p.Вставить("Настройка", threshold_setting(fo))
    p.Вставить("Повторов", repeats)
    out = checked(scenario(fo, p, f"разбор записи порогов: {limits_count} лимитов x {repeats}"))
    samples = out["данные"].Образцы
    rows = []
    for i in range(samples.Количество()):
        s = samples.Получить(i)
        rows.append({"лимит": int(s.Лимит), "повтор": int(s.Повтор), "шаг": s.Шаг, "мс": int(s.Мс), "признак": s.Признак})
    record = {"объем": state.get("объем", {}).get("o"), "начало": datetime.datetime.now().isoformat(timespec="seconds"),
              "образцы": rows}
    append("bench.jsonl", record)
    for step in dict.fromkeys(r["шаг"] for r in rows):
        values = [r["мс"] for r in rows if r["шаг"] == step]
        signs = {r["признак"].split(";")[0] for r in rows if r["шаг"] == step and r["признак"]}
        log(f"  {step:22} медиана {st.median(values):7.1f} мс, среднее {st.mean(values):7.1f}, макс {max(values)} "
            f"{'; '.join(sorted(signs))}")


def step_restore(fo):
    state = load_state()
    original = state.get("исходно")
    if not original:
        log("исходные значения не сохранялись")
        return
    fo.Константы.ИспользоватьКлассыЛимитов.Установить(original["ИспользоватьКлассыЛимитов"])
    if not original["ВерсионированиеЛимитов"]:
        p = fo.NewObject("Структура")
        p.Вставить("Сценарий", "Версионирование")
        p.Вставить("Включить", False)
        checked(scenario(fo, p, "версионирование лимитов: исходное (нет настройки)"))
    log(f"restore: ИспользоватьКлассыЛимитов = {original['ИспользоватьКлассыЛимитов']}, "
        f"версионирование лимитов = {original['ВерсионированиеЛимитов'] or 'нет настройки'}")
    del state["исходно"]
    save_state(state)


def step_report():
    runs = [json.loads(line) for line in open(os.path.join(RESULTS, "runs.jsonl"), encoding="utf-8")]
    summary = {"запуски": {}, "разбор": []}
    groups = {}
    for r in runs:
        if r["ошибка"]:
            continue
        groups.setdefault(f"{r['режим']}:{r['объем']}", []).append(r)
    for key, items in groups.items():
        pairs = sum(i["замеры"].get("СоздатьУстановкиЛимитов.Всего", (0, 0))[0] for i in items)
        keys = {}
        for i in items:
            for k, (n, ms) in i["замеры"].items():
                acc = keys.setdefault(k, [0, 0])
                acc[0] += n
                acc[1] += ms
        summary["запуски"][key] = {"запусков": len(items), "пар": pairs,
                                   "действия": {k: {"вызовов": n, "мс": ms, "мс_на_пару": round(ms / pairs, 1) if pairs else None}
                                                for k, (n, ms) in sorted(keys.items())}}
        log(f"== {key}: запусков {len(items)}, пар {pairs}")
        total = keys.get("Запуск.Всего", [0, 1])[1]
        for k, (n, ms) in sorted(keys.items(), key=lambda kv: -kv[1][1]):
            log(f"   {k:38} {n:5} вызовов {ms:9} мс  {100 * ms / total:5.1f}%  {ms / pairs if pairs else 0:8.1f} мс/пару")
    bench_path = os.path.join(RESULTS, "bench.jsonl")
    if os.path.exists(bench_path):
        for line in open(bench_path, encoding="utf-8"):
            b = json.loads(line)
            if "образцы" not in b:
                continue
            steps = dict.fromkeys(r["шаг"] for r in b["образцы"])
            row = {"объем": b["объем"], "начало": b["начало"],
                   "медиана_мс": {s: st.median([r["мс"] for r in b["образцы"] if r["шаг"] == s]) for s in steps},
                   "среднее_мс": {s: round(st.mean([r["мс"] for r in b["образцы"] if r["шаг"] == s]), 1) for s in steps}}
            summary["разбор"].append(row)
            log(f"== разбор, объем {b['объем']}: " + ", ".join(f"{s} {v}" for s, v in row["медиана_мс"].items()))
    with open(os.path.join(RESULTS, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "report":
        step_report()
        return
    fo = connect("wim_fo")
    if cmd == "prep":
        step_prep(fo)
    elif cmd == "volume":
        register(fo)
        ensure_conditions(fo, load_state())
        set_volume(fo, sys.argv[3] if len(sys.argv) > 3 else "o", int(sys.argv[2]))
    elif cmd == "ordinary":
        step_runs(fo, "o", int(sys.argv[2]), 1)
    elif cmd == "retail":
        step_runs(fo, "r", int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 2)
    elif cmd == "bench":
        step_bench(fo, int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 5)
    elif cmd == "restore":
        step_restore(fo)
    else:
        print(__doc__)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
