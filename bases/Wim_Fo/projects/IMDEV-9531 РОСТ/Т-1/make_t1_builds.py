# -*- coding: utf-8 -*-
"""Сборки РОСТ для ручной проверки на Т-1 (копия ПРОД): "1.16-т1" из ОРИГИНАЛ_1_16 и "1.21-т1" из УСКОРЕНО_1_21.

Обе сборки получают одинаковые служебные вставки, алгоритм создания поручений не меняется:
- тестовый режим включен в теле модуля (позиция на прошлый день, цена - котировка из регистра, без адаптера);
- перед запросом цены в тестовом режиме пауза 1 с (ожидание ответа стакана на ПРОД): в фоновом задании -
  ожидание завершения своего же задания с таймаутом 1 с, иначе цикл до истечения 1 с;
- проверка лимитов без отправки на биржу: ОтправитьПослеПроверки = Не ЭтоТест;
- списки реинвестирования и продаж под блокировки упорядочены по портфелю и активу (одинаковый порядок в прогонах).

    python make_t1_builds.py      -> Т-1/сборки/<версия>-т1 (исходники) и Т-1/РОСТ_<версия>-т1.epf
"""
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
ROOT_XML = "внСозданиеТорговыхПорученийРОСТ.xml"
MODULE = os.path.join("внСозданиеТорговыхПорученийРОСТ", "Ext", "ObjectModule.bsl")
BUILDS = {"1.16": "ОРИГИНАЛ_1_16", "1.21": "УСКОРЕНО_1_21"}
EPF_BUILD = os.path.join(os.path.expanduser("~"), ".claude", "skills", "epf-build", "scripts", "epf-build.ps1")

PAUSE = """// IMDEV-9531 СБОРКА Т-1: пауза 1 с вместо ответа стакана на ПРОД. В фоновом задании - ожидание завершения
// своего же задания с таймаутом (процессор не занимает), вне фонового задания - цикл до истечения 1 с.
//
Процедура ПаузаСтаканаТ1()

	Окончание = ТекущаяУниверсальнаяДатаВМиллисекундах() + 1000;
	ТекущееЗадание = ПолучитьТекущийСеансИнформационнойБазы().ПолучитьФоновоеЗадание();
	Если ТекущееЗадание <> Неопределено Тогда
		Попытка
			ТекущееЗадание.ОжидатьЗавершенияВыполнения(1);
		Исключение
			// Ожидание прервано платформой: оставшееся время добирается циклом ниже.
		КонецПопытки;
	КонецЕсли;
	Пока ТекущаяУниверсальнаяДатаВМиллисекундах() < Окончание Цикл
	КонецЦикла;

КонецПроцедуры

"""

ORDER = '\t// IMDEV-9531 СБОРКА Т-1: одинаковый порядок списка в прогонах\n' \
        '\tЗапрос.Текст = Запрос.Текст + Символы.ПС + "УПОРЯДОЧИТЬ ПО Портфель, Актив";\n'

def replace_once(text, old, new, what):
    assert text.count(old) == 1, "%s: найдено %d" % (what, text.count(old))
    return text.replace(old, new)


def patch(text, version):
    text = text.replace("\r\n", "\n")
    text = replace_once(text, '\tПараметрыРегистрации.Версия = "%s";' % version,
                        '\tПараметрыРегистрации.Версия = "%s-т1";' % version, "версия")
    text = replace_once(text, "\nЭтоТест = Ложь;", "\n// IMDEV-9531 СБОРКА Т-1: тестовый режим\nЭтоТест = Истина;",
                        "тело модуля")
    text = replace_once(text, "\tУказания.ОтправитьПослеПроверки = Истина;",
                        "\t// IMDEV-9531 СБОРКА Т-1: в тестовом режиме проверка лимитов без отправки на биржу\n"
                        "\tУказания.ОтправитьПослеПроверки = Не ЭтоТест;", "отправка")

    start = text.index("Функция ИзменитьЦенуПорученияТест(")
    query = text.index("Запрос = новый запрос;", start)
    line_start = text.rindex("\n", 0, query) + 1
    indent = text[line_start:query]
    text = text[:query] + "ПаузаСтаканаТ1(); // IMDEV-9531 СБОРКА Т-1\n" + indent + text[query:]
    text = text[:start] + PAUSE + text[start:]

    for table in ("СписокПортфелейРеинвестирование", "СписокПортфелейПродажиПодБлокировки"):
        load = "\t%s.Загрузить(Запрос.Выполнить().Выгрузить());" % table
        assert text.count(load) == 1, table
        text = text.replace(load, ORDER + load)
    return text.replace("\n", "\r\n")


def main():
    for version, folder in BUILDS.items():
        src = os.path.join(TASK, folder, "внСозданиеТорговыхПорученийРОСТ_epf")
        dst = os.path.join(HERE, "сборки", version + "-т1")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        path = os.path.join(dst, MODULE)
        with open(path, "r", encoding="utf-8-sig") as handle:
            text = handle.read()
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            handle.write(patch(text, version))
        epf = os.path.join(HERE, "РОСТ_%s-т1.epf" % version)
        result = subprocess.run(["powershell.exe", "-NoProfile", "-File", EPF_BUILD, "-Checks", "off",
                                 "-SourceFile", os.path.join(dst, ROOT_XML), "-OutputFile", epf],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = result.returncode == 0 and os.path.exists(epf)
        print(version, "ok" if ok else "ОШИБКА СБОРКИ", epf)
        if not ok:
            print(result.stdout[-2000:], result.stderr[-2000:])


if __name__ == "__main__":
    main()
