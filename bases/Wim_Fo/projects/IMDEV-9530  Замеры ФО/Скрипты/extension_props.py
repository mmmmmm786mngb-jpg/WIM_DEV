"""Свойства расширений в разработческой базе ФО (WIN_FO_server) через внешнее соединение.

Серверную базу ibcmd не открывает, поэтому безопасный режим и применимость смотрим по COM.

    python extension_props.py list                  - все расширения: версия, активность, безопасный режим
    python extension_props.py prepare FO_KeyOpsPerf - активно, без безопасного режима, без предупреждений
    python extension_props.py check FO_KeyOpsPerf FO_PositionLoadOpt - проблемы применимости
    python extension_props.py deactivate FO_KeyOpsPerf - отключить (базовый прогон без замеров)

Подключение берется из стендовых скриптов IMDEV-9532 (реестр баз WIM_DEV).
"""
import glob
import os
import sys

STAND = glob.glob(r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО')[0]
sys.path.insert(0, STAND)
from stand_common import connect  # noqa: E402


def extensions(fo):
    items = fo.РасширенияКонфигурации.Получить()
    return [items.Получить(i) for i in range(items.Количество())]


def find(fo, name):
    for ext in extensions(fo):
        if ext.Имя == name:
            return ext
    raise SystemExit(f"Расширение {name} не найдено")


def show(fo, ext):
    print(f"{ext.Имя:20} версия {ext.Версия or '-':10} активно {str(ext.Активно):6} "
          f"безопасный режим {str(ext.БезопасныйРежим):6}")


def check(fo, name):
    ext = find(fo, name)
    problems = ext.ПроверитьВозможностьПрименения()
    print(f"{name}: проблем применимости {problems.Количество()}")
    for i in range(problems.Количество()):
        p = problems.Получить(i)
        print("   ", p.Важность, p.Описание)


def main():
    fo = connect("wim_fo")
    command = sys.argv[1]
    if command == "list":
        for ext in extensions(fo):
            show(fo, ext)
    elif command == "prepare":
        ext = find(fo, sys.argv[2])
        # В безопасном режиме платформа не применяет перехват модуля обработки, а БСП не пишет замеры.
        ext.Активно = True
        ext.БезопасныйРежим = False
        ext.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
        ext.Записать()
        show(fo, find(fo, sys.argv[2]))
    elif command == "deactivate":
        ext = find(fo, sys.argv[2])
        ext.Активно = False
        ext.Записать()
        show(fo, find(fo, sys.argv[2]))
    elif command == "check":
        for name in sys.argv[2:]:
            check(fo, name)


if __name__ == "__main__":
    main()
