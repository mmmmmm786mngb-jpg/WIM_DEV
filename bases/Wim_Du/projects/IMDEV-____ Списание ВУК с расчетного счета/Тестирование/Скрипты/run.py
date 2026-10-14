# -*- coding: utf-8 -*-
"""Сценарии CR IMDEV-8856 на стенде: вызов ЗачисленияНаРСРозничногоДУ() выписки 6.09 через COM.

python run.py <сценарий>      - список сценариев: python run.py list
Перед сценарием прежние тестовые начисления и поручения стенда помечаются на удаление,
чтобы в выборку попадали только данные сценария. Протокол пишется в ../Результаты/<сценарий>.txt.
"""
import datetime as dt
import os
import sys
import time

import stand

DAY = dt.date(2026, 10, 13)
VUK_TEXT = "Оплата ВУК. Розничное ДУ. НДС не облагается."
OUT_TEXT = "Вывод денежных средств с брокерского счета 30601810100012100828, субсчет 13W6XW"
IN_TEXT = "Перевод средств компенсации по договорам ДУ. НДС не облагается"

LOG = []


def log(*parts):
    line = " ".join(str(p) for p in parts)
    LOG.append(line)
    print(line)


def retire_old(c):
    for text in [
        "ВЫБРАТЬ Н.Ссылка КАК Ссылка ИЗ Документ.НачислениеВознаграждения КАК Н "
        "ГДЕ Н.Комментарий ПОДОБНО \"T8856%\" И НЕ Н.ПометкаУдаления",
    ]:
        t = stand.query(c, text)
        for i in range(t.Количество()):
            obj = t.Получить(i).Ссылка.ПолучитьОбъект()
            obj.ПометкаУдаления = True
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
    t = stand.query(c, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Документ.Поручение КАК П ГДЕ П.ДоговорДУ.Наименование ПОДОБНО \"T8856%\"")
    for i in range(t.Количество()):
        obj = t.Получить(i).Ссылка.ПолучитьОбъект()
        obj.ОбменДанными.Загрузка = True
        obj.Удалить()


def contracts_by_index(c, indexes):
    by_code = {code: ref for ref, code in stand.test_contracts(c)}
    result = []
    for i in indexes:
        code = "МИ26089" if i == 1 else f"МИ9{i:04d}"
        result.append((i, code, by_code[code]))
    return result


def make_accruals(c, scenario, items, status="СформированоПлатежноеПоручение"):
    """items: список (индекс договора, сумма, дата). Возвращает список ссылок начислений."""
    uk = stand.contractor(c)
    rub = c.Справочники.Валюты.НайтиПоКоду("643")
    refs = []
    contracts = {i: (code, ref) for i, code, ref in contracts_by_index(c, [x[0] for x in items])}
    for i, amount, day in items:
        code, ref = contracts[i]
        doc = c.Документы.НачислениеВознаграждения.СоздатьДокумент()
        doc.Дата = stand.date_1c(c, dt.datetime(day.year, day.month, day.day, 18, 0, 0))
        doc.УстановитьНовыйНомер()
        doc.ДоговорДУ = ref
        doc.Розница = True
        doc.СуммаДокумента = amount
        doc.СуммаВознаграждения = amount
        doc.ВалютаДокумента = rub
        doc.ВалютаОплаты = rub
        doc.Курс = 1
        doc.Кратность = 1
        doc.Контрагент = uk
        doc.ВидКонтрагента = c.Перечисления.ВидыОбязательныхКонтрагентов.УправляющаяКомпания
        doc.СчетУчетаРасчетовСКонтрагентом = c.ПланыСчетов.Хозрасчетный.РасчетВознаграждениеУКЗаУправление
        doc.Комментарий = f"T8856 {scenario}"
        doc.ОбменДанными.Загрузка = True
        doc.Записать()
        set_status(c, doc.Ссылка, status)
        refs.append(doc.Ссылка)
    return refs


