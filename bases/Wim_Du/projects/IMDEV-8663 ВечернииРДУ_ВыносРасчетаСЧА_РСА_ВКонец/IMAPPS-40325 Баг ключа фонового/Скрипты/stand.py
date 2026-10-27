# -*- coding: utf-8 -*-
"""
IMAPPS-40325: стенд вечерних регламентных операций на dev WIM_DU.

На dev-базе нет данных для регламента: нет учетных политик (список действующих договоров
пуст), нет установки регл. операций, в группе "2. Вечерние" нет видов операций, из
периодичностей только "Никогда". Стенд добавляет минимум, чтобы форма периода запускала
вечерние операции по двум портфелям, как в проде:

  prepare  - портфели "T40325 Портфель А/Б" по N договоров (только договоры с префиксом
             номера, иначе параллельные порции ловят "номер не уникален"), учетная политика,
             периодичность "T40325 Ежедневно" и ее кэш на дату теста, один реальный вид
             операции перенесен в группу "2. Вечерние", установка регл. операций по умолчанию;
  status   - что сейчас есть на стенде;
  cleanup  - откат всего по stand_state.json; планы за дату теста по договорам стенда
             помечаются на удаление.

Вход в базу по Windows-авторизации (без Usr/Pwd).
"""
import json
import os
import sys

import pythoncom
import win32com.client

sys.stdout.reconfigure(encoding="utf-8")

CONN = 'Srvr="localhost";Ref="WIM_DU";'
MARK = "T40325"
PORTFOLIO_A = "T40325 Портфель А"
PORTFOLIO_B = "T40325 Портфель Б"
PER_PORTFOLIO = int(os.environ.get("T40325_PER_PORTFOLIO", "200"))
TEST_DAY = (2027, 4, 16)
OPERATION = "ОпределениеРынковПоКотировкам_УУ"
EVENING_GROUP_CODE = '2. "Вечерние" операции'
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stand_state.json")


def connect():
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN)


def query(c, text, **params):
    q = c.NewObject("Запрос")
    q.Текст = text
    for k, v in params.items():
        q.УстановитьПараметр(k, v)
    return q.Выполнить().Выгрузить()


def uid(c, ref):
    return str(c.XMLString(ref))


def ref_by_uid(c, manager, s):
    return manager.ПолучитьСсылку(c.NewObject("УникальныйИдентификатор", s))


def make_date(c, y, m, d, hh=0, mm=0, ss=0):
    return query(c, "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d, %d, %d, %d) КАК Дата" % (y, m, d, hh, mm, ss)).Получить(0).Дата


def evening_group(c):
    t = query(c, "ВЫБРАТЬ ВидыОпер.Ссылка КАК Ссылка ИЗ Справочник.ВидыОперацийЗакрытияПериода КАК ВидыОпер "
                 "ГДЕ ВидыОпер.ЭтоГруппа И ВидыОпер.Код = &Код", Код=EVENING_GROUP_CODE)
    if t.Количество() == 0:
        raise RuntimeError("Нет группы " + EVENING_GROUP_CODE)
    return t.Получить(0).Ссылка


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def load_state():
    if not os.path.exists(STATE):
        return {"contracts": {}, "test_day": "%04d-%02d-%02d" % TEST_DAY}
    with open(STATE, encoding="utf-8") as f:
        return json.load(f)


def operation_ref(c):
    t = query(c, "ВЫБРАТЬ ВидыОпер.Ссылка КАК Ссылка ИЗ Справочник.ВидыОперацийЗакрытияПериода КАК ВидыОпер "
                 "ГДЕ ВидыОпер.ИмяПредопределенныхДанных = &Имя", Имя=OPERATION)
    if t.Количество() == 0:
        raise RuntimeError("Нет предопределенной операции " + OPERATION)
    return t.Получить(0).Ссылка


