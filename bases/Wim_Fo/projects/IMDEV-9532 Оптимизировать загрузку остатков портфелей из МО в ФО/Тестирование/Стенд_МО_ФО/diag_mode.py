# -*- coding: utf-8 -*-
"""Диагностические переключатели стенда на ФО.

  python diag_mode.py versioning on|off  - версионирование справочника Портфели при записи (как в ПРОД).
      Каждая запись флага в ДополнительныеСведения создает версию портфеля, поэтому число версий тестовых
      портфелей - точный счетчик записей флагов, а стоимость записи ближе к ПРОД.
      Исходные значения константы и настройки запоминаются в state.json и возвращаются командой off.
  python diag_mode.py extension on|off   - активность расширения FO_PositionLoadOpt.
  python diag_mode.py versions           - число версий тестовых портфелей.
"""
import sys

from stand_common import PREFIX, connect, load_state, query, save_state

EXTENSION = "FO_PositionLoadOpt"


def versions_count(fo):
    rows = query(fo, """
        ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Всего
        ИЗ РегистрСведений.ВерсииОбъектов КАК ВерсииОбъектов
        ГДЕ ВЫРАЗИТЬ(ВерсииОбъектов.Объект КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &Маска""",
                 {"Маска": PREFIX + "%"})
    return rows[0]["Всего"]


def portfolio_type_id(fo):
    return fo.ОбщегоНазначения.ИдентификаторОбъектаМетаданных("Справочник.Портфели")


def versioning(fo, enable):
    state = load_state()
    manager = fo.РегистрыСведений.НастройкиВерсионированияОбъектов
    type_id = portfolio_type_id(fo)
    if enable:
        if "versioning_original" not in state:
            record = manager.СоздатьМенеджерЗаписи()
            record.ТипОбъекта = type_id
            record.Прочитать()
            state["versioning_original"] = {
                "константа": bool(fo.Константы.ИспользоватьВерсионированиеОбъектов.Получить()),
                "настройка": fo.ЗначениеВСтрокуВнутр(record.Вариант) if record.Выбран() else None,
            }
            save_state(state)
        fo.Константы.ИспользоватьВерсионированиеОбъектов.Установить(True)
        fo.ВерсионированиеОбъектов.ЗаписатьНастройкуВерсионированияПоОбъекту(
            type_id, fo.Перечисления.ВариантыВерсионированияОбъектов.ВерсионироватьПриЗаписи)
    else:
        original = state.get("versioning_original")
        if original is None:
            print("Исходное состояние не сохранено - нечего возвращать")
            return
        if original["настройка"] is None:
            record_set = manager.СоздатьНаборЗаписей()
            record_set.Отбор.ТипОбъекта.Установить(type_id)
            record_set.Записать()
        else:
            fo.ВерсионированиеОбъектов.ЗаписатьНастройкуВерсионированияПоОбъекту(
                type_id, fo.ЗначениеИзСтрокиВнутр(original["настройка"]))
        fo.Константы.ИспользоватьВерсионированиеОбъектов.Установить(original["константа"])
        del state["versioning_original"]
        save_state(state)
    print("Версионирование портфелей:", "включено" if enable else "возвращено в исходное состояние",
          "| константа =", fo.Константы.ИспользоватьВерсионированиеОбъектов.Получить())


def extension(fo, enable):
    exts = fo.РасширенияКонфигурации.Получить()
    for i in range(exts.Количество()):
        ext = exts.Получить(i)
        if ext.Имя == EXTENSION:
            # Расширение перехватывает модуль обработки обмена: в безопасном режиме платформа такой перехват
            # не применяет (журнал: "расширение модуля запрещено ... подключено в безопасном режиме").
            ext.Активно = enable
            ext.БезопасныйРежим = False
            ext.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
            ext.Записать()
            problems = ext.ПроверитьВозможностьПрименения()
            print(EXTENSION, "активно" if enable else "неактивно", "| безопасный режим:", ext.БезопасныйРежим,
                  "| проблем применимости:", problems.Количество())
            return
    print(EXTENSION, "не найдено")


def main():
    fo = connect("wim_fo")
    command = sys.argv[1]
    if command == "versions":
        print("Версий тестовых портфелей:", versions_count(fo))
    elif command == "versioning":
        versioning(fo, sys.argv[2] == "on")
    elif command == "extension":
        extension(fo, sys.argv[2] == "on")


if __name__ == "__main__":
    main()