def set_status(c, ref, status_name):
    rec = c.РегистрыСведений.ИсторияСтатусовОбъектов.СоздатьМенеджерЗаписи()
    rec.Период = stand.date_1c(c, dt.datetime.now() - dt.timedelta(minutes=5))
    rec.Объект = ref
    rec.Статус = getattr(c.Перечисления.СтатусыОбъектов, status_name)
    rec.Записать()


def make_input_order(c, index, amount):
    _, code, ref = contracts_by_index(c, [index])[0]
    doc = c.Документы.Поручение.СоздатьДокумент()
    doc.Дата = stand.date_1c(c, dt.datetime(DAY.year, DAY.month, DAY.day, 10, 0, 0))
    doc.УстановитьНовыйНомер()
    doc.ДоговорДУ = ref
    doc.ВидОперации = c.Перечисления.ВидыОперацийПоручение.ВводВДУ
    doc.СуммаДС = amount
    doc.Контрагент = stand.contractor(c)
    doc.АналитическийСчетПриемник = stand.find_one(
        c, "ВЫБРАТЬ ПЕРВЫЕ 1 А.Ссылка КАК Ссылка ИЗ Справочник.АналитическиеСчета КАК А ГДЕ А.ДоговорДУ = &Д", Д=ref)
    doc.ОбменДанными.Загрузка = True
    doc.Записать()
    set_status(c, doc.Ссылка, "Новый")
    return doc.Ссылка


def statement_row(kind, number, amount, day=DAY):
    if kind == "vuk":
        return dict(Номер=number, Сумма=amount, ПлательщикСчет=stand.ACC_ERS, ПолучательСчет=stand.ACC_UK,
                    НазначениеПлатежа=VUK_TEXT, ДатаПоступления=day)
    if kind == "out":
        return dict(Номер=number, Сумма=amount, ПлательщикСчет=stand.ACC_BROKER, ПолучательСчет=stand.ACC_ERS,
                    НазначениеПлатежа=OUT_TEXT, ДатаПоступления=day)
    if kind == "in":
        return dict(Номер=number, Сумма=amount, ПлательщикСчет=stand.ACC_UK, ПолучательСчет=stand.ACC_ERS,
                    НазначениеПлатежа=IN_TEXT, ДатаПоступления=day)
    raise ValueError(kind)


def run_statement(c, statement_rows):
    c.ПолучитьСообщенияПользователю(True)
    obj = c.ВнешниеОбработки.Создать(stand.EPF_609, False)
    for r in statement_rows:
        row = obj.ПлатежныеДокументы.Добавить()
        for k, v in r.items():
            setattr(row, k, stand.date_1c(c, v) if isinstance(v, dt.date) else v)
    started = time.time()
    try:
        res = obj.ЗачисленияНаРСРозничногоДУ()
    except Exception as exc:
        log("ИСКЛЮЧЕНИЕ ЗачисленияНаРСРозничногоДУ:", str(exc).replace("\n", " | "))
        res = None
    log(f"время вызова {time.time() - started:.1f} с")
    if res is not None:
        log("ТекстСообщения:", res.ТекстСообщения.replace("\n", " | ") or "<пусто>")
        p = res.Параметры
        log("Параметры: ЕРС =", c.String(p.ЕРС), "/", c.String(p.ЕРС.НомерСчета) if not p.ЕРС.Пустая() else "",
            "| ДатаСписания =", c.String(p.ДатаСписания), "| ВхНомерСписание =", p.ВхНомерСписание,
            "| ВхНомер =", p.ВхНомер, "| ВхНомерВвод =", p.ВхНомерВвод)
    log("строк ПорученияПоДС_РДУ:", obj.ПорученияПоДС_РДУ.Количество(),
        "ПорученияПоДСВвод_РДУ:", obj.ПорученияПоДСВвод_РДУ.Количество(),
        "СписаниеСРасчетногоСчета_ВУК:", obj.СписаниеСРасчетногоСчета_ВУК.Количество())
    msgs = c.ПолучитьСообщенияПользователю(True)
    for i in range(msgs.Количество()):
        log("Сообщение:", msgs.Получить(i).Текст.replace("\n", " | ")[:600])
    return obj


