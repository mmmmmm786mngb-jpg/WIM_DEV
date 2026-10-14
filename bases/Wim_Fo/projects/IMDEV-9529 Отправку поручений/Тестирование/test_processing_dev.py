"""Проверка обработки FO_SendFixStub_ТестОтправки (FO_SendFixStub 1.0.0.3) в разработческой базе ФО.

    python test_processing_dev.py            - полный прогон с восстановлением данных
    python test_processing_dev.py --keep     - подготовить данные и оставить их (для UI-теста), снимок в keep_state.json
    python test_processing_dev.py --restore  - восстановить данные по keep_state.json

Временные данные: адаптер вида FIX + запись ИспользуемыеАдаптеры; настройки WebSocket-прокси на локальный HTTP-слушатель
127.0.0.1:18529; у тестовых поручений - привязка к адаптеру (РасширенияПоручений) и тикер на бирже поручения у их
активов (Справочник.Активы, ТЧ БиржиЛистинга). Регистры тестовых поручений сохраняются до теста и восстанавливаются
после: СтатусыПоручений, БиржевыеЗаявки, РасширенияПоручений, СтатусыПорученийБлокировки, СобытияПоручений,
СобытияПорученийТорговые, ПорученияДляОбменаС_CRM, ХешОбъектов.

Методы обработки, которые меняют данные и отправляют, вызываются фоновыми заданиями на сервере
(ОбщегоНазначения.ВыполнитьМетодКонфигурации): модуль менеджера АдаптерFIX во внешнем соединении не инициализируется.
"""
import glob
import json
import os
import re
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding="utf-8")
STAND = glob.glob(r"C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО")[0]
sys.path.insert(0, STAND)
from stand_common import connect  # noqa: E402

PROC = "Обработки.FO_SendFixStub_ТестОтправки"
EVENT = "IMDEV-9529.ЗаглушкаFIX"
PROXY_PORT = 18529
SETTINGS = ("ВебСокетПрокси", "НастройкиВебСокетПрокси", "7f5e9f00-f3dc-4178-b225-90bdf5bd8e44")
TEST_DAY = (2026, 10, 7)
TICKER = "TEST9529"
ORDER_REGISTERS = ["СтатусыПоручений", "БиржевыеЗаявки", "РасширенияПоручений", "СтатусыПорученийБлокировки",
                   "СобытияПоручений", "СобытияПорученийТорговые", "ПорученияДляОбменаС_CRM"]
STATE_FILE = os.path.join(os.path.dirname(__file__), "keep_state.json")
HELPER_EPF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ДанныеТеста9529.epf")

results = []
requests_log = []


class Listener(BaseHTTPRequestHandler):
    def _answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        requests_log.append(f"{self.command} {self.path[:60]}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    do_GET = do_POST = do_PUT = _answer

    def log_message(self, *args):
        pass


def same_ref(fo, left, right):
    """Сравнение ссылок 1С одного типа: COM-объекты Python сравнивает по идентичности прокси, поэтому сравнивается УИД."""
    return fo.String(left.УникальныйИдентификатор()) == fo.String(right.УникальныйИдентификатор())


def check(name, ok, details=""):
    results.append((name, ok))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" - {details}" if details else ""), flush=True)


def date_1c(fo, y, m, d, hh=0, mi=0, ss=0):
    date_type = fo.NewObject("ОписаниеТипов", "Дата").Типы().Получить(0)
    return fo.XMLЗначение(date_type, f"{y:04d}-{m:02d}-{d:02d}T{hh:02d}:{mi:02d}:{ss:02d}")


def ref_by_uuid(fo, manager, uid):
    if uid == "00000000-0000-0000-0000-000000000000":
        return manager.ПустаяСсылка()
    return manager.ПолучитьСсылку(fo.NewObject("УникальныйИдентификатор", uid))


def array(fo, values):
    result = fo.NewObject("Массив")
    for value in values:
        result.Добавить(value)
    return result


def run_job(fo, method, args, timeout=180):
    params = array(fo, [method, array(fo, args)])
    job = fo.ФоновыеЗадания.Выполнить("ОбщегоНазначения.ВыполнитьМетодКонфигурации", params, None, "IMDEV-9529 тест обработки")
    uid = job.УникальныйИдентификатор
    for _ in range(timeout * 2):
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно:
            error = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке) if job.ИнформацияОбОшибке else ""
            return fo.String(job.Состояние), error
        time.sleep(0.5)
    return "Таймаут", ""


