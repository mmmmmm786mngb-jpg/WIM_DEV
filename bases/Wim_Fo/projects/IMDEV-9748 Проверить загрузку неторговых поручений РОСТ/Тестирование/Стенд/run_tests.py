# -*- coding: utf-8 -*-
"""Тест обработки «Загрузка неторговых поручений РОСТ»: 1.07 (ПРОД) против 1.08 (IMDEV-9748) на dev ФО (WIN_FO_server).

Правки 1.08: письмо без созданных поручений только при ошибке (важность 2), тело письма оформляется HTML-абзацами,
не выполняется запрос суммы погашенных купонов, отбор портфелей по дополнительным сведениям с условием
Объект ССЫЛКА Справочник.Портфели.

Обе версии регистрируются в один элемент справочника дополнительных обработок (ЗагрузкаНеторговыхПорученийРОСТ):
перед каждым запуском записываются двоичные данные версии и ее настройки. У версии свои портфели (код T9748_A_* для
1.07, T9748_B_* для 1.08) и свое свойство статуса, поэтому запуски версий не видят данных друг друга. Обработку
вызывает тестовая обработка T9530_ТестРОСТ 1.7 из базы (сценарий «Неторговые», ЭтоТест = Истина: сумма на брокерском
счете без адаптера FIX). Нужны заглушки: mock_dm_service.py (1С:ДО, порт 18530) и mock_smtp.py (почта, порт 18525).

    python run_tests.py prep          свойства, статусы, портфели с субпортфелями, учетная запись почты
    python run_tests.py scenarios     сценарии С1-С6 для каждой версии
    python run_tests.py extra         сценарии С7 (сервис 1С:ДО недоступен), С8 (поручение и предупреждение), С9 (отказ и поручение)
    python run_tests.py bench [N]     N пустых запусков каждой версии поочередно (15 портфелей в поиске, сумма 0)
    python run_tests.py queries [N]   время запросов купонов и отбора портфелей, сверка результатов отбора
    python run_tests.py collect       поручения, статусы, регистры, замеры, письма -> results/state.json
    python run_tests.py close         конечный статус «ДС выведены» всем портфелям T9748
"""
import datetime
import email
import email.header
import email.policy
import glob
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
STAGE4 = glob.glob(r"C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9530*\Тестирование\Стенд_замеры")[0]
sys.path.insert(0, STAGE4)
import run_stage4_tests as s4  # noqa: E402

RESULTS = os.path.join(HERE, "results")
MAIL_DIR = os.path.join(RESULTS, "mail")
# Серия данных: у каждой серии свои портфели и свойства (поручения прошлой серии мешают сценариям).
# Серия 1 (теги A/B) - первая сборка 1.08 с пунктом 3; серия 2 (C/D) - 1.08 с пунктами 1, 2, 4;
# серия 3 (E/F) - итоговая сборка 1.08 без закомментированных исходных строк.
SERIES = os.environ.get("T9748_SERIES", "3")
TAGS = {"1": ("A", "B"), "2": ("C", "D"), "3": ("E", "F")}[SERIES]
STATE = os.path.join(RESULTS, f"state_{SERIES}.json")
RULES = os.path.join(RESULTS, "mock_dm_rules.json")
EPF_NAME = "внЗагрузкаНеторговыхПорученийРОСТ.epf"
VERSIONS = {
    "1.07": (TAGS[0], os.path.join(TASK, "ОРИГИНАЛ_1_07", EPF_NAME)),
    "1.08": (TAGS[1], os.path.join(TASK, "УСКОРЕНО_1_08", EPF_NAME)),
}
PREFIX = "T9748"
GROUPS = {"N": 7, "Q": 15}
NT_STATUSES = s4.NT_STATUSES
MOCK_URL = "http://127.0.0.1:18530/dm?wsdl"
MOCK_DOWN_URL = "http://127.0.0.1:18531/dm?wsdl"
MAIL_ACCOUNT = f"{PREFIX} Тестовая почта"
MAIL_TO = "rost-ops@t9748.test"
HARNESS = "T9530_ТестРОСТ"
log = s4.log


# ---------------------------------------------------------------- состояние

def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"runs": []}