def report_writeoffs(c, accruals):
    t = stand.query(c, """ВЫБРАТЬ
        Н.Ссылка КАК Начисление, Н.ДоговорДУ.Код КАК Код, Н.СуммаДокумента КАК СуммаНачисления,
        С.Ссылка КАК Списание, С.Дата КАК Дата, С.Проведен КАК Проведен, С.ДатаВходящегоДокумента КАК ДатаВх,
        С.НомерВходящегоДокумента КАК ВхНомер, С.НазначениеПлатежа КАК Назначение, С.СуммаДокумента КАК Сумма,
        С.СчетДоговораДУ.НомерСчета КАК СчетДоговора, С.АналитическийСчет.МестоХранения.НомерСчета КАК МестоАналитики,
        С.АналитическийСчет.Наименование КАК Аналитика, С.Ответственный КАК Ответственный,
        С.СтатьяДвиженияДенежныхСредств КАК СтатьяДДС, С.ВидОперации КАК ВидОперации
        ИЗ Документ.НачислениеВознаграждения КАК Н
        ЛЕВОЕ СОЕДИНЕНИЕ Документ.СписаниеСРасчетногоСчета КАК С ПО С.ПлановаяПозиция = Н.Ссылка
        ГДЕ Н.Ссылка В (&Н) УПОРЯДОЧИТЬ ПО Код""", Н=to_array(c, accruals))
    statuses = status_map(c, accruals)
    created = 0
    for r in stand.rows(c, t):
        s = {k: c.String(v) for k, v in r.items()}
        if s["Списание"]:
            created += 1
        log("  ", s["Код"], "| начисл", s["СуммаНачисления"], "| статус", statuses.get(c.String(r["Начисление"]), "?"),
            "|", s["Списание"] or "<нет списания>", "| пров", s["Проведен"], "| дата", s["Дата"], "| датаВх", s["ДатаВх"],
            "| вх№", s["ВхНомер"], "| сумма", s["Сумма"], "| счетДог", s["СчетДоговора"], "| место аналит",
            s["МестоАналитики"], "| отв", s["Ответственный"], "| ДДС", s["СтатьяДДС"], "| назн:", s["Назначение"])
    dup = stand.query(c, """ВЫБРАТЬ С.ПлановаяПозиция КАК П, КОЛИЧЕСТВО(*) КАК К ИЗ Документ.СписаниеСРасчетногоСчета КАК С
        ГДЕ С.ПлановаяПозиция В (&Н) СГРУППИРОВАТЬ ПО С.ПлановаяПозиция ИМЕЮЩИЕ КОЛИЧЕСТВО(*) > 1""", Н=to_array(c, accruals))
    log(f"итог: начислений {len(accruals)}, со списанием {created}, начислений с 2+ списаниями {dup.Количество()}")


def status_map(c, refs):
    t = stand.query(c, """ВЫБРАТЬ С.Объект КАК Объект, С.Статус КАК Статус
        ИЗ РегистрСведений.ИсторияСтатусовОбъектов.СрезПоследних(, Объект В (&Н)) КАК С""", Н=to_array(c, refs))
    return {c.String(r["Объект"]): c.String(r["Статус"]) for r in stand.rows(c, t)}


def to_array(c, refs):
    arr = c.NewObject("Массив")
    for r in refs:
        arr.Добавить(r)
    return arr


def report_receipts(c, contract_indexes):
    refs = [ref for _, _, ref in contracts_by_index(c, contract_indexes)]
    t = stand.query(c, """ВЫБРАТЬ П.Ссылка КАК Поступление, П.Проведен КАК Проведен, П.ДоговорДУ.Код КАК Код,
        П.СчетДоговораДУ.НомерСчета КАК СчетДоговора, П.СуммаДокумента КАК Сумма, П.НомерВходящегоДокумента КАК ВхНомер
        ИЗ Документ.ПоступлениеНаРасчетныйСчет КАК П ГДЕ П.ДоговорДУ В (&Д) И НЕ П.ПометкаУдаления""",
                    Д=to_array(c, refs))
    log("поступлений по договорам", contract_indexes, ":", t.Количество())
    for r in stand.rows(c, t):
        log("  ", {k: c.String(v) for k, v in r.items()})