def wait_bsp_jobs(fo, since, timeout=120):
    """Ждет завершения фоновых заданий отправки, запущенных после since (длительная операция БСП и задание адаптера)."""
    for _ in range(timeout * 2):
        jobs = fo.ФоновыеЗадания.ПолучитьФоновыеЗадания(fo.NewObject("Структура", "Состояние", fo.СостояниеФоновогоЗадания.Активно))
        active = [jobs.Получить(i) for i in range(jobs.Количество()) if jobs.Получить(i).Начало >= since]
        if not active:
            return True
        time.sleep(0.5)
    return False


def stub_comments(fo, since):
    table = fo.NewObject("ТаблицаЗначений")
    log_filter = fo.NewObject("Структура")
    log_filter.Вставить("Событие", EVENT)
    log_filter.Вставить("ДатаНачала", since)
    fo.ВыгрузитьЖурналРегистрации(table, log_filter)
    return [table.Get(i).Комментарий for i in range(table.Count())]


def sent_orders_from_log(comments):
    counts = [int(m.group(1)) for c in comments for m in [re.search(r"заявок 35=D: (\d+)", c)] if m and c.startswith("Команда /send")]
    return counts


def key_op_weights(fo, since_ms):
    query = fo.NewObject("Запрос",
                         "ВЫБРАТЬ З.ВесЗамера КАК ВесЗамера, З.ВремяВыполнения КАК ВремяВыполнения "
                         "ИЗ РегистрСведений.ЗамерыВремени КАК З "
                         "ГДЕ З.КлючеваяОперация = ЗНАЧЕНИЕ(Справочник.КлючевыеОперации.Отправка) "
                         "И З.ДатаНачалаЗамера >= &Начало")
    query.УстановитьПараметр("Начало", since_ms)
    table = query.Выполнить().Выгрузить()
    return [(int(table.Get(i).ВесЗамера), float(table.Get(i).ВремяВыполнения)) for i in range(table.Count())]


def status_info(fo, order):
    records = fo.РегистрыСведений.СтатусыПоручений.СоздатьНаборЗаписей()
    records.Отбор.Поручение.Установить(order)
    records.Прочитать()
    if records.Количество() == 0:
        return "", ""
    return fo.String(records.Получить(0).Статус), records.Получить(0).СтатусСтрокой


def exchange_number(fo, order):
    records = fo.РегистрыСведений.БиржевыеЗаявки.СоздатьНаборЗаписей()
    records.Отбор.Поручение.Установить(order)
    records.Прочитать()
    return records.Получить(0).НомерБиржевой if records.Количество() else ""


def locks_count(fo, order):
    records = fo.РегистрыСведений.СтатусыПорученийБлокировки.СоздатьНаборЗаписей()
    records.Отбор.Поручение.Установить(order)
    records.Прочитать()
    return records.Количество()


# ---------------------------------------------------------------- подготовка и восстановление данных

def pick_orders(fo, count=5):
    query = fo.NewObject("Запрос",
                         "ВЫБРАТЬ ПЕРВЫЕ 5 П.Ссылка КАК Ссылка, П.Актив КАК Актив, П.Биржа КАК Биржа "
                         "ИЗ Документ.Поручение КАК П "
                         "ГДЕ П.Проведен И НЕ П.Внебиржевая И П.Дата МЕЖДУ &Н И &К И П.Биржа <> ЗНАЧЕНИЕ(Справочник.Биржи.ПустаяСсылка) "
                         "УПОРЯДОЧИТЬ ПО П.Дата, П.Ссылка")
    query.УстановитьПараметр("Н", date_1c(fo, *TEST_DAY))
    query.УстановитьПараметр("К", date_1c(fo, *TEST_DAY, 23, 59, 59))
    table = query.Выполнить().Выгрузить()
    return [(table.Get(i).Ссылка, table.Get(i).Актив, table.Get(i).Биржа) for i in range(table.Count())][:count]


def setup(fo):
    state = {"orders": [], "assets": [], "registers": {}}
    try:
        return setup_steps(fo, state)
    except Exception:
        print("Сбой подготовки данных, восстановление по сохраненному снимку", flush=True)
        restore(fo, state)
        raise


