"""Проверка расширения FO_SendFixStub в разработческой базе ФО (WIN_FO_server) через внешнее соединение.

    python test_stub_dev.py

Модуль менеджера АдаптерFIX во внешнем соединении не инициализируется (типовой код ссылается на серверный
модуль РаботаСАдаптерамиПолныеПрава), поэтому методы адаптера вызываются фоновыми заданиями на сервере
через ОбщегоНазначения.ВыполнитьМетодКонфигурации - так же на сервере, как при настоящей отправке поручений.

Временные данные (удаляются в конце): адаптер вида FIX, запись ИспользуемыеАдаптеры, настройки
WebSocket-прокси на локальный HTTP-слушатель 127.0.0.1:18529, сообщения адаптера.

Проверки:
  1. заглушка включена в базе из списка (ЗаглушкаОтправкиFIXВключена);
  2. АдаптерыПорученийГотовыеКРаботе = типовой список + идентификатор тестового адаптера FIX;
  3. фоновое задание ОтправитьПакетАдаптеру (/send): событие журнала регистрации и JSON-файл
     с orders = 2 и guid тестового адаптера;
  4. фоновое задание ВыполнитьРазъединение (send?params + disconnect): слушатель не получил ни одного
     HTTP-запроса, send?params записан в JSON-файл;
  5. контроль: с отключенным расширением то же задание отправляет HTTP-запросы слушателю
     (слушатель доступен, блокирует именно заглушка). После контроля расширение включается обратно.
"""
import glob
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding="utf-8")
STAND = glob.glob(r"C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО")[0]
sys.path.insert(0, STAND)
from stand_common import connect  # noqa: E402

EXT = "FO_SendFixStub"
EVENT = "IMDEV-9529.ЗаглушкаFIX"
PROXY_PORT = 18529
SETTINGS = ("ВебСокетПрокси", "НастройкиВебСокетПрокси", "7f5e9f00-f3dc-4178-b225-90bdf5bd8e44")

results = []
requests_log = []


class Listener(BaseHTTPRequestHandler):
    def _answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        requests_log.append(f"{self.command} {self.path[:60]}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
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
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" - {details}" if details else ""))


def ids(fo, array):
    return {str(fo.String(array.Get(i))) for i in range(array.Count())}


def find_extension(fo):
    items = fo.РасширенияКонфигурации.Получить()
    for i in range(items.Количество()):
        if items.Получить(i).Имя == EXT:
            return items.Получить(i)
    raise SystemExit(f"Расширение {EXT} не найдено")


def set_active(fo, active):
    ext = find_extension(fo)
    ext.Активно = active
    if active:
        ext.БезопасныйРежим = False
    ext.Записать()


def run_job(fo, method, args):
    method_args = fo.NewObject("Массив")
    for value in args:
        method_args.Добавить(value)
    params = fo.NewObject("Массив")
    params.Добавить(method)
    params.Добавить(method_args)
    job = fo.ФоновыеЗадания.Выполнить("ОбщегоНазначения.ВыполнитьМетодКонфигурации", params, None,
                                      "IMDEV-9529 тест заглушки")
    uid = job.УникальныйИдентификатор
    for _ in range(120):
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        state = fo.String(job.Состояние)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно:
            error = ""
            if job.ИнформацияОбОшибке is not None:
                error = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
            return state, error
        time.sleep(0.5)
    return "Таймаут", ""


def stub_events(fo, since):
    for _ in range(20):
        table = fo.NewObject("ТаблицаЗначений")
        log_filter = fo.NewObject("Структура")
        log_filter.Вставить("Событие", EVENT)
        log_filter.Вставить("ДатаНачала", since)
        fo.ВыгрузитьЖурналРегистрации(table, log_filter)
        comments = [table.Get(i).Комментарий for i in range(table.Count())]
        if comments:
            return comments
        time.sleep(0.5)
    return []


def orders_from_comment(comment):
    marker = "заявок 35=D: "
    if marker not in comment:
        return None
    return int(comment.split(marker, 1)[1].split(",", 1)[0])


def adapter_params(fo, adapter):
    # Признак "ожидается на клиенте": без менеджера обработки, модуль адаптера во внешнем соединении не нужен.
    return fo.Справочники.Адаптеры.ПараметрыАдаптера(adapter, True)


def setup(fo):
    obj = fo.Справочники.Адаптеры.СоздатьЭлемент()
    obj.Наименование = "IMDEV-9529 тест заглушки FIX"
    obj.Вид = fo.Перечисления.ВидыАдаптеров.FIX
    obj.Использовать = True
    obj.Отправитель = "TEST_SENDER"
    obj.Получатель = "TEST_TARGET"
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    adapter = obj.Ссылка

    record = fo.РегистрыСведений.ИспользуемыеАдаптеры.СоздатьМенеджерЗаписи()
    record.Адаптер = adapter
    record.Идентификатор = fo.NewObject("УникальныйИдентификатор")
    record.Используется = True
    record.Записать()
    used_id = str(fo.String(record.Идентификатор))

    settings = fo.NewObject("Структура")
    settings.Вставить("АдресHTTPСервиса", f"http://127.0.0.1:{PROXY_PORT}")
    fo.ОбщегоНазначения.ХранилищеОбщихНастроекСохранить(SETTINGS[0], SETTINGS[1], settings, None, SETTINGS[2])
    return adapter, used_id