def event_log(c, since):
    t = c.NewObject("ТаблицаЗначений")
    flt = c.NewObject("Структура")
    flt.Вставить("ДатаНачала", stand.date_1c(c, since))
    levels = c.NewObject("Массив")
    levels.Добавить(c.УровеньЖурналаРегистрации.Ошибка)
    flt.Вставить("Уровень", levels)
    c.ВыгрузитьЖурналРегистрации(t, flt)
    log("ошибок в журнале с", since.strftime("%H:%M:%S"), ":", t.Количество())
    for i in range(min(t.Количество(), 15)):
        r = t.Получить(i)
        log("  ЖР:", r.Событие, "|", str(r.Комментарий).replace("\n", " | ")[:500])


def measurements(c, since):
    try:
        t = stand.query(c, """ВЫБРАТЬ К.Наименование КАК Ключ, КОЛИЧЕСТВО(*) КАК Замеров
            ИЗ РегистрСведений.ЗамерыВремени КАК З ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.КлючевыеОперации КАК К
            ПО З.КлючеваяОперация = К.Ссылка ГДЕ З.ДатаЗаписи >= &Д СГРУППИРОВАТЬ ПО К.Наименование""",
                        Д=stand.date_1c(c, since))
        for r in stand.rows(c, t):
            log("  замер:", r["Ключ"], r["Замеров"])
    except Exception as exc:
        log("  замеры не прочитаны:", str(exc)[:200])


# ---------------------------------------------------------------- сценарии

def scenario_vuk_small(c):
    """3.2/2.1/2.2: день только с ВУК, 6 начислений (<=50, последовательно), сумма совпадает."""
    stand.cmd_acc928(c, "1")
    items = [(i, 1000 + i * 10.5, DAY) for i in (1, 4, 5, 6, 7, 8)]
    acc = make_accruals(c, "vuk_small", items)
    total = round(sum(x[1] for x in items), 2)
    run_statement(c, [statement_row("vuk", "5001", f"{total:.2f}")])
    report_writeoffs(c, acc)


def scenario_vuk_big(c):
    """3.2: день только с ВУК, 120 начислений (>50, фоновые порции по 50)."""
    stand.cmd_acc928(c, "1")
    items = [(i, 500 + i, DAY) for i in range(4, 124)]
    acc = make_accruals(c, "vuk_big", items)
    total = round(sum(x[1] for x in items), 2)
    since = dt.datetime.now() - dt.timedelta(seconds=5)
    run_statement(c, [statement_row("vuk", "5002", f"{total:.2f}")])
    report_writeoffs(c, acc)
    event_log(c, since)
    measurements(c, since)
    c.ХранилищеОбщихНастроек.Сохранить("T8856", "vuk_big", stand.date_1c(c, since))


def scenario_rerun(c):
    """Повтор той же выписки после vuk_big: второе списание не должно появиться."""
    t = stand.query(c, "ВЫБРАТЬ Н.Ссылка КАК Ссылка ИЗ Документ.НачислениеВознаграждения КАК Н "
                       "ГДЕ Н.Комментарий = \"T8856 vuk_big\" И НЕ Н.ПометкаУдаления")
    acc = [t.Получить(i).Ссылка for i in range(t.Количество())]
    total = round(sum(500 + i for i in range(4, 124)), 2)
    run_statement(c, [statement_row("vuk", "5002", f"{total:.2f}")])
    report_writeoffs(c, acc)


def scenario_mismatch(c):
    """3.5: сумма строки ВУК не равна итогу начислений - документы не создаются."""
    stand.cmd_acc928(c, "1")
    items = [(i, 700.0, DAY) for i in range(4, 9)]
    acc = make_accruals(c, "mismatch", items)
    run_statement(c, [statement_row("vuk", "5003", "3499.00")])
    report_writeoffs(c, acc)


def scenario_tail(c):
    """3.5: в статусе осталось начисление двухмесячной давности не из этой платежки."""
    stand.cmd_acc928(c, "1")
    items = [(i, 700.0, DAY) for i in range(4, 9)]
    acc = make_accruals(c, "tail", items)
    acc += make_accruals(c, "tail-old", [(9, 333.0, DAY - dt.timedelta(days=60))])
    run_statement(c, [statement_row("vuk", "5004", "3500.00")])
    report_writeoffs(c, acc)


