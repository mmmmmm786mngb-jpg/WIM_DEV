# Сборка тестовой обработки ..\Тестирование\T431_Сверка.epf: модуль 1.08 из ОПТИМИЗИРОВАНО + Т431-функции
# из ..\Тестирование\test_harness.bsl; размер пачки задается переменной Т431_РазмерПорции.
# Затем регистрация в dev WIM_DU карточкой "T431 Сверка TWR (стенд)" без безопасного режима.
import glob
import os
import shutil
import subprocess
import sys

import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
NAME = "внЗаполнениеРеглОтчетаПоДоговорамДУ_0420431_71"
SRC = os.path.join(TASK, "ОПТИМИЗИРОВАНО", NAME + "_epf")
DST = os.path.join(TASK, "Тестирование", "T431_src")
EPF = os.path.join(TASK, "Тестирование", "T431_Сверка.epf")
CARD = "T431 Сверка TWR (стенд)"


def build():
    shutil.rmtree(DST, ignore_errors=True)
    shutil.copytree(SRC, DST)
    p = os.path.join(DST, NAME, "Ext", "ObjectModule.bsl")
    s = open(p, encoding="utf-8-sig").read().replace("\r\n", "\n")
    h = open(os.path.join(TASK, "Тестирование", "test_harness.bsl"), encoding="utf-8").read()
    k = "Перем МассивСоединений;"
    assert s.count(k) == 1 and s.count("\tВозврат 500;") == 1
    s = s.replace(k, k + "\nПерем Т431_РазмерПорции;\nПерем Т431_ОтключитьПозиции;\nПерем Т431_Пачек;"
                  "\nПерем Т431_ПачекПоСтрокам;", 1)
    # Счетчики пачек и переключатель свертки по позициям (только в тестовой копии).
    cond = "\t\t\tИли НЕ СвернутьПорциюПоПозициям(Соединение, ДанныеПорции, ИтогиПоМандатам) Тогда\n"
    rel = "\t\t// Ссылки на таблицу пачки снимаются до следующего вызова TWR.\n"
    assert s.count(cond) == 1 and s.count(rel) == 1
    s = s.replace(cond, "\t\t\tИли Т431_ОтключитьПозиции = Истина\n" + cond
                  + "\t\t\tТ431_ПачекПоСтрокам = Т431_ПачекПоСтрокам + 1;\n")
    s = s.replace(rel, "\t\tТ431_Пачек = Т431_Пачек + 1;\n" + rel)
    s = s.replace("\tВозврат 500;", "\tЕсли Т431_РазмерПорции <> Неопределено Тогда\n\t\tВозврат Т431_РазмерПорции;"
                  "\n\tКонецЕсли;\n\tВозврат 500;")
    s = s.rstrip("\n") + "\n" + h
    open(p, "w", encoding="utf-8-sig", newline="\r\n").write(s)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-File",
                        os.path.expanduser("~/.claude/skills/epf-build/scripts/epf-build.ps1"),
                        "-InfoBaseServer", "localhost", "-InfoBaseRef", "WIM_DU", "-Checks", "off",
                        "-SourceFile", os.path.join(DST, NAME + ".xml"), "-OutputFile", EPF],
                       capture_output=True, text=True, encoding="cp866", errors="replace")
    print(r.stdout[-300:], r.stderr[-300:])
    assert os.path.exists(EPF)


def register():
    c = win32com.client.Dispatch("V83.COMConnector").Connect('Srvr="localhost";Ref="WIM_DU";')
    found = c.Справочники.ДополнительныеОтчетыИОбработки.НайтиПоНаименованию(CARD, True)
    obj = found.ПолучитьОбъект() if not found.Пустая() else c.Справочники.ДополнительныеОтчетыИОбработки.СоздатьЭлемент()
    obj.Наименование = CARD
    obj.ИмяОбъекта = NAME
    obj.ИмяФайла = "T431_Сверка.epf"
    obj.Вид = c.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
    obj.Публикация = c.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    obj.БезопасныйРежим = False
    obj.ХранилищеОбработки = c.NewObject("ХранилищеЗначения", c.NewObject("ДвоичныеДанные", EPF))
    obj.Версия = "1.08-T431"
    obj.Записать()
    print("карточка", c.XMLСтрока(obj.Ссылка))


if __name__ == "__main__":
    build()
    register()
    sys.stdout.flush()
    os._exit(0)
