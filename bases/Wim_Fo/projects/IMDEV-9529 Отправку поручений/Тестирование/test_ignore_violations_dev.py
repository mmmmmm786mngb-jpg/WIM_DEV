"""Проверка перехватчика FO_SendFixStub_ЗаписатьСтатусыПоручений (1.0.0.2) в разработческой базе ФО.

    python test_ignore_violations_dev.py

Берется проведенное поручение базы, его запись регистра СтатусыПоручений сохраняется. Фоновым заданием (как в
распорядителе) вызывается ИсполнителиПолныеПрава.ЗаписатьСтатусыПоручений с одной строкой проверки: зона
Красная, Отказ = Истина.
  1. с расширением: статус поручения "Проверено" (или "Ожидает отправки"), событие журнала
     "Нарушения лимитов проигнорированы: поручений 1 из 1";
  2. контроль с отключенным расширением: статус "Проверка не пройдена".
В конце запись регистра поручения восстанавливается, расширение включается обратно.
"""
import glob
import sys
import time
import uuid

sys.stdout.reconfigure(encoding="utf-8")
STAND = glob.glob(r"C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО")[0]
sys.path.insert(0, STAND)
from stand_common import connect  # noqa: E402

EXT = "FO_SendFixStub"
results = []


def check(name, ok, details=""):
    results.append((name, ok))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" - {details}" if details else ""))


def set_active(fo, active):
    items = fo.РасширенияКонфигурации.Получить()
    for i in range(items.Количество()):
        ext = items.Получить(i)
        if ext.Имя == EXT:
            ext.Активно = active
            ext.Записать()


def find_order(fo):
    query = fo.NewObject("Запрос", "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.Поручение КАК Т "
                                   "ГДЕ Т.Проведен И НЕ Т.ПометкаУдаления УПОРЯДОЧИТЬ ПО Т.Дата УБЫВ")
    table = query.Выполнить().Выгрузить()
    if table.Количество() == 0:
        raise SystemExit("В базе нет проведенных поручений")
    return table.Получить(0).Ссылка


def status_set(fo, order):
    records = fo.РегистрыСведений.СтатусыПоручений.СоздатьНаборЗаписей()
    records.Отбор.Поручение.Установить(order)
    records.Прочитать()
    return records


def status_of(fo, order):
    records = status_set(fo, order)
    return fo.String(records.Получить(0).Статус) if records.Количество() else "<нет записи>"


def check_table(fo, order):
    table = fo.NewObject("ТаблицаЗначений")
    table.Колонки.Добавить("Поручение", fo.NewObject("ОписаниеТипов", "ДокументСсылка.Поручение"))
    table.Колонки.Добавить("Лимит", fo.NewObject("ОписаниеТипов", "СправочникСсылка.Лимиты"))
    table.Колонки.Добавить("Зона", fo.NewObject("ОписаниеТипов", "ПеречислениеСсылка.ЗоныПроверкиЛимитов"))
    table.Колонки.Добавить("Отказ", fo.NewObject("ОписаниеТипов", "Булево"))
    row = table.Добавить()
    row.Поручение = order
    row.Зона = fo.Перечисления.ЗоныПроверкиЛимитов.Красная
    row.Отказ = True
    return table


def run_write_statuses(fo, order):
    method_args = fo.NewObject("Массив")
    method_args.Добавить(check_table(fo, order))
    method_args.Добавить(fo.NewObject("УникальныйИдентификатор", str(uuid.uuid4())))
    params = fo.NewObject("Массив")
    params.Добавить("ИсполнителиПолныеПрава.ЗаписатьСтатусыПоручений")
    params.Добавить(method_args)
    job = fo.ФоновыеЗадания.Выполнить("ОбщегоНазначения.ВыполнитьМетодКонфигурации", params, None,
                                      "IMDEV-9529 тест игнорирования нарушений")
    uid = job.УникальныйИдентификатор
    for _ in range(120):
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != fo.СостояниеФоновогоЗадания.Активно:
            error = fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке) if job.ИнформацияОбОшибке else ""
            return fo.String(job.Состояние), error
        time.sleep(0.5)
    return "Таймаут", ""


def stub_events(fo, since):
    table = fo.NewObject("ТаблицаЗначений")
    log_filter = fo.NewObject("Структура")
    log_filter.Вставить("Событие", "IMDEV-9529.ЗаглушкаFIX")
    log_filter.Вставить("ДатаНачала", since)
    for _ in range(20):
        fo.ВыгрузитьЖурналРегистрации(table, log_filter)
        comments = [table.Get(i).Комментарий for i in range(table.Count())]
        if comments:
            return comments
        time.sleep(0.5)
    return []


def main():
    fo = connect("wim_fo")
    order = find_order(fo)
    print("Поручение:", fo.String(order), "| статус до теста:", status_of(fo, order))
    saved = status_set(fo, order).Выгрузить()
    try:
        since = fo.ТекущаяДатаСеанса()
        state, error = run_write_statuses(fo, order)
        status = status_of(fo, order)
        comments = [c for c in stub_events(fo, since) if "Нарушения лимитов" in c]
        check("1. С расширением: нарушение снято, статус без 'Проверка не пройдена'",
              state == "Задание выполнено" and status in ("Проверено", "Ожидает отправки")
              and comments and "поручений 1 из 1" in comments[-1],
              f"задание {state} {error}; статус {status}; журнал {comments[-1] if comments else '-'}")

        set_active(fo, False)
        fo_plain = connect("wim_fo")
        plain_order = fo_plain.Документы.Поручение.ПолучитьСсылку(
            fo_plain.NewObject("УникальныйИдентификатор", str(fo.String(order.УникальныйИдентификатор()))))
        state, error = run_write_statuses(fo_plain, plain_order)
        status = status_of(fo_plain, plain_order)
        check("2. Контроль без расширения: статус 'Проверка не пройдена'",
              state == "Задание выполнено" and status == "Проверка не пройдена",
              f"задание {state} {error}; статус {status}")
        del fo_plain
    finally:
        set_active(fo, True)
        records = status_set(fo, order)
        records.Загрузить(saved)
        records.Записать()
        print("Запись регистра восстановлена, статус:", status_of(fo, order))

    failed = [n for n, ok in results if not ok]
    print(f"\nИтог: {len(results) - len(failed)}/{len(results)} OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