def cleanup(fo, adapter):
    for register in ("СообщенияАдаптеров", "СообщенияАдаптеровСчетчики", "СостоянияАдаптеров"):
        manager = getattr(fo.РегистрыСведений, register)
        records = manager.СоздатьНаборЗаписей()
        if hasattr(records.Отбор, "Адаптер"):
            records.Отбор.Адаптер.Установить(adapter)
            records.Записать()
    used = fo.РегистрыСведений.ИспользуемыеАдаптеры.СоздатьНаборЗаписей()
    used.Прочитать()
    for i in reversed(range(used.Количество())):
        if same_ref(fo, used.Получить(i).Адаптер, adapter):
            used.Удалить(i)
    used.Записать()
    obj = adapter.ПолучитьОбъект()
    obj.ОбменДанными.Загрузка = True
    obj.Удалить()
    fo.ОбщегоНазначения.ХранилищеОбщихНастроекУдалить(SETTINGS[0], SETTINGS[1], SETTINGS[2])
    print("Временные данные удалены")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    fo = connect("wim_fo")
    print("Строка соединения:", fo.СтрокаСоединенияИнформационнойБазы())
    adapter, used_id = setup(fo)
    guid = str(fo.String(adapter.УникальныйИдентификатор()))
    try:
        check("1. Заглушка включена", bool(fo.Адаптеры.ЗаглушкаОтправкиFIXВключена()))

        base = ids(fo, fo.РегистрыСведений.СостоянияАдаптеров.АдаптерыПорученийГотовыеКРаботе())
        ext = ids(fo, fo.Адаптеры.АдаптерыПорученийГотовыеКРаботе())
        check("2. Готовые адаптеры = типовые + тестовый FIX",
              ext == base | {used_id} and used_id not in base,
              f"типовых {len(base)}, с заглушкой {len(ext)}")

        since = fo.ТекущаяДатаСеанса()
        soh = "\x01"
        order = soh.join(["8=FIX.4.2", "9=100", "35=D", "49=TEST", "56=TEST", "34=1", "11=1", "10=000"]) + soh
        packet = order + order.replace("11=1", "11=2").replace("34=1", "34=2")
        requests_log.clear()
        state, error = run_job(fo, "Обработки.АдаптерFIX.ОтправитьПакетАдаптеру", [guid, packet, None])
        comments = stub_events(fo, since)
        comment = comments[-1] if comments else ""
        check("3а. Фоновое задание: /send записан заглушкой, в прокси не ушел",
              state == "Задание выполнено" and len(comments) == 1 and comment.startswith("Команда /send")
              and orders_from_comment(comment) == 2 and not requests_log,
              f"задание {state} {error}; HTTP-запросов {len(requests_log)}; журнал: {comment}")

        # Каталог временных файлов службы 1С недоступен на чтение, поэтому формат файла проверяется
        # вызовом той же процедуры записи во внешнем соединении: файл попадает в каталог текущего пользователя.
        body = json.dumps({"guid": guid, "message": urllib.parse.quote(packet, safe="")}, separators=(",", ":"))
        local_dir = os.path.join(fo.КаталогВременныхФайлов(), "IMDEV-9529_FIX")
        before = set(glob.glob(os.path.join(local_dir, "*.json")))
        fo.Адаптеры.ЗаписатьВызовПроксиFIX("/send", body)
        new_files = sorted(set(glob.glob(os.path.join(local_dir, "*.json"))) - before)
        data = {}
        if new_files:
            with open(new_files[-1], encoding="utf-8-sig") as f:
                data = json.load(f)
        check("3б. JSON-файл: command, guid, orders, messages",
              data.get("command") == "/send" and data.get("guid") == guid and data.get("orders") == 2
              and data.get("body_length") == len(body) and data.get("messages", "").count("|35=D|") == 2,
              f"файл {new_files[-1] if new_files else '-'}; orders={data.get('orders')}; "
              f"messages={data.get('messages', '')[:70]}...")

        since = fo.ТекущаяДатаСеанса()
        time.sleep(1.1)
        requests_log.clear()
        state, error = run_job(fo, "Обработки.АдаптерFIX.ВыполнитьРазъединение", [adapter_params(fo, adapter)])
        comments = stub_events(fo, since)
        commands = [c.split(",", 1)[0] for c in comments]
        check("4. send?params в JSON, disconnect не выполнен, HTTP-запросов нет",
              state == "Задание выполнено" and not requests_log and any("send?params" in c for c in commands),
              f"задание {state} {error}; события: {commands}; HTTP-запросов {len(requests_log)}")

        set_active(fo, False)
        fo_plain = connect("wim_fo")
        requests_log.clear()
        plain_adapter = fo_plain.Справочники.Адаптеры.ПолучитьСсылку(fo_plain.NewObject("УникальныйИдентификатор", guid))
        state, error = run_job(fo_plain, "Обработки.АдаптерFIX.ВыполнитьРазъединение",
                               [adapter_params(fo_plain, plain_adapter)])
        time.sleep(1)
        check("5. Контроль без расширения: HTTP-запросы доходят до слушателя",
              len(requests_log) > 0, f"задание {state}; запросы: {requests_log}")
        del fo_plain
    finally:
        set_active(fo, True)
        print("Расширение включено:", find_extension(fo).Активно, "| безопасный режим:", find_extension(fo).БезопасныйРежим)
        cleanup(fo, adapter)
        server.shutdown()

    failed = [n for n, ok in results if not ok]
    print(f"\nИтог: {len(results) - len(failed)}/{len(results)} OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