def scenario_no_vuk(c):
    """3.3: обычный день без строки ВУК (только ввод) - какой текст получит пользователь."""
    stand.cmd_acc928(c, "1")
    make_input_order(c, 20, 1500.0)
    run_statement(c, [statement_row("in", "6001", "1500.00")])
    report_receipts(c, [20])


def scenario_in_and_vuk(c, present):
    """3.1: день с вводом и ВУК. present=1 - счет 928 есть в справочнике, 0 - нет."""
    stand.cmd_acc928(c, present)
    make_input_order(c, 21 if present == "1" else 22, 1500.0)
    items = [(i, 900.0, DAY) for i in range(4, 7)]
    acc = make_accruals(c, "in_vuk" + present, items)
    run_statement(c, [statement_row("in", "6002", "1500.00"), statement_row("vuk", "5005", "2700.00")])
    report_receipts(c, [21 if present == "1" else 22])
    report_writeoffs(c, acc)


def scenario_space(c):
    """2.3: сумма строки ВУК с пробелом-разделителем разрядов."""
    stand.cmd_acc928(c, "1")
    items = [(i, 617.0, DAY) for i in range(4, 6)]
    acc = make_accruals(c, "space", items)
    run_statement(c, [statement_row("vuk", "5006", "1 234.00")])
    report_writeoffs(c, acc)


def scenario_analytics(c):
    """2.1: договор 002 - аналитика только на индивидуальном счете, 003 - две аналитики (ЕРС и индивидуальный)."""
    stand.cmd_acc928(c, "1")
    items = [(2, 800.0, DAY), (3, 800.0, DAY), (4, 800.0, DAY)]
    acc = make_accruals(c, "analytics", items)
    obj = run_statement(c, [statement_row("vuk", "5007", "2400.00")])
    report_writeoffs(c, acc)
    acc2 = make_accruals(c, "analytics-b", [(2, 800.0, DAY), (4, 800.0, DAY)])
    retire(c, acc)
    log("-- повтор только с договорами 002 и 004 (без дубля аналитики), сумма 1600")
    run_statement(c, [statement_row("vuk", "5008", "1600.00")])
    report_writeoffs(c, acc2)


def summary_writeoffs(c, accruals):
    """Сводка по списаниям начислений без построчного вывода (для объема)."""
    t = stand.query(c, """ВЫБРАТЬ
        КОЛИЧЕСТВО(С.Ссылка) КАК Списаний,
        КОЛИЧЕСТВО(РАЗЛИЧНЫЕ С.ПлановаяПозиция) КАК НачисленийСоСписанием,
        КОЛИЧЕСТВО(РАЗЛИЧНЫЕ С.Номер) КАК РазныхНомеров,
        СУММА(ВЫБОР КОГДА С.Проведен ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК Проведено,
        СУММА(ВЫБОР КОГДА С.Дата = &Дата ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК ДатаВерна,
        СУММА(ВЫБОР КОГДА С.НазначениеПлатежа ПОДОБНО "Вознаграждение согласно п.3%" ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК НазначениеВерно,
        СУММА(ВЫБОР КОГДА С.СчетДоговораДУ.НомерСчета = &ЕРС ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК СчетЕРС,
        МИНИМУМ(С.Дата) КАК ДатаМин, МАКСИМУМ(С.Дата) КАК ДатаМакс
        ИЗ Документ.СписаниеСРасчетногоСчета КАК С ГДЕ С.ПлановаяПозиция В (&Н)""",
                    Н=to_array(c, accruals), ЕРС=stand.ACC_ERS,
                    Дата=stand.date_1c(c, dt.datetime(DAY.year, DAY.month, DAY.day, 9, 0, 0)))
    r = stand.rows(c, t)[0]
    statuses = status_map(c, accruals)
    done = sum(1 for v in statuses.values() if v == "Исполнено")
    log("сводка:", f"начислений {len(accruals)}", "|", " | ".join(f"{k}={c.String(v)}" for k, v in r.items()),
        f"| статус Исполнено {done}")


