#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild rev2_ЗначенияПараметровДоговораДУ from exact CF text for ИзменениеИКонтроль."""

base_path = (
    r"c:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF\InformationRegisters"
    r"\ЗначенияПараметровДоговораДУ\Ext\ManagerModule.bsl"
)
ext_path = (
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-8899 Вечерние регламенты Этап2\Расширения\rev2"
    r"\InformationRegisters\ЗначенияПараметровДоговораДУ\Ext\ManagerModule.bsl"
)

with open(base_path, "rb") as f:
    base = f.read().decode("utf-8-sig").splitlines()

header = base[12:28]
blank_before_insert = [base[28]]
query_setup = base[29:33]
blank_before_query_text = [base[33]]
query_old = base[34:54]
tail_delete = base[54:64]
tail_return = base[64:66]
tail_before_end = [base[66]]

insert_prefill = [
    "\t#Вставка",
    "\tДля Каждого Параметр Из МассивПараметров Цикл",
    "\t\tЗначенияПараметров.Вставить(Параметр, Неопределено);",
    "\tКонецЦикла;",
    "\t#КонецВставки",
]

insert_query = [
    "\t#Вставка",
    "\tЗапрос.Текст =",
    '\t"ВЫБРАТЬ',
    "\t|    Срез.Параметр КАК Параметр,",
    "\t|    Срез.Значение КАК Значение",
    "\t|ИЗ",
    "\t|    РегистрСведений.ЗначенияПараметровДоговораДУ.СрезПоследних(",
    "\t|            &Дата,",
    "\t|            ДоговорДУ = &ДоговорДУ",
    "\t|                И Параметр В (&Параметры)) КАК Срез\";",
    "\t#КонецВставки",
]

insert_tail = [
    "\t#Вставка",
    "   Выборка = Запрос.Выполнить().Выбрать();",
    "   ",
    "   Пока Выборка.Следующий() Цикл",
    "\t   ЗначенияПараметров.Вставить(Выборка.Параметр, Выборка.Значение);",
    "   КонецЦикла;",
    "\t#КонецВставки",
]

delete_query = ["\t#Удаление"] + query_old + ["\t#КонецУдаления"]
delete_tail = ["\t#Удаление"] + tail_delete + ["\t#КонецУдаления"]

body_lines = (
    header
    + blank_before_insert
    + insert_prefill
    + query_setup
    + blank_before_query_text
    + delete_query
    + insert_query
    + delete_tail
    + insert_tail
    + tail_return
    + tail_before_end
)

func_header = (
    "// IMDEV-8899 3.2: оптимизация единичного запроса — срез с фильтром "
    "вместо ПОМЕСТИТЬ + ЛЕВОЕ СОЕДИНЕНИЕ\n"
    "// Бенчмарк: 3000 договоров x 4 набора, 0 расхождений, -69% к текущему КФ\n"
    "\n"
    '&ИзменениеИКонтроль("ЗначенияПараметровДоговораДУ")\n'
    "Функция rev2_ЗначенияПараметровДоговораДУ"
    "(ДоговорДУ, Параметры, Знач Дата = '00010101') Экспорт\n"
)

with open(ext_path, "rb") as f:
    ext_content = f.read().decode("utf-8-sig")

rest_marker = "// Описание: Возвращает значения параметров по списку договоров"
rest_start = ext_content.find(rest_marker)
if rest_start < 0:
    raise SystemExit("rest section not found")
rest = ext_content[rest_start:]

new_func = func_header + "\n".join(body_lines) + "\nКонецФункции\n\n" + rest

with open(ext_path, "wb") as f:
    f.write(new_func.encode("utf-8"))

print("OK: rebuilt interceptor, body lines:", len(body_lines))