def prepare(c):
    """Шаги идемпотентны: состояние пишется после каждого, повторный запуск продолжает с места остановки.
    Объекты, созданные до появления пошагового состояния, находятся по маркеру T40325."""
    state = load_state()

    if "contracts_done" not in state:
        contracts = query(c, "ВЫБРАТЬ ПЕРВЫЕ %d Договоры.Ссылка КАК Ссылка, Договоры.Портфель КАК Портфель "
                             "ИЗ Справочник.ДоговорДУ КАК Договоры ГДЕ НЕ Договоры.ПометкаУдаления "
                             "И Договоры.Префикс <> \"\" УПОРЯДОЧИТЬ ПО Договоры.Код" % (2 * PER_PORTFOLIO))
        if contracts.Количество() < 2 * PER_PORTFOLIO:
            raise RuntimeError("Договоров с префиксом меньше %d" % (2 * PER_PORTFOLIO))
        for i in range(contracts.Количество()):
            row = contracts.Получить(i)
            key = uid(c, row.Ссылка)
            original = str(row.Портфель)
            if original.startswith(MARK):
                original = ""
            state["contracts"].setdefault(key, original)
            portfolio = PORTFOLIO_A if i < PER_PORTFOLIO else PORTFOLIO_B
            if str(row.Портфель) != portfolio:
                obj = row.Ссылка.ПолучитьОбъект()
                obj.Портфель = portfolio
                obj.ОбменДанными.Загрузка = True
                obj.Записать()
        state["contracts_done"] = True
        save_state(state)
    print("Портфели: А и Б по %d договоров" % PER_PORTFOLIO)

    policy_date = make_date(c, 2026, 1, 1)
    if "policy" not in state:
        t = query(c, "ВЫБРАТЬ Политики.Ссылка КАК Ссылка ИЗ Документ.УчетнаяПолитика КАК Политики "
                     "ГДЕ Политики.Комментарий ПОДОБНО \"T40325%\"")
        if t.Количество() > 0:
            policy_ref = t.Получить(0).Ссылка
        else:
            policy = c.Документы.УчетнаяПолитика.СоздатьДокумент()
            policy.Дата = policy_date
            policy.УстановитьНовыйНомер()
            policy.Комментарий = MARK + " стенд IMAPPS-40325"
            policy.ОбменДанными.Загрузка = True
            policy.Записать()
            policy_ref = policy.Ссылка
        records = c.РегистрыСведений.УчетныеПолитики.СоздатьНаборЗаписей()
        records.Отбор.Регистратор.Установить(policy_ref)
        for key in state["contracts"]:
            rec = records.Добавить()
            rec.Период = policy_date
            rec.ДоговорДУ = ref_by_uid(c, c.Справочники.ДоговорДУ, key)
            rec.УчетнаяПолитика = policy_ref
        records.Записать(True)
        state["policy"] = uid(c, policy_ref)
        save_state(state)
    print("Учетная политика:", len(state["contracts"]), "записей")

    if "periodicity" not in state:
        t = query(c, "ВЫБРАТЬ Периодичности.Ссылка КАК Ссылка ИЗ Справочник.НастройкиПериодичности КАК Периодичности "
                     "ГДЕ Периодичности.Наименование = &Имя", Имя=MARK + " Ежедневно")
        if t.Количество() > 0:
            periodicity_ref = t.Получить(0).Ссылка
        else:
            periodicity = c.Справочники.НастройкиПериодичности.СоздатьЭлемент()
            periodicity.Наименование = MARK + " Ежедневно"
            periodicity.ОбменДанными.Загрузка = True
            periodicity.Записать()
            periodicity_ref = periodicity.Ссылка
        cache = c.РегистрыСведений.КэшВидовПериодичности.СоздатьМенеджерЗаписи()
        cache.ВидПериодичности = periodicity_ref
        cache.Год = TEST_DAY[0]
        cache.ДатаПериодичности = make_date(c, *TEST_DAY)
        cache.Записать(True)
        state["periodicity"] = uid(c, periodicity_ref)
        save_state(state)
    print("Периодичность и кэш на", state["test_day"])

    operation = operation_ref(c)
    if "operation_parent" not in state:
        op_obj = operation.ПолучитьОбъект()
        state["operation_parent"] = uid(c, op_obj.Родитель)
        save_state(state)
        op_obj.Родитель = evening_group(c)
        op_obj.ОбменДанными.Загрузка = True
        op_obj.Записать()
    print("Операция", OPERATION, "в группе", EVENING_GROUP_CODE)

    if "settings" not in state:
        settings = c.Документы.УстановкаРеглОперацийДУ.СоздатьДокумент()
        settings.Дата = policy_date
        settings.УстановитьНовыйНомер()
        row = settings.Настройки.Добавить()
        row.ВидОперации = operation
        row.Периодичность = ref_by_uid(c, c.Справочники.НастройкиПериодичности, state["periodicity"])
        settings.Записать(c.РежимЗаписиДокумента.Проведение)
        state["settings"] = uid(c, settings.Ссылка)
        save_state(state)
    print("Установка регл. операций по умолчанию проведена")

    # ПланРеглОпераций берет настройки с заполненным договором: запись с пустым договором ни к одному
    # договору не применяется. Поэтому под документом-регистратором - запись по каждому договору стенда.
    if "settings_records" not in state:
        settings_ref = ref_by_uid(c, c.Документы.УстановкаРеглОперацийДУ, state["settings"])
        periodicity_ref = ref_by_uid(c, c.Справочники.НастройкиПериодичности, state["periodicity"])
        records = c.РегистрыСведений.НастройкиЗакрытияПериода.СоздатьНаборЗаписей()
        records.Отбор.Регистратор.Установить(settings_ref)
        for key in state["contracts"]:
            rec = records.Добавить()
            rec.Период = policy_date
            rec.ДоговорДУ = ref_by_uid(c, c.Справочники.ДоговорДУ, key)
            rec.ВидОперации = operation
            rec.Периодичность = periodicity_ref
        records.Записать(True)
        state["settings_records"] = len(state["contracts"])
        save_state(state)
    print("Настройки закрытия периода по договорам:", state["settings_records"])
    print("Состояние:", STATE)