def measurement_rows(c, since_utc):
    t = stand.query(c, """ВЫБРАТЬ К.Наименование КАК Ключ, З.ВремяВыполнения КАК Время, З.ВесЗамера КАК Вес,
        З.ВыполненСОшибкой КАК Ошибка, З.НомерСеанса КАК Сеанс, З.ДатаНачалаЗамера КАК Начало, З.Комментарий КАК Комментарий
        ИЗ РегистрСведений.ЗамерыВремени КАК З ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.КлючевыеОперации КАК К
        ПО З.КлючеваяОперация = К.Ссылка ГДЕ З.ДатаЗаписи >= &Д УПОРЯДОЧИТЬ ПО З.ДатаНачалаЗамера""",
                    Д=stand.date_1c(c, since_utc))
    result = stand.rows(c, t)
    log("записей ЗамерыВремени:", len(result))
    for r in result:
        comment = str(r["Комментарий"])
        if '"ДопИнф"' in comment:
            comment = comment.split('"ДопИнф":', 1)[1]
        log("  замер:", r["Ключ"], "| время", c.String(r["Время"]), "| вес", c.String(r["Вес"]), "| ошибка",
            c.String(r["Ошибка"]), "| сеанс", c.String(r["Сеанс"]), "|", comment[:300])
    return result


def scenario_volume(c):
    """Объем: день только с ВУК, N начислений (T8856_N, по умолчанию 500), сводка, журнал, замеры."""
    n = int(os.environ.get("T8856_N", "500"))
    stand.cmd_acc928(c, "1")
    started = time.time()
    items = [(i, 300 + (i % 97) + 0.25, DAY) for i in range(4, 4 + n)]
    acc = make_accruals(c, "volume", items)
    log(f"начислений создано {len(acc)} за {time.time() - started:.0f} с")
    total = round(sum(x[1] for x in items), 2)
    since = dt.datetime.now() - dt.timedelta(seconds=2)
    since_utc = dt.datetime.utcnow() - dt.timedelta(seconds=2)
    run_statement(c, [statement_row("vuk", "5009", f"{total:.2f}")])
    summary_writeoffs(c, acc)
    event_log(c, since)
    measurement_rows(c, since_utc)


def scenario_measure_small(c):
    """Замеры: ввод и ВУК в один день (6 начислений) - какие ключи пишут поступления и списания."""
    stand.cmd_acc928(c, "1")
    make_input_order(c, 21, 1500.0)
    items = [(i, 900.0, DAY) for i in range(4, 10)]
    acc = make_accruals(c, "measure_small", items)
    since_utc = dt.datetime.utcnow() - dt.timedelta(seconds=2)
    run_statement(c, [statement_row("in", "6003", "1500.00"), statement_row("vuk", "5010", "5400.00")])
    summary_writeoffs(c, acc)
    measurement_rows(c, since_utc)


