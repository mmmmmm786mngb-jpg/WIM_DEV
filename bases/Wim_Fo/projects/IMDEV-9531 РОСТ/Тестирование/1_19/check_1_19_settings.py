# -*- coding: utf-8 -*-
"""Проверка настройки "Срок кеша цены стакана, с" боевой сборки 1.19 во внешнем соединении с dev ФО.

Обработка создается из файла УСКОРЕНО_1_19, справочник дополнительных обработок не меняется. Проверяется:
  1. настройки без поля (как у 1.15-1.18 на ПРОД) -> реквизит 0;
  2. настройки с полем 45 -> реквизит 45, УстановитьПараметры возвращает 45 (сохранение формы "Настройки");
  3. сохраненная структура читается новым экземпляром -> 45;
  4. НастройкиПоУмолчанию -> 0.
"""
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
import os as _os
# Общий стенд IMDEV-9531 (заглушка стакана, тестовые сборки, функции прогона) - в каталоге Тестирование/1_18
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "1_18"))
import run_1_18_tests as base  # noqa: E402

stage4 = base.stage4
EPF = os.path.join(base.TASK, "УСКОРЕНО_1_19", "внСозданиеТорговыхПорученийРОСТ.epf")


def main():
    fo = stage4.connect("wim_fo")
    tmp = os.path.join(tempfile.gettempdir(), "rost_1_19_check.epf")
    shutil.copyfile(EPF, tmp)
    ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": stage4.ROST_OBJECT},
    )
    stored = ref.ПолучитьОбъект().ХранилищеНастроек.Получить()
    results = []

    def check(name, actual, expected):
        ok = actual == expected
        results.append(ok)
        print(("OK  " if ok else "FAIL"), name, "получено", actual, "ожидалось", expected)

    first = fo.ВнешниеОбработки.Создать(tmp, False)
    # настройки из базы без поля срока кеша
    without = fo.NewObject("Структура")
    without.Вставить("КонтрольПоЦенеЗакрытия", False)
    first.СрокКешаЦеныСтаканаСек = 77
    first.УстановитьПользовательскиеНастройки(without, "")
    check("1. настройки без поля", float(first.СрокКешаЦеныСтаканаСек), 0.0)

    with_value = fo.NewObject("Структура")
    with_value.Вставить("СрокКешаЦеныСтаканаСек", 45)
    first.УстановитьПользовательскиеНастройки(with_value, "")
    check("2a. настройки с полем 45", float(first.СрокКешаЦеныСтаканаСек), 45.0)
    title = ""
    saved = first.УстановитьПараметры(title)
    check("2b. УстановитьПараметры содержит поле", bool(saved.Свойство("СрокКешаЦеныСтаканаСек")), True)
    check("2c. УстановитьПараметры значение", float(saved.СрокКешаЦеныСтаканаСек), 45.0)

    second = fo.ВнешниеОбработки.Создать(tmp, False)
    second.УстановитьПользовательскиеНастройки(saved, "")
    check("3. новый экземпляр читает сохраненное", float(second.СрокКешаЦеныСтаканаСек), 45.0)

    second.НастройкиПоУмолчанию(second)
    check("4. НастройкиПоУмолчанию", float(second.СрокКешаЦеныСтаканаСек), 0.0)

    # настройки, которые сейчас лежат в базе (сохранены версиями до 1.19)
    third = fo.ВнешниеОбработки.Создать(tmp, False)
    third.СрокКешаЦеныСтаканаСек = 99
    third.УстановитьПользовательскиеНастройки(stored, "")
    check("5. настройки dev-базы (без поля)", float(third.СрокКешаЦеныСтаканаСек), 0.0)

    os.remove(tmp)
    print("ИТОГ", sum(results), "из", len(results))


if __name__ == "__main__":
    main()
