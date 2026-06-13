#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild rev2_СформироватьДокументыЗакрытияПериода from CF 1.5.28.9 for ИзменениеИКонтроль."""

base_path = (
    r"c:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF\Catalogs\РегламентныеПериоды\Ext\ManagerModule.bsl"
)
ext_path = (
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-8899 Вечерние регламенты Этап2\Расширения\rev2"
    r"\Catalogs\РегламентныеПериоды\Ext\ManagerModule.bsl"
)

with open(base_path, "rb") as f:
    base = f.read().decode("utf-8-sig").splitlines()

proc_start = next(
    i for i, line in enumerate(base) if "Процедура СформироватьДокументыЗакрытияПериода" in line
)
proc_end = next(
    i for i in range(proc_start + 1, len(base)) if base[i].startswith("КонецПроцедуры")
)

# Body inside procedure: from first tab line after signature through blank before КонецПроцедуры
body_start = proc_start + 1
body_end = proc_end
body = base[body_start:body_end]

# Split points (indices in body list, 0 = body_start in file)
idx_after_cache = next(i for i, line in enumerate(body) if line == "\t// IMAPPS-35039--" and i > 50)
idx_before_0110_delete = next(
    i
    for i, line in enumerate(body)
    if "Операция 0110" in line and "переоценка активов" in line and "передаём кэш" in line
)
idx_after_0110_delete = next(
    i
    for i in range(idx_before_0110_delete, len(body))
    if body[i] == "\t// IMAPPS-35039--\t" or body[i].rstrip("\t") == "\t// IMAPPS-35039--"
)
# normalize: use exact line from base at idx_after_0110_delete
idx_after_0110_delete = next(
    i
    for i in range(idx_before_0110_delete, len(body))
    if body[i].startswith("\t// IMAPPS-35039--")
)

insert_propusk = [
    "\t#Вставка",
    "\t// IMDEV-8899 3.1",
    "\tСоответствиеПропускРЕПОВетки = Неопределено;",
    '\tПараметрыСохранения.Свойство("СоответствиеПропускРЕПОВетки", СоответствиеПропускРЕПОВетки);',
    "\t#КонецВставки",
]

delete_0110 = ["\t#Удаление"] + body[idx_before_0110_delete : idx_after_0110_delete + 1] + ["\t#КонецУдаления"]

insert_0110 = [
    "\t#Вставка",
    "\t// IMAPPS-35039++ Операция 0110 — переоценка активов: кэш котировок УУ и соответствие ПропускРЕПОВетки",
    "\t// IMDEV-8899 3.1",
    "\tЕсли КэшПоДоговоруКотировокУУ <> Неопределено Или СоответствиеПропускРЕПОВетки <> Неопределено Тогда",
    "\t\tДополнительныеДанныеОперации0110 = Новый Структура;",
    "\t\tЕсли КэшПоДоговоруКотировокУУ <> Неопределено Тогда",
    '\t\t\tДополнительныеДанныеОперации0110.Вставить("КэшКотировокУУ", КэшПоДоговоруКотировокУУ);',
    "\t\tКонецЕсли;",
    "\t\tЕсли СоответствиеПропускРЕПОВетки <> Неопределено Тогда",
    '\t\t\tДополнительныеДанныеОперации0110.Вставить("СоответствиеПропускРЕПОВетки", СоответствиеПропускРЕПОВетки);',
    "\t\tКонецЕсли;",
    "\t\tСоответствиеОперацияТаблица.Вставить(",
    '\t\t\t"ИсполняемыеПроцедурыЗакрытияПериода.Операция_0110_ПереоценкаАктивов",',
    "\t\t\tДополнительныеДанныеОперации0110);",
    "\tКонецЕсли;",
    "\t// IMAPPS-35039--",
    "\t#КонецВставки",
]

new_body = (
    body[: idx_after_cache + 1]
    + insert_propusk
    + body[idx_after_cache + 1 : idx_before_0110_delete]
    + delete_0110
    + insert_0110
    + body[idx_after_0110_delete + 1 :]
)

func_header = (
    "&ИзменениеИКонтроль(\"СформироватьДокументыЗакрытияПериода\")\n"
    "Процедура rev2_СформироватьДокументыЗакрытияПериода"
    "(ДатаПериода, ДоговорДУ, УчитыватьВыполненные, НаименованиеФоновогоЗадания, "
    "ТекЗначение, МаксимальноеЗначение, ПараметрыСохранения)\n"
)

new_proc = func_header + "\n".join(new_body) + "\n" + base[proc_end] + "\n"

with open(ext_path, "rb") as f:
    ext = f.read().decode("utf-8-sig")

marker_start = "&ИзменениеИКонтроль(\"СформироватьДокументыЗакрытияПериода\")"
marker_end = "&ИзменениеИКонтроль(\"ОчиститьПакетныеДанныеПараметрыСохранения\")"

start = ext.find(marker_start)
end = ext.find(marker_end)
if start < 0 or end < 0:
    raise SystemExit("markers not found in extension file")

new_ext = ext[:start] + new_proc + "\n" + ext[end:]

with open(ext_path, "wb") as f:
    f.write(new_ext.encode("utf-8"))

# verify reconstruction
out = []
i = 0
while i < len(new_body):
    s = new_body[i].strip()
    if s == "#Вставка":
        while i < len(new_body) and new_body[i].strip() != "#КонецВставки":
            i += 1
        i += 1
        continue
    if s == "#Удаление":
        i += 1
        while i < len(new_body) and new_body[i].strip() != "#КонецУдаления":
            out.append(new_body[i])
            i += 1
        i += 1
        continue
    out.append(new_body[i])
    i += 1

print("OK: rebuilt interceptor")
print("Reconstruct match:", out == body)
if out != body:
    for j, (a, e) in enumerate(zip(body, out)):
        if a != e:
            print("diff", j + 1, repr(a)[:100], "|", repr(e)[:100])
    if len(body) != len(out):
        print("length", len(body), len(out))