def save_state(state):
    os.makedirs(RESULTS, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def write_rules(rules):
    os.makedirs(RESULTS, exist_ok=True)
    with open(RULES, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def code(version, group, i):
    return f"{PREFIX}_{VERSIONS[version][0]}_{group}{i:02d}"


def mail_files():
    if not os.path.isdir(MAIL_DIR):
        return []
    return sorted(n for n in os.listdir(MAIL_DIR) if n.endswith(".eml"))


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- справочники

def context(fo, version):
    prop = s4.ensure_property(fo, f"{PREFIX} Статус неторговых {VERSIONS[version][0]}", "СправочникСсылка.ЗначенияСвойствОбъектов")
    prop_date = s4.ensure_property(fo, f"{PREFIX} Дата статуса неторговых {VERSIONS[version][0]}", "Дата")
    statuses = s4.ensure_status_values(fo, prop, NT_STATUSES)
    flag_loaded = s4.ensure_property(fo, f"{PREFIX} Позиция выгружена", "Булево")
    flag_recalc = s4.ensure_property(fo, f"{PREFIX} Дата пересчета РСА", "Дата")
    return {"prop": prop, "prop_date": prop_date, "statuses": statuses, "flag_loaded": flag_loaded,
            "flag_recalc": flag_recalc}


def ensure_mail_account(fo):
    ref = s4.find_ref(fo, "ВЫБРАТЬ У.Ссылка КАК Ссылка ИЗ Справочник.УчетныеЗаписиЭлектроннойПочты КАК У "
                          "ГДЕ У.Наименование = &Имя", {"Имя": MAIL_ACCOUNT})
    if ref is not None:
        return ref
    obj = fo.Справочники.УчетныеЗаписиЭлектроннойПочты.СоздатьЭлемент()
    obj.Наименование = MAIL_ACCOUNT
    obj.АдресЭлектроннойПочты = "rost-robot@t9748.test"
    obj.ИспользоватьДляОтправки = True
    obj.СерверИсходящейПочты = "127.0.0.1"
    obj.ПортСервераИсходящейПочты = 18525
    obj.ВремяОжидания = 30
    obj.Записать()
    log(f"  создана учетная запись почты {MAIL_ACCOUNT}")
    return obj.Ссылка


def ensure_portfolios(fo):
    existing = {r["Код"] for r in s4.query(fo, "ВЫБРАТЬ П.ВнешнийКод КАК Код ИЗ Справочник.Портфели КАК П "
                                               "ГДЕ П.ВнешнийКод ПОДОБНО &Маска", {"Маска": f"{PREFIX}_%"})}
    sample = s4.find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                             "ГДЕ НЕ П.ПометкаУдаления И НЕ П.Предопределенный И П.ВнешнийКод = \"\" "
                             "УПОРЯДОЧИТЬ ПО П.Наименование")
    strategy = s4.ensure_strategy(fo)
    place = s4.ensure_place(fo)
    created = 0
    for version in VERSIONS:
        for group, count in GROUPS.items():
            for i in range(1, count + 1):
                c = code(version, group, i)
                if c in existing:
                    continue
                name = f"{PREFIX} {version} {group}{i:02d}"
                obj = sample.Скопировать()
                obj.Наименование = name
                obj.ВнешнийКод = c
                obj.НомерДоговора = c
                obj.Записать()
                sub = fo.Справочники.Субпортфели.СоздатьЭлемент()
                sub.Наименование = name
                sub.КодСчета = c
                sub.Портфель = obj.Ссылка
                sub.Стратегия = strategy
                sub.МестоХранения = place
                sub.Записать()
                created += 1
    log(f"  портфелей с субпортфелями создано {created}")


def portfolios(fo, version, group=None):
    mask = f"{PREFIX}_{VERSIONS[version][0]}_" + (group or "") + "%"
    rows = s4.query(fo, "ВЫБРАТЬ П.ВнешнийКод КАК Код, П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                        "ГДЕ П.ВнешнийКод ПОДОБНО &Маска УПОРЯДОЧИТЬ ПО П.ВнешнийКод", {"Маска": mask})
    return {r["Код"]: r["Ссылка"] for r in rows}


def step_prep(fo):
    for version in VERSIONS:
        context(fo, version)
    ensure_mail_account(fo)
    ensure_portfolios(fo)


# ---------------------------------------------------------------- запуски

def harness_ref(fo):
    ref = s4.find_ref(fo, "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                          "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления", {"Имя": HARNESS})
    version = fo.String(ref.Версия)
    if version != "1.7":
        raise RuntimeError(f"в базе тестовая обработка {HARNESS} версии {version}, нужна 1.7")
    return ref


def settings(fo, version, ctx, mail_account, url=MOCK_URL):
    table = fo.NewObject("ТаблицаЗначений")
    table.Колонки.Добавить("ПочтовыйЯщик")
    table.Колонки.Добавить("Представление")
    row = table.Добавить()
    row.ПочтовыйЯщик = MAIL_TO
    row.Представление = "Тест IMDEV-9748"
    st = ctx["statuses"]
    s = fo.NewObject("Структура")
    s.Вставить("ПочтовыйЛогин", mail_account)
    s.Вставить("СписокРассылки", fo.XMLСтрока(fo.NewObject("ХранилищеЗначения", table)))
    s.Вставить("АдресWS", url)
    s.Вставить("Логин", "")
    s.Вставить("Пароль", "")
    s.Вставить("НеКонтролироватьДостаточностьДС", True)
    s.Вставить("КодСчетаБрокер", PREFIX)
    s.Вставить("ДопРеквизитСтатусПортфеля", ctx["prop"])
    s.Вставить("СтатусДляПоиска", st["Поиск"])
    s.Вставить("СтатусДСОтправленыБрокеру", st["ОтправленыБрокеру"])
    s.Вставить("СтатусДляПеревода", st["Перевод"])
    s.Вставить("СтатусПоданоПоручениеНаВыводДС_СБрокера", st["ВыводПодан"])
    s.Вставить("СтатусДСВыведены", st["Выведены"])
    s.Вставить("ДопРеквизитДатаОперации", ctx["prop_date"])
    s.Вставить("АктивРубли", s4.rub_asset(fo))
    s.Вставить("ПризнакПозицияВыгружена", ctx["flag_loaded"])
    s.Вставить("ПризнакДатаПересчетаРСА", ctx["flag_recalc"])
    return s


class Stand:
    def __init__(self, fo):
        self.fo = fo
        self.harness = harness_ref(fo)
        self.mail = ensure_mail_account(fo)
        self.ctx = {v: context(fo, v) for v in VERSIONS}
        self.refs = {v: portfolios(fo, v) for v in VERSIONS}

    def set_status(self, version, codes, status_key, title):
        ctx = self.ctx[version]
        refs = [self.refs[version][c] for c in codes]
        return s4.set_statuses(self.fo, self.harness, refs, ctx["prop"], ctx["prop_date"],
                               ctx["statuses"][status_key], title)

    def set_status_dated(self, version, c, status_key, hours_ago):
        """Статус с датой статуса в прошлом: перевод «ДС выведены» срабатывает через 30 минут после подачи вывода."""
        ctx = self.ctx[version]
        when = s4.query(self.fo, "ВЫБРАТЬ ДОБАВИТЬКДАТЕ(&Д, ЧАС, &Ч) КАК Д",
                        {"Д": self.fo.ТекущаяДатаСеанса(), "Ч": -hours_ago})[0]["Д"]
        records = self.fo.NewObject("Массив")
        for prop, value in ((ctx["prop"], ctx["statuses"][status_key]), (ctx["prop_date"], when)):
            rec = self.fo.NewObject("Структура")
            rec.Вставить("Объект", self.refs[version][c])
            rec.Вставить("Свойство", prop)
            rec.Вставить("Значение", value)
            records.Добавить(rec)
        p = self.fo.NewObject("Структура")
        p.Вставить("Сценарий", "Сведения")
        p.Вставить("Записи", records)
        return s4.run_harness(self.fo, self.harness, p, f"{version}: {c} статус {status_key} {hours_ago} ч назад")

    def run(self, version, scenario, url=MOCK_URL):
        path = VERSIONS[version][1]
        ref = s4.register_epf(self.fo, "ЗагрузкаНеторговыхПорученийРОСТ", path,
                              settings(self.fo, version, self.ctx[version], self.mail, url))
        before = mail_files()
        start_1c = self.fo.ТекущаяДатаСеанса()
        start_utc = utc_now()
        p = self.fo.NewObject("Структура")
        p.Вставить("Сценарий", "Неторговые")
        p.Вставить("ОбработкаСсылка", ref)
        p.Вставить("ЭтоТест", True)
        out = s4.run_harness(self.fo, self.harness, p, f"IMDEV-9748 {scenario} ({version})")
        end_utc = utc_now()
        time.sleep(1)
        letters = [n for n in mail_files() if n not in before]
        return {"версия": version, "сценарий": scenario, "начало_utc": start_utc.isoformat(),
                "конец_utc": end_utc.isoformat(), "длительность_с": out.get("длительность_с"),
                "состояние": out.get("состояние"), "ошибка": out.get("ошибка") or out.get("ошибка_задания") or "",
                "лог": out.get("лог") or "",
                # Нет - тестовая обработка не вернула результат через временное хранилище (лог неизвестен).
                "результат_получен": "поручений" in out, "письма": letters, "журнал": s4.event_log(self.fo, start_1c)}


# ---------------------------------------------------------------- сценарии

def scenario_rules():
    rules = {}
    for version in VERSIONS:
        rules[code(version, "N", 1)] = {"Сумма": 50000, "ОтправленоНаБрокерский": False}
        rules[code(version, "N", 2)] = {"Сумма": 100000, "ОтправленоНаБрокерский": True}
        rules[code(version, "N", 3)] = {"Сумма": 200000, "ОтправленоНаБрокерский": True}
        rules[code(version, "N", 4)] = "fail"
        rules[code(version, "N", 6)] = {"Сумма": 0, "ОтправленоНаБрокерский": False}
        rules[code(version, "N", 7)] = {"Сумма": 400000, "ОтправленоНаБрокерский": True}
    return rules


def step_scenarios(fo):
    stand = Stand(fo)
    state = load_state()
    write_rules(scenario_rules())

    def both(name, prepare=None, after=None):
        for version in VERSIONS:
            if prepare:
                prepare(version)
            run = stand.run(version, name)
            state["runs"].append(run)
            save_state(state)
            log(f"  {name} {version}: писем {len(run['письма'])}, лог: {run['лог'].strip()[:150]!r}")
            if after:
                after(version)

    # С1: ни одного портфеля в статусах поиска - предупреждение "Не найдено портфелей", поручений 0
    both("С1.НетПортфелей")
    # С2: Н01 - деньги поступили, но не отправлены на брокерский счет; Н06 - сумма 0
    both("С2.ТолькоПредупреждения",
         lambda v: stand.set_status(v, [code(v, "N", 1), code(v, "N", 6)], "Поиск", f"{v}: Н01, Н06 поиск"),
         lambda v: stand.set_status(v, [code(v, "N", 1), code(v, "N", 6)], "Выведены", f"{v}: Н01, Н06 закрыть"))
    # С3: Н02, Н03 - деньги на брокерском счете, создаются 2 поручения
    both("С3.СозданиеПоручений",
         lambda v: stand.set_status(v, [code(v, "N", 2), code(v, "N", 3)], "Поиск", f"{v}: Н02, Н03 поиск"))
    # С4: Н02 снова в поиске, у портфеля уже есть проведенное поручение - предупреждение, поручений 0
    both("С4.УжеЕстьПоручение",
         lambda v: stand.set_status(v, [code(v, "N", 2)], "Поиск", f"{v}: Н02 поиск"),
         lambda v: stand.set_status(v, [code(v, "N", 2), code(v, "N", 3)], "Выведены", f"{v}: Н02, Н03 закрыть"))
    # С5: Н04 - отказ сервиса 1С:ДО - ошибка (важность 2), поручений 0
    both("С5.ОтказСервиса",
         lambda v: stand.set_status(v, [code(v, "N", 4)], "Поиск", f"{v}: Н04 поиск"),
         lambda v: stand.set_status(v, [code(v, "N", 4)], "Выведены", f"{v}: Н04 закрыть"))
    # С6: Н05 подан вывод 2 часа назад - перевод в "ДС выведены", портфелей в поиске нет
    both("С6.ПереводДСВыведены", lambda v: stand.set_status_dated(v, code(v, "N", 5), "ВыводПодан", 2))
    log(f"  сценариев {len(state['runs'])}")


def step_extra(fo):
    stand = Stand(fo)
    state = load_state()
    rules = scenario_rules()
    for version in VERSIONS:
        rules[code(version, "N", 6)] = {"Сумма": 300000, "ОтправленоНаБрокерский": True}
    write_rules(rules)
    for version in VERSIONS:
        # С7: сервис 1С:ДО недоступен (WSОпределения не создается) - ошибка без исключения, поручений 0
        stand.set_status(version, [code(version, "N", 4)], "Поиск", f"{version}: Н04 поиск")
        run = stand.run(version, "С7.СервисНедоступен", MOCK_DOWN_URL)
        state["runs"].append(run)
        stand.set_status(version, [code(version, "N", 4)], "Выведены", f"{version}: Н04 закрыть")
        log(f"  С7 {version}: писем {len(run['письма'])}, лог: {run['лог'].strip()[:150]!r}")
        # С8: Н06 - деньги на брокерском счете (поручение), Н01 - не отправлены брокеру (предупреждение)
        stand.set_status(version, [code(version, "N", 1), code(version, "N", 6)], "Поиск", f"{version}: Н01, Н06 поиск")
        run = stand.run(version, "С8.ПоручениеИПредупреждение")
        state["runs"].append(run)
        stand.set_status(version, [code(version, "N", 1), code(version, "N", 6)], "Выведены", f"{version}: Н01, Н06 закрыть")
        log(f"  С8 {version}: писем {len(run['письма'])}, лог: {run['лог'].strip()[:150]!r}")
        # С9: Н04 - отказ 1С:ДО, Н07 - деньги на брокерском счете; в 1.08 отказ не прерывает обработку Н07
        stand.set_status(version, [code(version, "N", 4), code(version, "N", 7)], "Поиск", f"{version}: Н04, Н07 поиск")
        run = stand.run(version, "С9.ОтказИПоручение")
        state["runs"].append(run)
        stand.set_status(version, [code(version, "N", 4), code(version, "N", 7)], "Выведены", f"{version}: Н04, Н07 закрыть")
        log(f"  С9 {version}: писем {len(run['письма'])}, лог: {run['лог'].strip()[:200]!r}")
        save_state(state)


def step_bench(fo, count):
    stand = Stand(fo)
    state = load_state()
    write_rules(scenario_rules())
    for version in VERSIONS:
        stand.set_status(version, list(stand.refs[version].keys() & {code(version, "Q", i) for i in range(1, 16)}),
                         "Поиск", f"{version}: 15 портфелей Q поиск")
    for i in range(count):
        order = list(VERSIONS) if i % 2 == 0 else list(reversed(VERSIONS))
        for version in order:
            run = stand.run(version, f"Б.Пустой{i + 1:02d}")
            state["runs"].append(run)
            save_state(state)
    for version in VERSIONS:
        stand.set_status(version, [code(version, "Q", i) for i in range(1, 16)], "Выведены", f"{version}: Q закрыть")


# ---------------------------------------------------------------- запросы

COUPON_QUERY = """ВЫБРАТЬ
	т.Актив КАК Актив,
	т.Актив.Объект КАК АктивОбъект,
	СУММА(т.Количество) КАК Количество
ПОМЕСТИТЬ втАктивы
ИЗ
	РегистрСведений.ФактическаяПозиция КАК т
ГДЕ
	т.Дата = &НаДату
СГРУППИРОВАТЬ ПО
	т.Актив,
	т.Актив.Объект
;
ВЫБРАТЬ
	т.Облигация КАК Облигация,
	т.Документ КАК Документ
ПОМЕСТИТЬ втКупоны
ИЗ
	РегистрСведений.КупонноеРасписаниеПоОблигациям.СрезПоследних(
			КОНЕЦПЕРИОДА(&НаДату, ДЕНЬ),
			Облигация В
				(ВЫБРАТЬ
					т.АктивОбъект
				ИЗ
					втАктивы КАК т)) КАК т
;
ВЫБРАТЬ
	втКупоны.Облигация КАК Облигация,
	втАктивы.Количество КАК Количество,
	ЕСТЬNULL(тКупоны.РазмерДоходаВРублях, 0) * ЕСТЬNULL(втАктивы.Количество, 0) КАК СуммаКупонов
ИЗ
	втКупоны КАК втКупоны
		ЛЕВОЕ СОЕДИНЕНИЕ втАктивы КАК втАктивы
		ПО втКупоны.Облигация = втАктивы.АктивОбъект
		ЛЕВОЕ СОЕДИНЕНИЕ Документ.КупонноеРасписание.Купоны КАК тКупоны
		ПО втКупоны.Документ = тКупоны.Ссылка
ГДЕ
	тКупоны.ДатаОкончанияКупонногоПериода = &НаДату
ИТОГИ
	СУММА(СуммаКупонов)
ПО
	ОБЩИЕ"""

SELECTION_QUERY = """ВЫБРАТЬ РАЗРЕШЕННЫЕ
	ДополнительныеСведения.Объект КАК Портфель,
	ДополнительныеСведения.Значение КАК СтатусПортфеля,
	ВЫРАЗИТЬ(ДополнительныеСведения.Объект КАК Справочник.Портфели).НомерДоговора КАК НомерДоговора,
	ВЫРАЗИТЬ(ДополнительныеСведения.Объект КАК Справочник.Портфели).КодПортфеля КАК КодПортфеля
ПОМЕСТИТЬ ВТ_Портфели
ИЗ
	РегистрСведений.ДополнительныеСведения КАК ДополнительныеСведения
ГДЕ
	ДополнительныеСведения.Свойство = &Свойство
	И ДополнительныеСведения.Значение В(&Значение)
	{ССЫЛКА}
;
ВЫБРАТЬ
	ВТ_Портфели.Портфель КАК Портфель,
	ВТ_Портфели.СтатусПортфеля КАК СтатусПортфеля,
	ВТ_Портфели.НомерДоговора КАК НомерДоговора,
	ВТ_Портфели.КодПортфеля КАК КодПортфеля,
	МАКСИМУМ(Поручение.Ссылка) КАК СсылкаНаПоручение,
	СУММА(Поручение.СуммаПоручения) КАК СуммаПоручения
ИЗ
	ВТ_Портфели КАК ВТ_Портфели
		ЛЕВОЕ СОЕДИНЕНИЕ Документ.Поручение КАК Поручение
		ПО ВТ_Портфели.Портфель = Поручение.Портфель
			И (Поручение.Проведен)
			И (Поручение.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.НеторговоеПоручение))
			И (Поручение.ВидОперацииНеторговогоПоручения = ЗНАЧЕНИЕ(Перечисление.ВидыОперацийНеторговыхПоручений.Ввод))
СГРУППИРОВАТЬ ПО
	ВТ_Портфели.Портфель,
	ВТ_Портфели.СтатусПортфеля,
	ВТ_Портфели.НомерДоговора,
	ВТ_Портфели.КодПортфеля"""


def timed(fo, text, params, reps):
    times, rows = [], None
    for _ in range(reps):
        t = time.perf_counter()
        rows = s4.query(fo, text, params)
        times.append(time.perf_counter() - t)
    return times, rows


def stats(times):
    s = sorted(times)
    return {"n": len(s), "медиана_мс": round(s[len(s) // 2] * 1000, 1), "мин_мс": round(s[0] * 1000, 1),
            "макс_мс": round(s[-1] * 1000, 1), "среднее_мс": round(sum(s) / len(s) * 1000, 1)}


def step_queries(fo, reps):
    stand = Stand(fo)
    state = load_state()
    result = {}
    today = s4.today_1c(fo)
    max_date = s4.query(fo, "ВЫБРАТЬ МАКСИМУМ(Ф.Дата) КАК Д ИЗ РегистрСведений.ФактическаяПозиция КАК Ф")[0]["Д"]
    for label, day in (("сегодня", today), ("последняя_дата_позиции", max_date)):
        rows = s4.query(fo, "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ РегистрСведений.ФактическаяПозиция КАК Ф ГДЕ Ф.Дата = &Д",
                        {"Д": day})
        times, _ = timed(fo, COUPON_QUERY, {"НаДату": day}, reps)
        result[f"купоны_{label}"] = {"дата": fo.String(day), "строк_позиции": int(rows[0]["К"]), **stats(times)}
    # Отбор портфелей: старый и новый текст поочередно, свойство версии 1.07 со статусами поиска.
    ctx = stand.ctx["1.07"]
    values = s4.refs_array(fo, [ctx["statuses"]["Поиск"], ctx["statuses"]["ОтправленыБрокеру"]])
    old_text = SELECTION_QUERY.replace("{ССЫЛКА}", "")
    new_text = SELECTION_QUERY.replace("{ССЫЛКА}", "И ДополнительныеСведения.Объект ССЫЛКА Справочник.Портфели")
    old_times, new_times = [], []
    for i in range(reps):
        for text, bucket in ((old_text, old_times), (new_text, new_times))[:: 1 if i % 2 == 0 else -1]:
            t = time.perf_counter()
            s4.query(fo, text, {"Свойство": ctx["prop"], "Значение": values})
            bucket.append(time.perf_counter() - t)
    result["отбор_1.07"] = stats(old_times)
    result["отбор_1.08"] = stats(new_times)
    # Сверка: для каждого свойства-статуса, у которого есть значения у не-портфелей, результаты старого и нового
    # отбора по всем его значениям.
    total = s4.query(fo, "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ РегистрСведений.ДополнительныеСведения")[0]["К"]
    others = s4.query(fo, """ВЫБРАТЬ Д.Свойство КАК Свойство, ПРЕДСТАВЛЕНИЕ(Д.Свойство) КАК Имя, КОЛИЧЕСТВО(*) КАК К
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ НЕ Д.Объект ССЫЛКА Справочник.Портфели
        СГРУППИРОВАТЬ ПО Д.Свойство""")
    checks = []
    props = s4.query(fo, """ВЫБРАТЬ РАЗЛИЧНЫЕ Д.Свойство КАК Свойство, ПРЕДСТАВЛЕНИЕ(Д.Свойство) КАК Имя
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ Д.Значение ССЫЛКА Справочник.ЗначенияСвойствОбъектов""")
    for p in props:
        vals = s4.query(fo, """ВЫБРАТЬ РАЗЛИЧНЫЕ Д.Значение КАК З ИЗ РегистрСведений.ДополнительныеСведения КАК Д
            ГДЕ Д.Свойство = &С""", {"С": p["Свойство"]})
        arr = s4.refs_array(fo, [v["З"] for v in vals])
        a = s4.query(fo, old_text, {"Свойство": p["Свойство"], "Значение": arr})
        b = s4.query(fo, new_text, {"Свойство": p["Свойство"], "Значение": arr})
        key = lambda rows: sorted(fo.String(r["Портфель"]) + "|" + fo.String(r["СсылкаНаПоручение"]) for r in rows)  # noqa: E731
        checks.append({"свойство": p["Имя"], "строк_1.07": len(a), "строк_1.08": len(b), "совпадает": key(a) == key(b)})
    result["сверка_отбора"] = {"строк_регистра": int(total),
                               "строк_не_портфелей": [{"свойство": o["Имя"], "строк": int(o["К"])} for o in others],
                               "свойств_статусов": len(checks), "совпало": sum(1 for c in checks if c["совпадает"]),
                               "проверки": checks}
    state["запросы"] = result
    save_state(state)
    log(json.dumps({k: v for k, v in result.items() if k != "сверка_отбора"}, ensure_ascii=False))
    log(f"  сверка отбора: свойств {len(checks)}, совпало {result['сверка_отбора']['совпало']}, "
        f"строк не-портфелей {sum(o['строк'] for o in result['сверка_отбора']['строк_не_портфелей'])}")


# ---------------------------------------------------------------- сбор

def to_text(fo, v):
    return s4.to_text(fo, v)


def utc_of_ms(ms):
    return datetime.datetime(1, 1, 1) + datetime.timedelta(milliseconds=ms)


def collect_measurements(fo, state):
    first = min(datetime.datetime.fromisoformat(r["начало_utc"]) for r in state["runs"])
    since_local = first + datetime.timedelta(hours=3) - datetime.timedelta(minutes=5)
    rows = s4.query(fo, """ВЫБРАТЬ
            З.КлючеваяОперация.Имя КАК Ключ, З.ДатаНачалаЗамера КАК Начало, З.ВремяВыполнения КАК Время,
            З.ВесЗамера КАК Вес, З.Комментарий КАК Комментарий, З.ВыполненСОшибкой КАК Ошибка
        ИЗ РегистрСведений.ЗамерыВремени КАК З
        ГДЕ З.ДатаЗаписиЛокальная >= &Начало И З.КлючеваяОперация.Имя ПОДОБНО "ЗагрузкаНеторговыхПорученийРОСТ%"
        УПОРЯДОЧИТЬ ПО Начало""", {"Начало": s4.date_1c(fo, since_local)})
    windows = [(datetime.datetime.fromisoformat(r["начало_utc"]) - datetime.timedelta(seconds=2),
                datetime.datetime.fromisoformat(r["конец_utc"]) + datetime.timedelta(seconds=2), r) for r in state["runs"]]
    unmatched = 0
    for r in state["runs"]:
        r["замеры"] = []
    for m in rows:
        start = utc_of_ms(float(m["Начало"]))
        comment = m["Комментарий"] or ""
        try:
            comment = json.loads(comment).get("ДопИнф", "")
        except ValueError:
            pass
        rec = {"ключ": m["Ключ"], "время_с": float(m["Время"]), "вес": float(m["Вес"]), "комментарий": comment,
               "ошибка": bool(m["Ошибка"])}
        # Замер начинается внутри фонового задания запуска: относится к последнему запуску, начавшемуся до него.
        owner = None
        for a, b, run in windows:
            if datetime.datetime.fromisoformat(run["начало_utc"]) <= start <= b:
                owner = run
        if owner is None:
            unmatched += 1
        else:
            owner["замеры"].append(rec)
    return unmatched


def parse_mail(name):
    with open(os.path.join(MAIL_DIR, name), "rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)
    body, attachments = "", []
    for part in msg.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if filename:
            attachments.append({"имя": filename, "байт": len(part.get_payload(decode=True) or b"")})
        elif part.get_content_type() in ("text/html", "text/plain") and not body:
            body = part.get_content()
    return {"файл": name, "тема": str(msg["Subject"] or ""), "кому": str(msg["To"] or ""),
            "важность": str(msg["Importance"] or msg["X-Priority"] or ""), "тип": msg.get_content_type(),
            "тело": body, "вложения": attachments}


def step_collect(fo):
    state = load_state()
    unmatched = collect_measurements(fo, state)
    mask = f"{PREFIX}_[{TAGS[0]}{TAGS[1]}]_%"
    orders = s4.query(fo, """ВЫБРАТЬ П.Портфель.ВнешнийКод КАК Портфель, П.ВидОперацииНеторговогоПоручения КАК Вид,
            П.СуммаПоручения КАК Сумма, П.Количество КАК Количество, П.Проведен КАК Проведен,
            П.ПометкаУдаления КАК Удален, П.Субпортфель.КодСчета КАК Субпортфель, П.Комментарий КАК Комментарий
        ИЗ Документ.Поручение КАК П ГДЕ П.Портфель.ВнешнийКод ПОДОБНО &М УПОРЯДОЧИТЬ ПО П.Портфель.ВнешнийКод, П.Дата""",
                      {"М": mask})
    state["поручения"] = [{k: (float(v) if k in ("Сумма", "Количество") else to_text(fo, v)) for k, v in r.items()}
                          for r in orders]
    props = s4.query(fo, """ВЫБРАТЬ ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод КАК Портфель,
            Д.Свойство.Наименование КАК Свойство, Д.Значение КАК Значение
        ИЗ РегистрСведений.ДополнительныеСведения КАК Д
        ГДЕ ВЫРАЗИТЬ(Д.Объект КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &М
        УПОРЯДОЧИТЬ ПО Портфель, Свойство""", {"М": mask})
    state["сведения"] = [{k: to_text(fo, v) for k, v in r.items()} for r in props]
    rsa = s4.query(fo, """ВЫБРАТЬ Р.Портфель.ВнешнийКод КАК Портфель, Р.РСА КАК РСА, Р.СЧА КАК СЧА
        ИЗ РегистрСведений.РегистрРСА_СЧА КАК Р ГДЕ Р.Портфель.ВнешнийКод ПОДОБНО &М УПОРЯДОЧИТЬ ПО Портфель""",
                   {"М": mask})
    state["рса_сча"] = [{"Портфель": r["Портфель"], "РСА": float(r["РСА"]), "СЧА": float(r["СЧА"])} for r in rsa]
    act = s4.query(fo, """ВЫБРАТЬ Р.Портфель.ВнешнийКод КАК Портфель, Р.Дата КАК Дата
        ИЗ РегистрСведений.ДатаАктуальностиФактическойПозиции КАК Р ГДЕ Р.Портфель.ВнешнийКод ПОДОБНО &М
        УПОРЯДОЧИТЬ ПО Портфель""", {"М": mask})
    state["дата_актуальности"] = [{k: to_text(fo, v) for k, v in r.items()} for r in act]
    hist = s4.query(fo, """ВЫБРАТЬ Р.Портфель.ВнешнийКод КАК Портфель, ПРЕДСТАВЛЕНИЕ(Р.СтатусПортфеля) КАК Статус,
            КОЛИЧЕСТВО(*) КАК К
        ИЗ РегистрСведений.ВТБ_СтатусыПортфелей КАК Р ГДЕ Р.Портфель.ВнешнийКод ПОДОБНО &М
        СГРУППИРОВАТЬ ПО Р.Портфель.ВнешнийКод, Р.СтатусПортфеля УПОРЯДОЧИТЬ ПО Портфель""", {"М": mask})
    state["история_статусов"] = [{"Портфель": r["Портфель"], "Статус": r["Статус"], "Записей": int(r["К"])}
                                 for r in hist]
    state["письма"] = [parse_mail(n) for n in mail_files()]
    save_state(state)
    log(f"  замеров без запуска {unmatched}, поручений {len(orders)}, писем {len(state['письма'])}")


def step_close(fo):
    stand = Stand(fo)
    for version in VERSIONS:
        stand.set_status(version, list(stand.refs[version]), "Выведены", f"{version}: все портфели T9748 закрыть")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    fo = s4.connect("wim_fo")
    if cmd == "prep":
        step_prep(fo)
    elif cmd == "scenarios":
        step_scenarios(fo)
    elif cmd == "extra":
        step_extra(fo)
    elif cmd == "bench":
        step_bench(fo, int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == "queries":
        step_queries(fo, int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    elif cmd == "collect":
        step_collect(fo)
    elif cmd == "close":
        step_close(fo)
    else:
        raise SystemExit(__doc__)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