def setup_steps(fo, state):
    orders = pick_orders(fo)
    if len(orders) < 5:
        raise SystemExit(f"Нужно 5 биржевых поручений за {TEST_DAY}, найдено {len(orders)}")

    adapter_obj = fo.Справочники.Адаптеры.СоздатьЭлемент()
    adapter_obj.Наименование = "IMDEV-9529 тест обработки"
    adapter_obj.Вид = fo.Перечисления.ВидыАдаптеров.FIX
    adapter_obj.Использовать = True
    adapter_obj.Отправитель = "TEST_SENDER"
    adapter_obj.Получатель = "TEST_TARGET"
    # Режимы торгов адаптера: торговая площадка берется из режима торгов поручения, привязка режима к площадке
    # (регистр РежимыТорговПлощадок) в разработческой базе не нужна.
    adapter_obj.ИспРежимыТоргов = True
    adapter_obj.ОбменДанными.Загрузка = True
    adapter_obj.Записать()
    adapter = adapter_obj.Ссылка
    used_id = str(uuid.uuid4())
    record = fo.РегистрыСведений.ИспользуемыеАдаптеры.СоздатьМенеджерЗаписи()
    record.Адаптер = adapter
    record.Идентификатор = fo.NewObject("УникальныйИдентификатор", used_id)
    record.Используется = True
    record.Записать()
    state["adapter"] = str(fo.String(adapter.УникальныйИдентификатор()))
    state["used_id"] = used_id
    save_state(state)

    settings = fo.NewObject("Структура")
    settings.Вставить("АдресHTTPСервиса", f"http://127.0.0.1:{PROXY_PORT}")
    fo.ОбщегоНазначения.ХранилищеОбщихНастроекСохранить(SETTINGS[0], SETTINGS[1], settings, None, SETTINGS[2])

    for order, asset, exchange in orders:
        order_id = str(fo.String(order.УникальныйИдентификатор()))
        state["orders"].append(order_id)
        for register in ORDER_REGISTERS + ["ХешОбъектов"]:
            records = getattr(fo.РегистрыСведений, register).СоздатьНаборЗаписей()
            if register == "ХешОбъектов":
                records.Отбор.Объект.Установить(order)
            else:
                records.Отбор.Поручение.Установить(order)
            records.Прочитать()
            state["registers"].setdefault(register, {})[order_id] = fo.ЗначениеВСтрокуВнутр(records.Выгрузить())
        asset_obj = asset.ПолучитьОбъект()
        if not any(same_ref(fo, asset_obj.БиржиЛистинга.Получить(i).Биржа, exchange) and asset_obj.БиржиЛистинга.Получить(i).Тикер
                   for i in range(asset_obj.БиржиЛистинга.Количество())):
            row = asset_obj.БиржиЛистинга.Добавить()
            row.Биржа = exchange
            row.Тикер = TICKER
            asset_obj.ОбменДанными.Загрузка = True
            asset_obj.Записать()
            state["assets"].append([str(fo.String(asset.УникальныйИдентификатор())), str(fo.String(exchange.УникальныйИдентификатор()))])
        save_state(state)

    # У поручений разработческой базы не заполнены торговый счет и режим торгов, без них типовая проверка перед
    # отправкой отклоняет поручение. Заполняются любыми существующими элементами, исходные значения сохраняются.
    account_obj = fo.Справочники.ТорговыеСчета.СоздатьЭлемент()
    account_obj.Код = "TEST9529"
    account_obj.ОбменДанными.Загрузка = True
    account_obj.Записать()
    account = account_obj.Ссылка
    state["account"] = str(fo.String(account.УникальныйИдентификатор()))
    save_state(state)
    mode = first_ref(fo, "РежимыТоргов")
    state["documents"] = {}
    query = fo.NewObject("Запрос", "ВЫБРАТЬ П.Ссылка КАК Ссылка, П.ТорговыйСчет КАК ТорговыйСчет, П.РежимТоргов КАК РежимТоргов "
                                   "ИЗ Документ.Поручение КАК П ГДЕ П.Ссылка В (&Поручения)")
    query.УстановитьПараметр("Поручения", array(fo, [ref_by_uuid(fo, fo.Документы.Поручение, o) for o in state["orders"][:4]]))
    table = query.Выполнить().Выгрузить()
    for i in range(table.Count()):
        row = table.Get(i)
        state["documents"][str(fo.String(row.Ссылка.УникальныйИдентификатор()))] = [
            str(fo.String(row.ТорговыйСчет.УникальныйИдентификатор())), str(fo.String(row.РежимТоргов.УникальныйИдентификатор()))]
    save_state(state)
    set_order_fields(fo, [(ref_by_uuid(fo, fo.Документы.Поручение, o), account, mode) for o in state["documents"]])

    # Четыре поручения привязываются к тестовому адаптеру FIX, пятое остается без адаптера FIX (проверка отбора).
    for order_id in state["orders"][:4]:
        order = ref_by_uuid(fo, fo.Документы.Поручение, order_id)
        ext = fo.РегистрыСведений.РасширенияПоручений.СоздатьМенеджерЗаписи()
        ext.Поручение = order
        ext.Прочитать()
        ext.Поручение = order
        ext.Адаптер = adapter
        ext.АдаптерИдентификаторИсп = fo.NewObject("УникальныйИдентификатор", used_id)
        ext.Записать()
    # У первого поручения - биржевой номер, чтобы проверить его очистку подготовкой.
    first = ref_by_uuid(fo, fo.Документы.Поручение, state["orders"][0])
    numbers = fo.РегистрыСведений.БиржевыеЗаявки.СоздатьНаборЗаписей()
    numbers.Отбор.Поручение.Установить(first)
    numbers.Прочитать()
    if numbers.Количество() == 0:
        row = numbers.Добавить()
        row.Поручение = first
        row.Адаптер = adapter
    numbers.Получить(0).НомерБиржевой = "TEST-EXCH-1"
    numbers.Записать()

    save_state(state)
    return state


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def set_order_fields(fo, rows):
    """Записывает поручениям торговый счет и режим торгов внешней обработкой ДанныеТеста9529.epf в фоновом задании."""
    values = fo.NewObject("Массив")
    for order, account, mode in rows:
        item = fo.NewObject("Структура")
        item.Вставить("Поручение", order)
        item.Вставить("ТорговыйСчет", account)
        item.Вставить("РежимТоргов", mode)
        values.Добавить(item)
    params = fo.NewObject("Структура")
    params.Вставить("ЭтоВнешняяОбработка", True)
    params.Вставить("ИмяОбработки", HELPER_EPF)
    params.Вставить("ИмяМетода", "ЗаполнитьРеквизитыПоручений")
    params.Вставить("ПараметрыВыполнения", values)
    job = fo.ФоновыеЗадания.Выполнить("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки",
                                      array(fo, [params, ""]), None, "IMDEV-9529 тестовые данные")
    uid = job.УникальныйИдентификатор
    for _ in range(240):
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно:
            break
        time.sleep(0.5)
    if job.ИнформацияОбОшибке is not None:
        raise RuntimeError("Тестовые данные не записаны: " + fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке))


