# -*- coding: utf-8 -*-
"""Прогон обработки замеров Т-1/МО/ЗамерБлокировок на стенде IMDEV-9532 (dev WIM_MO -> WIN_FO_server).

На dev МО нет остатков блокировок ДС, поэтому:
  1. Подготовка без подстановки - проверка запроса блокировок и разделов сведений (ожидается "нет мандатов").
  2. Полный замер на подставленных блокировках: по одной на тестовый мандат T9532 (рублевый банковский счет),
     у двух мандатов счет чужого мандата МО, которого нет в ФО, - проверка ветки ошибки пакета и повтора 1.43.

    python run_zamer_dev.py [мандатов=60]

Лог - Тестирование/reports/zamer_dev_<время>.txt. В dev ФО создаются поручения LOCK:T9532..._B:T9744C...
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
STAND = os.path.join(os.path.dirname(TASK),
                     "IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО", "Тестирование", "Стенд_МО_ФО")
sys.path.insert(0, STAND)
from stand_common import PREFIX, connect, query, query_table, to_array, mandate_code  # noqa: E402

EPF = os.path.join(TASK, "Т-1", "МО", "ЗамерБлокировок", "ЗамерБлокировокМО_ФО.epf")
BAD_INDEXES = (1, 3)  # индекс 1 попадает в выборку проверки, 3 - в выборку сравнения (шаг выборки 3)


def blocks_table(mo, count):
    codes = to_array(mo, [mandate_code(i) for i in range(1, count + 1)])
    rub = query(mo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = \"643\"")[0]["Ссылка"]
    table = query_table(mo, """
        ВЫБРАТЬ
            С.Владелец КАК Мандат, С.Владелец.КодМандата КАК КодМандата, С.Ссылка КАК СчетМандата,
            С.КодСчета КАК КодСчета, &Валюта КАК Валюта, 10000 КАК Количество
        ИЗ Справочник.СчетаМандатов КАК С
        ГДЕ С.КодСчета ПОДОБНО &МаскаБанк И С.Владелец.КодМандата В (&Коды)
        УПОРЯДОЧИТЬ ПО КодМандата""", {"Коды": codes, "Валюта": rub, "МаскаБанк": PREFIX + "%_B"})
    foreign = query(mo, "ВЫБРАТЬ ПЕРВЫЕ 1 С.Ссылка КАК Ссылка, С.КодСчета КАК КодСчета ИЗ Справочник.СчетаМандатов КАК С "
                        "ГДЕ НЕ С.КодСчета ПОДОБНО &Маска И С.КодСчета <> \"\" УПОРЯДОЧИТЬ ПО С.КодСчета",
                    {"Маска": PREFIX + "%"})[0]
    for index in BAD_INDEXES:
        row = table.Получить(index)
        row.СчетМандата = foreign["Ссылка"]
        row.КодСчета = foreign["КодСчета"]
    return table


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    if "--subportfolio" in sys.argv:
        # Учет по субпортфелям в dev ФО включается на время прогона: без него счет чужого мандата не дает
        # ошибки "Не найден Субпортфель" и ветка повтора пакета по мандатам (1.43) не проверяется.
        fo = connect("wim_fo")
        before = fo.Константы.ВестиУчетПоСубпортфелям.Получить()
        fo.Константы.ВестиУчетПоСубпортфелям.Установить(True)
        try:
            run(count)
        finally:
            fo.Константы.ВестиУчетПоСубпортфелям.Установить(before)
            print("ВестиУчетПоСубпортфелям возвращено:", fo.Константы.ВестиУчетПоСубпортфелям.Получить())
        return
    run(count)


def run(count):
    mo = connect("wim_mo")
    protection = mo.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    obj = mo.ВнешниеОбработки.Создать(EPF, False, protection)

    params = obj.ПараметрыПоУмолчанию()
    params.Вставить("АдресФО", "localhost/win_fo")
    first = obj.ПодготовитьЗамер(params)
    text = ["######## 1. Подготовка без подстановки блокировок", first.Лог,
            "Шагов: %d" % first.Шаги.Количество()]

    params = obj.ПараметрыПоУмолчанию()
    params.Вставить("АдресФО", "localhost/win_fo")
    for name, value in (("МандатовВЗамере", 20), ("РазмерПакета", 10), ("МалыйПакет", 5),
                        ("МандатовПроверкиОшибок", 40), ("МандатовВШагеПроверки", 20)):
        params.Вставить(name, value)
    params.Вставить("ТаблицаБлокировок", blocks_table(mo, count))
    prepared = obj.ПодготовитьЗамер(params)
    text += ["", "######## 2. Замер на подставленных блокировках", prepared.Лог]
    steps = prepared.Шаги
    for i in range(steps.Количество()):
        step = steps.Получить(i)
        text.append(obj.ВыполнитьШаг(step, prepared.Данные))
        print("шаг %d/%d: %s" % (i + 1, steps.Количество(), step.Серия), flush=True)

    out = os.path.join(HERE, "reports", "zamer_dev_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(text))
    print("лог:", out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