def status(c):
    print("Версия", c.Метаданные.Версия)
    for e in c.РасширенияКонфигурации.Получить():
        print("Расширение", e.Имя, e.Версия, "активно" if e.Активно else "неактивно")
    t = query(c, "ВЫБРАТЬ Договоры.Портфель КАК Портфель, КОЛИЧЕСТВО(*) КАК Количество ИЗ Справочник.ДоговорДУ КАК Договоры "
                 "ГДЕ Договоры.Портфель ПОДОБНО \"T40325%\" СГРУППИРОВАТЬ ПО Договоры.Портфель")
    for i in range(t.Количество()):
        print("Портфель", t.Получить(i).Портфель, t.Получить(i).Количество)
    t = query(c, "ВЫБРАТЬ ПРЕДСТАВЛЕНИЕ(Планы.ГруппаОперацийПользователя) КАК Группа, Планы.Проведен КАК Проведен, "
                 "Планы.ПометкаУдаления КАК Помечен, КОЛИЧЕСТВО(*) КАК Количество "
                 "ИЗ Документ.ПланРегламентныхОперацийДУ КАК Планы "
                 "ГДЕ Планы.Дата МЕЖДУ &Начало И &Конец И Планы.ДоговорДУ.Портфель ПОДОБНО \"T40325%\" "
                 "СГРУППИРОВАТЬ ПО ПРЕДСТАВЛЕНИЕ(Планы.ГруппаОперацийПользователя), Планы.Проведен, Планы.ПометкаУдаления",
          Начало=make_date(c, *TEST_DAY), Конец=make_date(c, *TEST_DAY, 23, 59, 59))
    for i in range(t.Количество()):
        r = t.Получить(i)
        print("Планы", r.Группа, "проведен" if r.Проведен else "не проведен", "помечен" if r.Помечен else "", r.Количество)


def cleanup(c):
    if not os.path.exists(STATE):
        raise RuntimeError("Нет " + STATE)
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    day = make_date(c, *TEST_DAY)
    plans = query(c, "ВЫБРАТЬ Планы.Ссылка КАК Ссылка ИЗ Документ.ПланРегламентныхОперацийДУ КАК Планы "
                     "ГДЕ Планы.Дата МЕЖДУ &Начало И &Конец И Планы.ДоговорДУ.Портфель ПОДОБНО \"T40325%\" "
                     "И НЕ Планы.ПометкаУдаления", Начало=day, Конец=make_date(c, *TEST_DAY, 23, 59, 59))
    for i in range(plans.Количество()):
        plans.Получить(i).Ссылка.ПолучитьОбъект().УстановитьПометкуУдаления(True)
    print("Планов помечено на удаление:", plans.Количество())

    settings = ref_by_uid(c, c.Документы.УстановкаРеглОперацийДУ, state["settings"]).ПолучитьОбъект()
    settings.Записать(c.РежимЗаписиДокумента.ОтменаПроведения)
    settings.Удалить()
    operation = operation_ref(c).ПолучитьОбъект()
    operation.Родитель = ref_by_uid(c, c.Справочники.ВидыОперацийЗакрытияПериода, state["operation_parent"])
    operation.ОбменДанными.Загрузка = True
    operation.Записать()
    periodicity = ref_by_uid(c, c.Справочники.НастройкиПериодичности, state["periodicity"])
    cache = c.РегистрыСведений.КэшВидовПериодичности.СоздатьНаборЗаписей()
    cache.Отбор.ВидПериодичности.Установить(periodicity)
    cache.Записать(True)
    per_obj = periodicity.ПолучитьОбъект()
    per_obj.ОбменДанными.Загрузка = True
    per_obj.Удалить()
    policy = ref_by_uid(c, c.Документы.УчетнаяПолитика, state["policy"])
    records = c.РегистрыСведений.УчетныеПолитики.СоздатьНаборЗаписей()
    records.Отбор.Регистратор.Установить(policy)
    records.Записать(True)
    pol_obj = policy.ПолучитьОбъект()
    pol_obj.ОбменДанными.Загрузка = True
    pol_obj.Удалить()
    for s, portfolio in state["contracts"].items():
        obj = ref_by_uid(c, c.Справочники.ДоговорДУ, s).ПолучитьОбъект()
        obj.Портфель = portfolio
        obj.ОбменДанными.Загрузка = True
        obj.Записать()
    os.rename(STATE, STATE + ".done")
    print("Стенд откачен")


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    c = connect()
    {"prepare": prepare, "status": status, "cleanup": cleanup}[action](c)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