def first_ref(fo, catalog):
    query = fo.NewObject("Запрос", f"ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Справочник.{catalog} КАК Т "
                                   "ГДЕ НЕ Т.ПометкаУдаления УПОРЯДОЧИТЬ ПО Т.Ссылка")
    return query.Выполнить().Выгрузить().Get(0).Ссылка


def restore(fo, state):
    if state.get("documents"):
        set_order_fields(fo, [(ref_by_uuid(fo, fo.Документы.Поручение, order_id),
                               ref_by_uuid(fo, fo.Справочники.ТорговыеСчета, account_id),
                               ref_by_uuid(fo, fo.Справочники.РежимыТоргов, mode_id))
                              for order_id, (account_id, mode_id) in state["documents"].items()])
    for register, by_order in state["registers"].items():
        for order_id, saved in by_order.items():
            order = ref_by_uuid(fo, fo.Документы.Поручение, order_id)
            records = getattr(fo.РегистрыСведений, register).СоздатьНаборЗаписей()
            if register == "ХешОбъектов":
                records.Отбор.Объект.Установить(order)
            else:
                records.Отбор.Поручение.Установить(order)
            records.Загрузить(fo.ЗначениеИзСтрокиВнутр(saved))
            records.Записать()
    for asset_id, exchange_id in state["assets"]:
        asset_obj = ref_by_uuid(fo, fo.Справочники.Активы, asset_id).ПолучитьОбъект()
        exchange = ref_by_uuid(fo, fo.Справочники.Биржи, exchange_id)
        for i in reversed(range(asset_obj.БиржиЛистинга.Количество())):
            row = asset_obj.БиржиЛистинга.Получить(i)
            if row.Тикер == TICKER and same_ref(fo, row.Биржа, exchange):
                asset_obj.БиржиЛистинга.Удалить(i)
        asset_obj.ОбменДанными.Загрузка = True
        asset_obj.Записать()
    if state.get("account"):
        account_obj = ref_by_uuid(fo, fo.Справочники.ТорговыеСчета, state["account"]).ПолучитьОбъект()
        if account_obj is not None:
            account_obj.ОбменДанными.Загрузка = True
            account_obj.Удалить()
    fo.ОбщегоНазначения.ХранилищеОбщихНастроекУдалить(SETTINGS[0], SETTINGS[1], SETTINGS[2])
    if not state.get("adapter"):
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print("Данные разработческой базы восстановлены", flush=True)
        return
    adapter = ref_by_uuid(fo, fo.Справочники.Адаптеры, state["adapter"])
    for register in ("СообщенияАдаптеров", "СообщенияАдаптеровСчетчики", "СостоянияАдаптеров"):
        records = getattr(fo.РегистрыСведений, register).СоздатьНаборЗаписей()
        records.Отбор.Адаптер.Установить(adapter)
        records.Записать()
    used = fo.РегистрыСведений.ИспользуемыеАдаптеры.СоздатьНаборЗаписей()
    used.Прочитать()
    for i in reversed(range(used.Количество())):
        if same_ref(fo, used.Получить(i).Адаптер, adapter):
            used.Удалить(i)
    used.Записать()
    adapter_obj = adapter.ПолучитьОбъект()
    if adapter_obj is not None:
        adapter_obj.ОбменДанными.Загрузка = True
        adapter_obj.Удалить()
    fo.ОбщегоНазначения.ХранилищеОбщихНастроекУдалить(SETTINGS[0], SETTINGS[1], SETTINGS[2])
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("Данные разработческой базы восстановлены", flush=True)


