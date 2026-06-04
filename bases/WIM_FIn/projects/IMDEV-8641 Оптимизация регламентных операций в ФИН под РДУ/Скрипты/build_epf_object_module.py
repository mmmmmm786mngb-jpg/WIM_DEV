#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sbor ObjectModule.bsl EPF iz ManagerModule RduPF.

Struktura vyhodnogo modulya (kak v tekushchem ObjectModule.bsl):
  #Obласть ПрограммныйИнтерфейс  — iz skeleton (EPF-karkas, poryadok vetok ne trogat)
  #Obласть СлужебныеПроцедурыИФункции
    ПроверитьСовместимость, zaglushki-kommentarii, ПриФормировании..., ТаблицаОптимизируемых...
    #Obласть Отбор... + #Obласть Фильтрация... — iz RduPF ManagerModule (s patchami EPF)
  #КонецОбласти

Ne dublirovat telo iz skeleton: hvost beretsya tolko odin raz (#КонецОбласти Служебные).
"""

from pathlib import Path

PROJECT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects"
    r"\IMDEV-8641 Оптимизация регламентных операций в ФИН под РДУ"
)
SKELETON = PROJECT / "ДоработкиОтАванкор/АлгоритмДопДействийПриЗакрытииДня/Ext/ObjectModule.bsl"
SOURCE = (
    PROJECT
    / "Расширения/RduPF/InformationRegisters/ВидыОптимизируемыхРегламентныхОперацийДУ/Ext/ManagerModule.bsl"
)
OUT = SKELETON

RS_JOIN_OLD = (
    "    |        ВНУТРЕННЕЕ СОЕДИНЕНИЕ РегистрСведений.ВидыОптимизируемыхРегламентныхОперацийДУ КАК ОптВиды\n"
    "    |        ПО План.ВидОперации = ОптВиды.ВидОперации"
)
RS_JOIN_NEW = (
    "    |        ВНУТРЕННЕЕ СОЕДИНЕНИЕ ВТ_ОптВиды КАК ОптВиды\n"
    "    |        ПО План.ВидОперации = ОптВиды.ВидОперации"
)
VT_OPT_INSERT = (
    "    |////////////////////////////////////////////////////////////////////////////////\n"
    "    |ВЫБРАТЬ\n"
    "    |    ОптВиды.ВидОперации КАК ВидОперации\n"
    "    |ПОМЕСТИТЬ ВТ_ОптВиды\n"
    "    |ИЗ\n"
    "    |    &ТаблицаОптВиды КАК ОптВиды\n"
    "    |;\n"
    "    |\n"
)

HELPERS = """// Описание: Таблица из пяти предопределенных видов операций для пакета запроса свода (IMDEV-8641, EPF).
//           Список видов зашит в обработке; параметр &ТаблицаОптВиды, ВТ_ОптВиды в запросе свода.
//
// Возвращаемое значение:
//  ТаблицаЗначений - колонка ВидОперации (СправочникСсылка.ВидыОперацийЗакрытияПериода)
//
Функция ТаблицаОптимизируемыхВидовОпераций()

    ТаблицаВидов = Новый ТаблицаЗначений;
    ТаблицаВидов.Колонки.Добавить(
        "ВидОперации",
        Новый ОписаниеТипов("СправочникСсылка.ВидыОперацийЗакрытияПериода"));

    СтрокаВида = ТаблицаВидов.Добавить();
    СтрокаВида.ВидОперации = Справочники.ВидыОперацийЗакрытияПериода.НачислениеПроцентовПоБанковскимСчетамПоГрафику;

    СтрокаВида = ТаблицаВидов.Добавить();
    СтрокаВида.ВидОперации = Справочники.ВидыОперацийЗакрытияПериода.ПереводНКДЭмитента_БУ;

    СтрокаВида = ТаблицаВидов.Добавить();
    СтрокаВида.ВидОперации = Справочники.ВидыОперацийЗакрытияПериода.ОпределениеСделокСОтклонениемЦен_БУ;

    СтрокаВида = ТаблицаВидов.Добавить();
    СтрокаВида.ВидОперации = Справочники.ВидыОперацийЗакрытияПериода.ПогашениеОблигаций_БУ_ДоПереоценки;

    СтрокаВида = ТаблицаВидов.Добавить();
    СтрокаВида.ВидОперации = Справочники.ВидыОперацийЗакрытияПериода.ЧастичноеПогашениеОблигаций_БУ;

    Возврат ТаблицаВидов;

КонецФункции

"""

PRI_FORM_HEADER = """// Описание: Фильтрация плана регламентных операций на день (IMDEV-8641, EPF Аванкор).
// Параметры:
//  ПараметрыОбработки - Структура - Дата, ПланРегламентныхОпераци
//  Отказ - Булево
//
Процедура ПриФормированииПланаРегламентныхОперацийЗаДень(ПараметрыОбработки, Отказ = Ложь)

    День = ПараметрыОбработки.Дата;
    тПланРеглОперацийПоДням = ПараметрыОбработки.ПланРегламентныхОпераци;

    ОтфильтроватьПланРеглОперацийНаДень(День, тПланРеглОперацийПоДням);

КонецПроцедуры

"""

SERVICE_STUBS = (
    "// Перед выполнением всех регламентных операций по портфелю\n\n"
    "// После выполнения всех регламентных операций по портфелю\n"
    "// ...\n\n"
    "// Перед выполнением всех регламентных операций\n"
    "// ...\n\n"
    "// После выполнения всех регламентных операций \n\n"
)

TAIL_CLOSE_SERVICE = "#КонецОбласти\n"


def extract_program_interface(lines: list[str]) -> str:
    """Do #КонецОбластi posle ВыполнитьДополнительныеДействия (karkas EPF)."""
    head_end = 0
    for i, line in enumerate(lines):
        if line.strip() == "#КонецОбласти" and i > 30:
            head_end = i + 1
            break
    if head_end == 0:
        raise RuntimeError("ProgrammnyyInterfeys: #КонецОбласти not found")
    return "".join(lines[:head_end])


def extract_proverit_sovmestimost(lines: list[str]) -> str:
    start = None
    for i, line in enumerate(lines):
        if "Функция ПроверитьСовместимость" in line:
            start = i
            break
    if start is None:
        raise RuntimeError("ПроверитьСовместимость not found in skeleton")
    end = None
    for i in range(start, len(lines)):
        if lines[i].strip() == "КонецФункции":
            end = i + 1
            break
    if end is None:
        raise RuntimeError("КонецФункции for ПроверитьСовместимость not found")
    return "".join(lines[start:end]) + "\n"


def extract_service_prefix(lines: list[str]) -> str:
    """
    Sluzhebnaya chast do #Область Отбор...: ne vklyuchat telo iz RduPF.
    Esli v skeleton uzhe est polnyy modul — sрез do Otbor.
    Esli tolko karkas — sobiraem iz Проверить + zaglushki + PRI_FORM + HELPERS.
    """
    area_start = None
    otbor_start = None
    for i, line in enumerate(lines):
        if "#Область СлужебныеПроцедурыИФункции" in line:
            area_start = i
        if "#Область ОтборПортфелейДляСохраненияВыполненияВПлане" in line:
            otbor_start = i
            break

    if area_start is None:
        raise RuntimeError("#Область СлужебныеПроцедурыИФункции not found")

    if otbor_start is not None:
        return "".join(lines[area_start:otbor_start])

    # Karkas bez perenosa: #Область Служебные + Проверить + stub + PRI + Tablica
    return (
        lines[area_start]
        + "\n"
        + extract_proverit_sovmestimost(lines)
        + SERVICE_STUBS
        + PRI_FORM_HEADER
        + HELPERS
    )


def transform_rdu_body(source_lines: list[str]) -> str:
    """Stroki 25-1191 ManagerModule: oblasti Otbor i Filtratsiya."""
    body = "".join(source_lines[24:1191])
    body = body.replace(") Экспорт\n", ")\n")
    body = body.replace(RS_JOIN_OLD, RS_JOIN_NEW)

    marker = (
        "    |ПОМЕСТИТЬ ВТ_План\n"
        "    |ИЗ\n"
        "    |    &ТаблицаПлана КАК План\n"
        "    |;\n"
        "    |\n"
    )
    if marker not in body:
        raise RuntimeError("VT insert marker not found in RduPF source")
    body = body.replace(marker, marker + VT_OPT_INSERT, 1)

    param_marker = (
        '    ЗапросСвод.УстановитьПараметр("ТаблицаПлана", тПланРеглОперацийПоДням);\n\n'
        "    ЗапросСвод.Текст ="
    )
    param_new = (
        '    ЗапросСвод.УстановитьПараметр("ТаблицаПлана", тПланРеглОперацийПоДням);\n'
        '    ЗапросСвод.УстановитьПараметр("ТаблицаОптВиды", ТаблицаОптимизируемыхВидовОпераций());\n\n'
        "    ЗапросСвод.Текст ="
    )
    if param_marker not in body:
        raise RuntimeError("param marker not found in RduPF source")
    body = body.replace(param_marker, param_new, 1)

    body = body.replace(
        "// Пример:\n"
        "//  РегистрыСведений.ВидыОптимизируемыхРегламентныхОперацийДУ.ОтфильтроватьПланРеглОперацийНаДень(\n"
        "//      День, тПланРеглОперацийПоДням);\n",
        "// Пример (вызов из события EPF «ПриФормированииПланаРегламентныхОперацийЗаДень»):\n"
        "//  ОтфильтроватьПланРеглОперацийНаДень(ПараметрыОбработки.Дата, ПараметрыОбработки.ПланРегламентныхОпераци);\n",
    )
    body = body.replace(
        "    //        План помещается во ВТ_План; допустимые ключи: по Выполнять = 1 и регистру оптимизируемых видов.\n",
        "    //        План помещается во ВТ_План; допустимые ключи: по Выполнять = 1 и пяти видам из ТаблицаОптимизируемыхВидовОпераций (ВТ_ОптВиды).\n",
    )

    return body


def main():
    skeleton_lines = SKELETON.read_text(encoding="utf-8").splitlines(keepends=True)
    source_lines = SOURCE.read_text(encoding="utf-8").splitlines(keepends=True)

    head = extract_program_interface(skeleton_lines)
    service_prefix = extract_service_prefix(skeleton_lines)
    body = transform_rdu_body(source_lines)

    out_text = head + service_prefix + body + TAIL_CLOSE_SERVICE
    OUT.write_text(out_text, encoding="utf-8")
    print("OK lines:", len(out_text.splitlines()))


if __name__ == "__main__":
    main()
