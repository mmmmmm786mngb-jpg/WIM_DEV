#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка модуля менеджера расширения IM8663: перехваты из CF + новые процедуры.
"""

from pathlib import Path

CF = Path(r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF\Catalogs\РегламентныеПериоды\Ext\ManagerModule.bsl")
OUT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-8663 ВечернииРДУ_ВыносРасчетаСЧА_РСА_ВКонец"
    r"\Расширения\IM8663\Catalogs\РегламентныеПериоды\Ext\ManagerModule.bsl"
)

TAB = "\t"


def extract_proc(text: str, name: str) -> str:
    start = text.find(f"Процедура {name}(")
    if start < 0:
        raise SystemExit(f"Procedure not found: {name}")
    marker = "\n" + TAB + "КонецПроцедуры"
    end = text.find(marker, start)
    if end < 0:
        raise SystemExit(f"End not found: {name}")
    return text[start : end + len(marker)]


def patch_parent(src: str) -> str:
    src = src.replace(
        f"Процедура СформироватьРегламентныеОперации(",
        f'&ИзменениеИКонтроль("СформироватьРегламентныеОперации")\n'
        f"{TAB}Процедура IM8663_СформироватьРегламентныеОперации(",
        1,
    )

    needle_init = (
        f"{TAB}{TAB}{TAB}Если ПараметрыСохранения = Неопределено Или ТипЗнч(ПараметрыСохранения) <> Тип(\"Структура\") Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}Результат.Сообщение = НСтр(\"ru='Отсутствуют или некорректны параметры сохранения'\");\n"
        f"{TAB}{TAB}{TAB}{TAB}ПоместитьВоВременноеХранилище(Результат, АдресХранилищаРезультат);\n"
        f"{TAB}{TAB}{TAB}{TAB}Возврат;\n"
        f"{TAB}{TAB}{TAB}КонецЕсли;\n"
    )
    insert_init = needle_init + (
        f"\n"
        f"{TAB}{TAB}{TAB}#Вставка\n"
        f"{TAB}{TAB}{TAB}// IMDEV-8663.1.A\n"
        f"{TAB}{TAB}{TAB}ФоновыеЗаданияДоступны = ПараметрыСохранения.КоличествоПотоков > 0\n"
        f"{TAB}{TAB}{TAB}{TAB}И ФоновыеЗаданияСервер.ФоновыеЗаданияРазрешены();\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Вставить(\"ФоновыеЗаданияДоступны\", ФоновыеЗаданияДоступны);\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Вставить(\"УспешныхЗаданий\", 0);\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Вставить(\"ОшибокЗаданий\", 0);\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Вставить(\"ПроблемныеДоговоры\", Новый Массив);\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Вставить(\"РазмерЧанкаПоУИД\", Новый Соответствие);\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Вставить(\"IM8663_НачалоРасчетаМС\",\n"
        f"{TAB}{TAB}{TAB}{TAB}ТекущаяУниверсальнаяДатаВМиллисекундах());\n"
        f"{TAB}{TAB}{TAB}// IMDEV-8663.1.B\n"
        f"{TAB}{TAB}{TAB}РазмерЧанка = IM8663_ПолучитьЧисловуюКонстанту(\n"
        f"{TAB}{TAB}{TAB}{TAB}\"МаксимальныйРазмерПорцииДоговоровВПотокеРегл\", 50);\n"
        f"{TAB}{TAB}{TAB}Если РазмерЧанка < 1 Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}РазмерЧанка = 1;\n"
        f"{TAB}{TAB}{TAB}КонецЕсли;\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Вставить(\"РазмерЧанка\", РазмерЧанка);\n"
        f"{TAB}{TAB}{TAB}#КонецВставки\n"
    )
    if needle_init not in src:
        raise SystemExit("init needle not found")
    src = src.replace(needle_init, insert_init, 1)

    needle_batch = f"{TAB}{TAB}{TAB}РазмерПачки         = 3000; // IMDEV-8926\n"
    insert_batch = (
        f"{TAB}{TAB}{TAB}#Удаление\n"
        f"{TAB}{TAB}{TAB}РазмерПачки         = 3000; // IMDEV-8926\n"
        f"{TAB}{TAB}{TAB}#КонецУдаления\n"
        f"{TAB}{TAB}{TAB}#Вставка\n"
        f"{TAB}{TAB}{TAB}// IMDEV-8663.1.B\n"
        f"{TAB}{TAB}{TAB}РазмерПачки = IM8663_ПолучитьЧисловуюКонстанту(\n"
        f"{TAB}{TAB}{TAB}{TAB}\"МаксимальныйРазмерПачкиДоговоровДляПредварительногоЗапросаРегл\", 3000);\n"
        f"{TAB}{TAB}{TAB}Если РазмерПачки < 1 Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}РазмерПачки = 1;\n"
        f"{TAB}{TAB}{TAB}КонецЕсли;\n"
        f"{TAB}{TAB}{TAB}#КонецВставки\n"
    )
    if needle_batch not in src:
        raise SystemExit("batch size needle not found")
    src = src.replace(needle_batch, insert_batch, 1)

    loop_start = (
        f"{TAB}{TAB}{TAB}{TAB}// ASP-206799 IMDEV-8926: цикл по договорам текущей пачки (в типовой - по всему СписокДоговоровДУ)\n"
        f"{TAB}{TAB}{TAB}{TAB}Для Каждого ТекДоговор Из СписокПачки Цикл // IMDEV-8926\n"
    )
    loop_end = f"{TAB}{TAB}{TAB}{TAB}КонецЦикла; // IMDEV-8926: конец цикла по договорам пачки\n"
    i0 = src.find(loop_start)
    i1 = src.find(loop_end, i0)
    if i0 < 0 or i1 < 0:
        raise SystemExit("batch loop not found")
    i1 += len(loop_end)
    old_loop = src[i0:i1]
    new_loop = (
        f"{TAB}{TAB}{TAB}{TAB}#Удаление\n"
        + old_loop
        + f"{TAB}{TAB}{TAB}{TAB}#КонецУдаления\n"
        f"{TAB}{TAB}{TAB}{TAB}#Вставка\n"
        f"{TAB}{TAB}{TAB}{TAB}// IMDEV-8663.1.B\n"
        f"{TAB}{TAB}{TAB}{TAB}Если ПараметрыСохранения.ФоновыеЗаданияДоступны Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}IM8663_ОбработатьПачкуДиспетчером(\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ДатаПериода,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}СписокПачки,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}УчитыватьВыполненные,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}НаименованиеФоновогоЗадания,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ПараметрыСохранения,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ТекущийНомер,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}КоличествоДоговоров,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ИндексПачки);\n"
        f"{TAB}{TAB}{TAB}{TAB}Иначе\n"
        + old_loop.replace(TAB * 4, TAB * 5, 1).replace(
            f"\n{TAB}{TAB}{TAB}{TAB}", f"\n{TAB}{TAB}{TAB}{TAB}{TAB}"
        )
        + f"{TAB}{TAB}{TAB}{TAB}КонецЕсли;\n"
        f"{TAB}{TAB}{TAB}{TAB}// IMDEV-8663.1.A\n"
        f"{TAB}{TAB}{TAB}{TAB}IM8663_ЗавершитьФоновыеЗаданияПорции(ПараметрыСохранения);\n"
        f"{TAB}{TAB}{TAB}{TAB}#КонецВставки\n"
    )
    # The else-branch indent rewrite is fragile. Keep original loop indent inside Else as-is
    # (1C allows extra/missing indent). Use original loop unchanged inside Else.
    new_loop = (
        f"{TAB}{TAB}{TAB}{TAB}#Удаление\n"
        + old_loop
        + f"{TAB}{TAB}{TAB}{TAB}#КонецУдаления\n"
        f"{TAB}{TAB}{TAB}{TAB}#Вставка\n"
        f"{TAB}{TAB}{TAB}{TAB}// IMDEV-8663.1.B\n"
        f"{TAB}{TAB}{TAB}{TAB}Если ПараметрыСохранения.ФоновыеЗаданияДоступны Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}IM8663_ОбработатьПачкуДиспетчером(\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ДатаПериода,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}СписокПачки,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}УчитыватьВыполненные,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}НаименованиеФоновогоЗадания,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ПараметрыСохранения,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ТекущийНомер,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}КоличествоДоговоров,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}{TAB}ИндексПачки);\n"
        f"{TAB}{TAB}{TAB}{TAB}Иначе\n"
        + "".join(TAB + line if line.strip() else line for line in old_loop.splitlines(True))
        + f"{TAB}{TAB}{TAB}{TAB}КонецЕсли;\n"
        f"{TAB}{TAB}{TAB}{TAB}// IMDEV-8663.1.A\n"
        f"{TAB}{TAB}{TAB}{TAB}IM8663_ЗавершитьФоновыеЗаданияПорции(ПараметрыСохранения);\n"
        f"{TAB}{TAB}{TAB}{TAB}#КонецВставки\n"
    )
    src = src[:i0] + new_loop + src[i1:]

    needle_fin = (
        f"{TAB}{TAB}{TAB}// Финальное сообщение о завершении и фиксация успешного результата\n"
        f"{TAB}{TAB}{TAB}ДлительныеОперации.СообщитьПрогресс(\n"
        f"{TAB}{TAB}{TAB}100,\n"
        f"{TAB}{TAB}{TAB}НСтр(\"ru='Формирование регламентных операций завершено'\"));\n"
        f"{TAB}{TAB}{TAB}\n"
        f"{TAB}{TAB}{TAB}Результат.Успешно   = Истина;\n"
        f"{TAB}{TAB}{TAB}Результат.Сообщение = \"\";\n"
    )
    insert_fin = (
        f"{TAB}{TAB}{TAB}#Вставка\n"
        f"{TAB}{TAB}{TAB}// IMDEV-8663.1.A\n"
        f"{TAB}{TAB}{TAB}IM8663_ЗавершитьФоновыеЗаданияПорции(ПараметрыСохранения);\n"
        f"{TAB}{TAB}{TAB}НачалоРасчетаМС = 0;\n"
        f"{TAB}{TAB}{TAB}ПараметрыСохранения.Свойство(\"IM8663_НачалоРасчетаМС\", НачалоРасчетаМС);\n"
        f"{TAB}{TAB}{TAB}ДлительностьСек = 0;\n"
        f"{TAB}{TAB}{TAB}Если НачалоРасчетаМС > 0 Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}ДлительностьСек = Цел(\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}(ТекущаяУниверсальнаяДатаВМиллисекундах() - НачалоРасчетаМС) / 1000);\n"
        f"{TAB}{TAB}{TAB}КонецЕсли;\n"
        f"{TAB}{TAB}{TAB}МинутРасчета = Цел(ДлительностьСек / 60);\n"
        f"{TAB}{TAB}{TAB}СекундРасчета = ДлительностьСек - МинутРасчета * 60;\n"
        f"{TAB}{TAB}{TAB}ТекстВремени = СтрШаблон(\n"
        f"{TAB}{TAB}{TAB}{TAB}НСтр(\"ru='%1 мин %2 сек'\"),\n"
        f"{TAB}{TAB}{TAB}{TAB}Формат(МинутРасчета, \"ЧН=0; ЧГ=\"),\n"
        f"{TAB}{TAB}{TAB}{TAB}Формат(СекундРасчета, \"ЧН=0; ЧГ=\"));\n"
        f"{TAB}{TAB}{TAB}Если ПараметрыСохранения.ФоновыеЗаданияДоступны Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}ТекстСводки = СтрШаблон(\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}НСтр(\"ru='Обработано договоров: %1. Успешных заданий: %2, с ошибкой: %3. Затрачено: %4'\"),\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}КоличествоДоговоров,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}ПараметрыСохранения.УспешныхЗаданий,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}ПараметрыСохранения.ОшибокЗаданий,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}ТекстВремени);\n"
        f"{TAB}{TAB}{TAB}Иначе\n"
        f"{TAB}{TAB}{TAB}{TAB}ТекстСводки = СтрШаблон(\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}НСтр(\"ru='Обработано договоров: %1. Режим: последовательно, без фоновых. Затрачено: %2'\"),\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}КоличествоДоговоров,\n"
        f"{TAB}{TAB}{TAB}{TAB}{TAB}ТекстВремени);\n"
        f"{TAB}{TAB}{TAB}КонецЕсли;\n"
        f"{TAB}{TAB}{TAB}Если ПараметрыСохранения.ПроблемныеДоговоры.Количество() > 0 Тогда\n"
        f"{TAB}{TAB}{TAB}{TAB}ТекстСводки = ТекстСводки + \". \" + СтрСоединить(ПараметрыСохранения.ПроблемныеДоговоры, \"; \");\n"
        f"{TAB}{TAB}{TAB}КонецЕсли;\n"
        f"{TAB}{TAB}{TAB}Сообщить(ТекстСводки);\n"
        f"{TAB}{TAB}{TAB}#КонецВставки\n"
        + needle_fin.replace(
            f"{TAB}{TAB}{TAB}Результат.Сообщение = \"\";\n",
            f"{TAB}{TAB}{TAB}#Удаление\n"
            f"{TAB}{TAB}{TAB}Результат.Сообщение = \"\";\n"
            f"{TAB}{TAB}{TAB}#КонецУдаления\n"
            f"{TAB}{TAB}{TAB}#Вставка\n"
            f"{TAB}{TAB}{TAB}// IMDEV-8663.1.A\n"
            f"{TAB}{TAB}{TAB}Результат.Сообщение = ТекстСводки;\n"
            f"{TAB}{TAB}{TAB}#КонецВставки\n",
        )
    )
    if needle_fin not in src:
        raise SystemExit("final needle not found")
    src = src.replace(needle_fin, insert_fin, 1)

    needle_exc = (
        f"{TAB}{TAB}Исключение\n"
        f"{TAB}{TAB}{TAB}\n"
        f"{TAB}{TAB}{TAB}// ASP-207844 IMDEV-8927: завершение замера при ошибке (вес не дублируем)\n"
    )
    insert_exc = (
        f"{TAB}{TAB}Исключение\n"
        f"{TAB}{TAB}{TAB}\n"
        f"{TAB}{TAB}{TAB}#Вставка\n"
        f"{TAB}{TAB}{TAB}// IMDEV-8663.1.A\n"
        f"{TAB}{TAB}{TAB}IM8663_ОтменитьАктивныеЗадания(ПараметрыСохранения);\n"
        f"{TAB}{TAB}{TAB}#КонецВставки\n"
        f"{TAB}{TAB}{TAB}\n"
        f"{TAB}{TAB}{TAB}// ASP-207844 IMDEV-8927: завершение замера при ошибке (вес не дублируем)\n"
    )
    if needle_exc not in src:
        raise SystemExit("exception needle not found")
    src = src.replace(needle_exc, insert_exc, 1)
    return src


def patch_docs(src: str) -> str:
    src = src.replace(
        "Процедура СформироватьДокументыЗакрытияПериода(",
        '&ИзменениеИКонтроль("СформироватьДокументыЗакрытияПериода")\n'
        f"{TAB}Процедура IM8663_СформироватьДокументыЗакрытияПериода(",
        1,
    )

    key = "Если КоличествоПотоков > 0 И ФоновыеЗаданияСервер.ФоновыеЗаданияРазрешены() Тогда"
    pos = src.find(key)
    if pos < 0:
        raise SystemExit("bg if not found")
    line0 = src.rfind("\n", 0, pos) + 1
    sync_marker = (
        "СоответствиеОперацияТаблица); // ASP-197909 IMAPPS-35037++ "
        "Добавлен параметр СоответствиеОперацияТаблица"
    )
    m1 = src.find(sync_marker, pos)
    if m1 < 0:
        raise SystemExit("sync call marker not found")
    endif_pos = src.find("КонецЕсли;", m1)
    if endif_pos < 0:
        raise SystemExit("endif after sync call not found")
    line2 = src.find("\n", endif_pos) + 1
    old_block = src[line0:line2]

    indent = TAB * 4
    new_block = (
        f"{indent}#Удаление\n"
        + old_block
        + f"{indent}#КонецУдаления\n"
        f"{indent}#Вставка\n"
        f"{indent}// IMDEV-8663.1.A\n"
        f"{indent}// Удалена неиспользуемая ветка \"один договор = одно фоновое задание\":\n"
        f"{indent}// запуск ФоновыеЗадания.Выполнить(СоздатьПланРегламентныхОперацийДУ)\n"
        f"{indent}// и ожидание порции внутри этой процедуры. Сюда больше не заходят:\n"
        f"{indent}// диспетчер вызывает процедуру с КоличествоПотоков = 0 и\n"
        f"{indent}// ФоновыеЗаданияДоступны = Ложь; последовательный путь родителя уже\n"
        f"{indent}// идёт при ФоновыеЗаданияДоступны = Ложь. Параллельность только у\n"
        f"{indent}// диспетчера чанков. Остаётся синхронный вызов, как в Иначе типовой.\n"
        f"{indent}ФоновыеЗаданияСервер.СоздатьПланРегламентныхОперацийДУ(\n"
        f"{indent}ДатаПериода,\n"
        f"{indent}ДоговорДУ,\n"
        f"{indent}ТаблицаОпераций,\n"
        f"{indent}ТекПлан,\n"
        f"{indent}ТекГруппаОперацийПользователя,\n"
        f"{indent}УчитыватьВыполненные,\n"
        f"{indent}СоответствиеОперацияТаблица); // ASP-197909 IMAPPS-35037++ Добавлен параметр СоответствиеОперацияТаблица\n"
        f"{indent}#КонецВставки\n"
    )
    return src[:line0] + new_block + src[line2:]


def main():
    raw = CF.read_text(encoding="utf-8-sig")
    parent = extract_proc(raw, "СформироватьРегламентныеОперации")
    docs = extract_proc(raw, "СформироватьДокументыЗакрытияПериода")
    docs = patch_docs(docs)

    parent = patch_parent(parent)
    extra = Path(__file__).with_name("new_procedures.bsl").read_text(encoding="utf-8")

    out = (
        "// IMDEV-8663.1 фоновые задания регламентных операций\n\n"
        f"{TAB}#Область IMDEV_8663_1_A\n\n"
        f"{TAB}{parent}\n\n"
        f"{TAB}{docs}\n\n"
        f"{extra}"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8-sig", newline="\r\n")
    print("OK", OUT)


if __name__ == "__main__":
    main()