def scenario_manual(c):
    """Ручной режим 1.18/1.19 без выписки: настройки прошлого запуска, пустой шаблон назначения, пустой ЕРС."""
    stand.cmd_acc928(c, "1")
    proc = c.ВнешниеОбработки.Создать(stand.EPF_118, False)
    settings = c.NewObject("Структура")
    values = c.NewObject("Структура")
    values.Вставить("ВхНомерСписание", "СТАРЫЙ-777")
    values.Вставить("ДатаСписания", stand.date_1c(c, dt.date(2026, 9, 1)))
    values.Вставить("ЕРС", stand.bank_account(c, stand.ACC_ERS))
    values.Вставить("НазначениеПлатежаСписание", "")
    settings.Вставить("Значения", values)
    proc.УстановитьПользовательскиеНастройки(settings)
    log("после настроек прошлого запуска: ВхНомерСписание =", repr(proc.ВхНомерСписание),
        "| ДатаСписания =", c.String(proc.ДатаСписания))
    saved = proc.СтруктураНастрок()
    log("СтруктураНастрок сохраняет ВхНомерСписание:", saved.Свойство("ВхНомерСписание"),
        "| ДатаСписания:", saved.Свойство("ДатаСписания"))
    acc = make_accruals(c, "manual", [(i, 450.0, DAY) for i in (4, 5)])
    proc.ДатаСписания = stand.date_1c(c, DAY)
    proc.ВхНомерСписание = "7001"
    proc.НазначениеПлатежаСписание = ""
    c.ПолучитьСообщенияПользователю(True)
    try:
        proc.НачисленияВознаграждения(c.Перечисления.ВидыОперацийПоручение.Перевод)
        log("начитано строк:", proc.СписаниеСРасчетногоСчета.Количество())
        proc.СоздатьСписаниеДС(c.Перечисления.ВидыОперацийПоручение.Перевод)
    except Exception as exc:
        log("ИСКЛЮЧЕНИЕ:", str(exc).replace("\n", " | ")[:400])
    msgs = c.ПолучитьСообщенияПользователю(True)
    for i in range(msgs.Количество()):
        log("Сообщение:", msgs.Получить(i).Текст[:300])
    report_writeoffs(c, acc)
    log("-- пустой ЕРС")
    proc2 = c.ВнешниеОбработки.Создать(stand.EPF_118, False)
    proc2.ДатаСписания = stand.date_1c(c, DAY)
    try:
        proc2.НачисленияВознаграждения(c.Перечисления.ВидыОперацийПоручение.Перевод)
        log("начитано строк:", proc2.СписаниеСРасчетногоСчета.Количество())
    except Exception as exc:
        log("ИСКЛЮЧЕНИЕ:", str(exc).replace("\n", " | ")[:400])
    msgs = c.ПолучитьСообщенияПользователю(True)
    for i in range(msgs.Количество()):
        log("Сообщение:", msgs.Получить(i).Текст[:300])


def retire(c, refs):
    for r in refs:
        obj = r.ПолучитьОбъект()
        obj.ПометкаУдаления = True
        obj.ОбменДанными.Загрузка = True
        obj.Записать()


SCENARIOS = {
    "vuk_small": scenario_vuk_small,
    "vuk_big": scenario_vuk_big,
    "rerun": scenario_rerun,
    "mismatch": scenario_mismatch,
    "tail": scenario_tail,
    "no_vuk": scenario_no_vuk,
    "in_vuk1": lambda c: scenario_in_and_vuk(c, "1"),
    "in_vuk0": lambda c: scenario_in_and_vuk(c, "0"),
    "space": scenario_space,
    "analytics": scenario_analytics,
    "volume": scenario_volume,
    "measure_small": scenario_measure_small,
    "manual": scenario_manual,
}


def report_only(c, scenario, minutes):
    """Повторный отчет по начислениям сценария, журнал ошибок и замеры за последние N минут."""
    t = stand.query(c, "ВЫБРАТЬ Н.Ссылка КАК Ссылка ИЗ Документ.НачислениеВознаграждения КАК Н ГДЕ Н.Комментарий = &К",
                    К="T8856 " + scenario)
    report_writeoffs(c, [t.Получить(i).Ссылка for i in range(t.Количество())])
    since = dt.datetime.now() - dt.timedelta(minutes=minutes)
    event_log(c, since)
    measurements(c, since)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    name = sys.argv[1] if len(sys.argv) > 1 else "list"
    if name == "report":
        c = stand.connect()
        report_only(c, sys.argv[2], int(sys.argv[3]))
        with open(os.path.join(stand.RES, "report_" + sys.argv[2] + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(LOG) + "\n")
        return
    if name not in SCENARIOS:
        for k, f in SCENARIOS.items():
            print(k, "-", (f.__doc__ or "").strip())
        return
    c = stand.connect()
    log("=== сценарий", name, "вариант", stand.VARIANT, dt.datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    if name != "rerun":
        retire_old(c)
    SCENARIOS[name](c)
    os.makedirs(stand.RES, exist_ok=True)
    with open(os.path.join(stand.RES, name + ("" if stand.VARIANT == "orig" else "_" + stand.VARIANT) + ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)