# ---------------------------------------------------------------- проверки

def run_checks(fo, state):
    orders = [ref_by_uuid(fo, fo.Документы.Поручение, o) for o in state["orders"]]
    fix_orders = orders[:4]
    ready_names = {fo.String(fo.Перечисления.СтатусыПоручений.Проверено),
                   fo.String(fo.Перечисления.СтатусыПоручений.ОжидаетОтправки)}
    sent_name = fo.String(fo.Перечисления.СтатусыПоручений.ОтправленоОжидаетсяПодтверждение)
    period = fo.NewObject("СтандартныйПериод", date_1c(fo, *TEST_DAY), date_1c(fo, *TEST_DAY, 23, 59, 59))

    found = fo.Обработки.FO_SendFixStub_ТестОтправки.НайтиПоручения(period, 0)
    found_set = {str(fo.String(found.Get(i).Поручение.УникальныйИдентификатор())) for i in range(found.Count())}
    found2 = fo.Обработки.FO_SendFixStub_ТестОтправки.НайтиПоручения(period, 2)
    other = fo.NewObject("СтандартныйПериод", date_1c(fo, 2026, 10, 6), date_1c(fo, 2026, 10, 6, 23, 59, 59))
    found_other = fo.Обработки.FO_SendFixStub_ТестОтправки.НайтиПоручения(other, 0)
    check("2. Найти: только поручения периода с адаптером FIX, ограничение N",
          found_set == set(state["orders"][:4]) and found2.Count() == 2 and found_other.Count() == 0,
          f"найдено {found.Count()} (ожидалось 4, пятое без адаптера FIX не попало: {state['orders'][4] not in found_set}), "
          f"N=2 -> {found2.Count()}, 06.10 -> {found_other.Count()}")

    before_other = [status_info(fo, o)[1] for o in fix_orders[2:]]
    state_job, error = run_job(fo, f"{PROC}.ПодготовитьПоручения", [array(fo, fix_orders[:2])])
    after = [status_info(fo, o) for o in fix_orders[:2]]
    after_other = [status_info(fo, o)[1] for o in fix_orders[2:]]
    ready = all(s[0] in ready_names for s in after)
    check("3. Подготовить: выделенные - Проверено/Ожидает отправки, номер очищен, блокировок нет; остальные без изменений",
          state_job == "Задание выполнено" and ready and exchange_number(fo, fix_orders[0]) == ""
          and all(locks_count(fo, o) == 0 for o in fix_orders[:2]) and after_other == before_other,
          f"задание {state_job} {error[:200]}; статусы {[s[1] for s in after]}; невыделенные {after_other}")

    requests_log.clear()
    since = fo.ТекущаяДатаСеанса()
    since_ms = fo.ТекущаяУниверсальнаяДатаВМиллисекундах()
    form_id = fo.NewObject("УникальныйИдентификатор", str(uuid.uuid4()))
    state_job, error = run_job(fo, f"{PROC}.НачатьОтправку", [array(fo, fix_orders[:2]), False, form_id])
    wait_bsp_jobs(fo, since)
    time.sleep(1)
    sent = [status_info(fo, o) for o in fix_orders[:2]]
    log_counts = sent_orders_from_log(stub_comments(fo, since))
    weights = key_op_weights(fo, since_ms)
    check("4. Отправить (текущий вызов): статус Отправлено, в пакете 2 заявки, ключевая операция вес 2, 0 HTTP-запросов",
          state_job == "Задание выполнено" and all(s[0] == sent_name for s in sent)
          and log_counts == [2] and [w for w, _ in weights] == [2] and not requests_log,
          f"задание {state_job} {error[:200]}; статусы {[s[1] for s in sent]}; заявок в пакетах {log_counts}; "
          f"ключевая операция {weights}; HTTP {requests_log}")

    unprepared = fix_orders[2]
    before = status_info(fo, unprepared)
    since = fo.ТекущаяДатаСеанса()
    state_job, error = run_job(fo, f"{PROC}.НачатьОтправку", [array(fo, [unprepared]), False,
                                                              fo.NewObject("УникальныйИдентификатор", str(uuid.uuid4()))])
    wait_bsp_jobs(fo, since)
    time.sleep(1)
    after_unprepared = status_info(fo, unprepared)
    check("5. Отправить неподготовленное: отклонено типовой проверкой, статус не изменился, пакет не отправлен",
          state_job == "Задание выполнено" and after_unprepared[0] == before[0]
          and not sent_orders_from_log(stub_comments(fo, since)),
          f"статус до {before[1]}, после {after_unprepared[1]}")

    state_job, error = run_job(fo, f"{PROC}.ПодготовитьПоручения", [array(fo, fix_orders[:2])])
    again = [status_info(fo, o) for o in fix_orders[:2]]
    requests_log.clear()
    since = fo.ТекущаяДатаСеанса()
    since_ms = fo.ТекущаяУниверсальнаяДатаВМиллисекундах()
    state_job2, error2 = run_job(fo, f"{PROC}.НачатьОтправку", [array(fo, fix_orders[:2]), True,
                                                                fo.NewObject("УникальныйИдентификатор", str(uuid.uuid4()))])
    wait_bsp_jobs(fo, since)
    time.sleep(1)
    sent_again = [status_info(fo, o) for o in fix_orders[:2]]
    log_counts = sent_orders_from_log(stub_comments(fo, since))
    weights = key_op_weights(fo, since_ms)
    check("6-7. Повтор: Подготовить снова, Отправить фоновым заданием (длительная операция БСП)",
          state_job == "Задание выполнено" and state_job2 == "Задание выполнено"
          and all(s[0] in ready_names for s in again)
          and all(s[0] == sent_name for s in sent_again)
          and log_counts == [2] and [w for w, _ in weights] == [2] and not requests_log,
          f"после подготовки {[s[1] for s in again]}; после отправки {[s[1] for s in sent_again]}; "
          f"заявок в пакетах {log_counts}; ключевая операция {weights}; HTTP {requests_log} {error2[:200]}")


def main():
    fo = connect("wim_fo")
    if "--restore" in sys.argv:
        with open(STATE_FILE, encoding="utf-8") as f:
            saved_state = json.load(f)
        restore(fo, saved_state)
        return
    server = ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print("Строка соединения:", fo.СтрокаСоединенияИнформационнойБазы())
    state = setup(fo)
    print("Тестовые поручения:", state["orders"])
    if "--keep" in sys.argv:
        print("Данные подготовлены и оставлены (снимок keep_state.json). Восстановление: --restore")
        server.shutdown()
        return
    try:
        run_checks(fo, state)
    finally:
        restore(fo, state)
        server.shutdown()
    failed = [n for n, ok in results if not ok]
    print(f"\nИтог: {len(results) - len(failed)}/{len(results)} OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
