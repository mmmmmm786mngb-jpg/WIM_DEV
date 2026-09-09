#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate IM86632 stage 3-4 modules from CF 1.5.29.11 bodies and verified anchors."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
EXT = PROJECT / "Расширения" / "IM86632"
CF = Path(r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF")

PREFIX = "IM86632_"


def load_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(bytes([0xEF, 0xBB, 0xBF])):
        raw = raw[3:]
    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def write_bsl(path: Path, text: str) -> None:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


def must_count(text: str, marker: str, label: str, expected: int = 1) -> None:
    n = text.count(marker)
    if n != expected:
        raise SystemExit(f"{label}: expected {expected}, got {n}")


def extract_method(text: str, name: str) -> str:
    pat = re.compile(
        rf"^(?P<indent>\t*)(?P<kind>Процедура|Функция) {re.escape(name)}\(",
        re.M,
    )
    match = pat.search(text)
    if not match:
        raise SystemExit(f"method not found: {name}")
    kind = match.group("kind")
    indent = match.group("indent")
    end_kw = "КонецПроцедуры" if kind == "Процедура" else "КонецФункции"
    end_pat = re.compile(rf"^{re.escape(indent)}{end_kw}", re.M)
    end_match = end_pat.search(text, match.end())
    if not end_match:
        raise SystemExit(f"end not found: {name}")
    end = end_match.end()
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[match.start() : end]


def make_intercept(body: str, orig_name: str, stage: str, extra_sig: tuple[str, str] | None = None) -> str:
    indent = re.match(r"(\t*)", body).group(1)
    body2 = re.sub(
        rf"^(?P<ind>\t*)(?P<kind>Процедура|Функция) {re.escape(orig_name)}\(",
        rf"\g<ind>\g<kind> {PREFIX}{orig_name}(",
        body,
        count=1,
        flags=re.M,
    )
    if extra_sig is not None:
        old, new = extra_sig
        must_count(body2, old, f"signature {orig_name}")
        body2 = body2.replace(old, new, 1)
    return (
        f"{indent}// IMDEV-8663.2 этап {stage}\n"
        f"{indent}&ИзменениеИКонтроль(\"{orig_name}\")\n"
        + body2
    )


def find_string_assignment_end(text: str, start: int) -> int:
    quote = text.find('"', start)
    if quote < 0:
        raise SystemExit("string assignment: opening quote not found")
    i = quote + 1
    n = len(text)
    while i < n:
        if text[i] == '"':
            if i + 1 < n and text[i + 1] == '"':
                i += 2
                continue
            j = i + 1
            while j < n and text[j] in " \t":
                j += 1
            if j < n and text[j] == ";":
                j += 1
                while j < n and text[j] in " \t":
                    j += 1
                return j
            i += 1
            continue
        i += 1
    raise SystemExit("string assignment: unterminated")


def extract_query_literal(text: str, start_marker: str, label: str) -> str:
    must_count(text, start_marker, label)
    start = text.find(start_marker)
    end = find_string_assignment_end(text, start)
    chunk = text[start:end]
    q1 = chunk.find('"')
    q2 = chunk.rfind('"')
    if q1 < 0 or q2 <= q1:
        raise SystemExit(f"{label}: quotes not found")
    return chunk[q1 : q2 + 1]


def reindent_literal(literal: str, indent: str = "        ") -> str:
    lines = literal.split("\n")
    out = []
    for idx, line in enumerate(lines):
        if idx == 0:
            out.append(indent + line.lstrip(" \t"))
        else:
            out.append(indent + line.lstrip(" \t"))
    return "\n".join(out)


def wrap_assignment(text: str, start_marker: str, replacement: str, label: str) -> str:
    must_count(text, start_marker, label)
    start = text.find(start_marker)
    end = find_string_assignment_end(text, start)
    old = text[start:end]
    indent = re.match(r"[ \t]*", start_marker).group(0)
    wrapped = (
        f"{indent}#Удаление\n"
        f"{old}\n"
        f"{indent}#КонецУдаления\n"
        f"{indent}#Вставка\n"
        f"{indent}// IMDEV-8663.2 этап 4: те же конструкторы, что и пакетный путь (АР-4)\n"
        f"{replacement.rstrip()}\n"
        f"{indent}#КонецВставки"
    )
    return text[:start] + wrapped + text[end:]


def insert_after(text: str, marker: str, insertion: str, label: str) -> str:
    must_count(text, marker, label)
    return text.replace(marker, marker + insertion, 1)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    must_count(text, old, label)
    return text.replace(old, new, 1)


def make_query_func(func_name: str, description: str, literal: str) -> str:
    reindented = reindent_literal(literal, "        ")
    return (
        f"// Описание: {description}\n"
        f"//\n"
        f"// Возвращаемое значение:\n"
        f"//  Строка - текст запроса\n"
        f"//\n"
        f"Функция {func_name}()\n"
        f"\n"
        f"    // IMDEV-8663.2 этап 4\n"
        f"    Возврат\n"
        f"{reindented};\n"
        f"\n"
        f"КонецФункции\n"
    )


def patch_catalog_manager(cf_text: str) -> str:
    names = [
        ("СформироватьРегламентныеОперации", "3"),
        ("ОчиститьПакетныеДанныеПараметрыСохранения", "3"),
        ("СформироватьДокументыЗакрытияПериода", "3"),
        ("ОбработатьПачкуДиспетчером", "3"),
    ]
    intercepts = []
    for name, stage in names:
        body = extract_method(cf_text, name)
        intercepts.append((name, stage, make_intercept(body, name, stage)))

    by_name = {name: text for name, _stage, text in intercepts}

    evening_marker = (
        "\t\t\t\t\t\t\tЗаполнитьПараметрыСохраненияПакетнымиДаннымиВечернихОпераций("
        "ПараметрыСохранения, СписокПачки, ДатаПроведения);\n"
        "\t\t\t\t\t\tКонецЕсли;\n"
        "\t\t\t\t\tКонецЕсли;\n"
        "\t\t\t\t\t// IMAPPS-35039--"
    )
    evening_ins = (
        "\n"
        "\t\t\t\t\t#Вставка\n"
        "\t\t\t\t\t// IMDEV-8663.2 этап 3: пакетная предподготовка данных РСА/СЧА "
        'для группы "3. Расчет СЧА/РСА"\n'
        "\t\t\t\t\tЕсли ОбщегоНазначенияДУПовтИсп.ПолучитьЗначениеКонстанты("
        '"ИспользоватьПредварительныеЗапросыДляРегламентовСЧА_РСА") = Истина Тогда\n'
        "\t\t\t\t\t\tЕсли ЗначениеЗаполнено(ГруппаОперацийПользователя)"
        " И ГруппаОперацийПользователя.Код = КодГруппыРасчетаСЧА_РСА() Тогда\n"
        "\t\t\t\t\t\t\tЗаполнитьПараметрыСохраненияПакетнымиДаннымиГруппыСЧА("
        "ПараметрыСохранения, СписокПачки, ДатаПериода);\n"
        "\t\t\t\t\t\tКонецЕсли;\n"
        "\t\t\t\t\tКонецЕсли;\n"
        "\t\t\t\t\t#КонецВставки"
    )
    by_name["СформироватьРегламентныеОперации"] = insert_after(
        by_name["СформироватьРегламентныеОперации"],
        evening_marker,
        evening_ins,
        "evening insert",
    )

    clear_marker = '\t\tКлючиДляУдаления.Добавить("СоответствиеПропускРЕПОВетки");'
    clear_ins = (
        "\n"
        "\t\t#Вставка\n"
        "\t\t// IMDEV-8663.2 этап 3: пакетные данные расчета СЧА/РСА живут только "
        "в рамках одной пачки договоров\n"
        '\t\tКлючиДляУдаления.Добавить("СоответствиеДоговорТаблицаБУ_СЧА_РСА");\n'
        '\t\tКлючиДляУдаления.Добавить("СоответствиеДоговорТаблицаУУ_СЧА_РСА");\n'
        "\t\t#КонецВставки"
    )
    by_name["ОчиститьПакетныеДанныеПараметрыСохранения"] = insert_after(
        by_name["ОчиститьПакетныеДанныеПараметрыСохранения"],
        clear_marker,
        clear_ins,
        "clear keys",
    )

    docs_block1_old = (
        "\t\t// IMAPPS-35039--\n"
        "\t\t\n"
        "\t\t// ASP-209118 IMDEV-8899 3.1\n"
        "\t\tСоответствиеПропускРЕПОВетки = Неопределено;"
    )
    docs_block1_new = (
        "\t\t// IMAPPS-35039--\n"
        "\t\t\n"
        "\t\t#Вставка\n"
        "\t\t// IMDEV-8663.2 этап 3: готовые данные РСА/СЧА по текущему договору (операция 1000)\n"
        "\t\tТаблицаБУ_СЧА_РСАПоДоговору = Неопределено;\n"
        "\t\tТаблицаУУ_СЧА_РСАПоДоговору = Неопределено;\n"
        "\t\t\n"
        "\t\tСоответствиеДоговорТаблицаБУ_СЧА_РСА = Неопределено;\n"
        "\t\tСоответствиеДоговорТаблицаУУ_СЧА_РСА = Неопределено;\n"
        '\t\tПараметрыСохранения.Свойство("СоответствиеДоговорТаблицаБУ_СЧА_РСА", '
        "СоответствиеДоговорТаблицаБУ_СЧА_РСА);\n"
        '\t\tПараметрыСохранения.Свойство("СоответствиеДоговорТаблицаУУ_СЧА_РСА", '
        "СоответствиеДоговорТаблицаУУ_СЧА_РСА);\n"
        "\t\t\n"
        "\t\tЕсли СоответствиеДоговорТаблицаБУ_СЧА_РСА <> Неопределено Тогда\n"
        "\t\t\tТаблицаБУ_СЧА_РСАПоДоговору = СоответствиеДоговорТаблицаБУ_СЧА_РСА.Получить(ДоговорДУ);\n"
        "\t\tКонецЕсли;\n"
        "\t\tЕсли СоответствиеДоговорТаблицаУУ_СЧА_РСА <> Неопределено Тогда\n"
        "\t\t\tТаблицаУУ_СЧА_РСАПоДоговору = СоответствиеДоговорТаблицаУУ_СЧА_РСА.Получить(ДоговорДУ);\n"
        "\t\tКонецЕсли;\n"
        "\t\t#КонецВставки\n"
        "\t\t\n"
        "\t\t// ASP-209118 IMDEV-8899 3.1\n"
        "\t\tСоответствиеПропускРЕПОВетки = Неопределено;"
    )
    by_name["СформироватьДокументыЗакрытияПериода"] = replace_once(
        by_name["СформироватьДокументыЗакрытияПериода"],
        docs_block1_old,
        docs_block1_new,
        "docs block1",
    )

    docs_block2_marker = (
        "\t\t// ASP-197909 IMAPPS-35037++ Конец: Извлечение соответствия договор -> "
        "таблица взаиморасчетов"
    )
    docs_block2_ins = (
        "\t\t#Вставка\n"
        "\t\t// IMDEV-8663.2 этап 3: Операция 1000 - расчет РСА/СЧА. Передаем ОБЕ таблицы структурой.\n"
        "\t\t// Обе ссылки - таблицы значений (пустая ТЗ допустима: нулевые остатки, не откат).\n"
        "\t\tЕсли ТаблицаБУ_СЧА_РСАПоДоговору <> Неопределено"
        " И ТаблицаУУ_СЧА_РСАПоДоговору <> Неопределено Тогда\n"
        "\t\t\tДополнительныеДанныеОперации1000 = Новый Структура;\n"
        '\t\t\tДополнительныеДанныеОперации1000.Вставить("ТаблицаБУ", ТаблицаБУ_СЧА_РСАПоДоговору);\n'
        '\t\t\tДополнительныеДанныеОперации1000.Вставить("ТаблицаУУ", ТаблицаУУ_СЧА_РСАПоДоговору);\n'
        "\t\t\tСоответствиеОперацияТаблица.Вставить(\n"
        '\t\t\t\t"ИсполняемыеПроцедурыЗакрытияПериода.Операция_1000_РасчетРСА_СЧА",\n'
        "\t\t\t\tДополнительныеДанныеОперации1000);\n"
        "\t\tКонецЕсли;\n"
        "\t\t#КонецВставки\n"
        "\t\t\n"
    )
    by_name["СформироватьДокументыЗакрытияПериода"] = replace_once(
        by_name["СформироватьДокументыЗакрытияПериода"],
        docs_block2_marker,
        docs_block2_ins + docs_block2_marker,
        "docs block2",
    )

    idx_old = (
        "\t\tИндексОчереди = 0;\n"
        "\t\tНомерНачалаПачки = ТекущийНомер;\n"
        '\t\tПараметрыСохранения.Вставить("ОбработаноВПачке", 0);'
    )
    idx_new = (
        "\t\tИндексОчереди = 0;\n"
        "\t\tНомерНачалаПачки = ТекущийНомер;\n"
        "\t\t#Вставка\n"
        "\t\tТекущаяГруппаЧанков = Неопределено; // IMDEV-8663.2 этап 3 АР-9\n"
        "\t\t#КонецВставки\n"
        '\t\tПараметрыСохранения.Вставить("ОбработаноВПачке", 0);'
    )
    by_name["ОбработатьПачкуДиспетчером"] = replace_once(
        by_name["ОбработатьПачкуДиспетчером"],
        idx_old,
        idx_new,
        "AR-9 var",
    )

    chunk_old = (
        "\t\t\t\tЧанк = ОчередьЧанков[ИндексОчереди];\n"
        "\t\t\t\tИндексОчереди = ИндексОчереди + 1;"
    )
    chunk_new = (
        "\t\t\t\tЧанк = ОчередьЧанков[ИндексОчереди];\n"
        "\t\t\t\t#Вставка\n"
        "\t\t\t\t// IMDEV-8663.2 этап 3 АР-9: не стартовать чанки следующей группы, "
        "пока живы задания текущей.\n"
        "\t\t\t\t// Индекс очереди увеличивать только после прохождения барьера.\n"
        "\t\t\t\tЕсли ТекущаяГруппаЧанков <> Неопределено\n"
        "\t\t\t\t\tИ Чанк.ГруппаОперацийПользователя <> ТекущаяГруппаЧанков\n"
        "\t\t\t\t\tИ ПараметрыСохранения.СписокФоновыхЗаданий.Количество() > 0 Тогда\n"
        "\t\t\t\t\tПрервать;\n"
        "\t\t\t\tКонецЕсли;\n"
        "\t\t\t\tТекущаяГруппаЧанков = Чанк.ГруппаОперацийПользователя;\n"
        "\t\t\t\t#КонецВставки\n"
        "\t\t\t\tИндексОчереди = ИндексОчереди + 1;"
    )
    by_name["ОбработатьПачкуДиспетчером"] = replace_once(
        by_name["ОбработатьПачкуДиспетчером"],
        chunk_old,
        chunk_new,
        "AR-9 barrier",
    )

    keys_marker = '\t\t\t\tКлючиСоответствий.Добавить("СоответствиеДоговорТаблицаКотировокУУ");'
    keys_ins = (
        "\n"
        "\t\t\t\t#Вставка\n"
        "\t\t\t\t// IMDEV-8663.2 этап 3: пакетные данные расчета СЧА/РСА для операции 1000\n"
        '\t\t\t\tКлючиСоответствий.Добавить("СоответствиеДоговорТаблицаБУ_СЧА_РСА");\n'
        '\t\t\t\tКлючиСоответствий.Добавить("СоответствиеДоговорТаблицаУУ_СЧА_РСА");\n'
        "\t\t\t\t#КонецВставки"
    )
    by_name["ОбработатьПачкуДиспетчером"] = insert_after(
        by_name["ОбработатьПачкуДиспетчером"],
        keys_marker,
        keys_ins,
        "dispatcher keys",
    )

    parts = [
        "#Область IMDEV_8663_2_Перехваты\n",
        by_name["СформироватьРегламентныеОперации"].rstrip(),
        "",
        by_name["СформироватьДокументыЗакрытияПериода"].rstrip(),
        "",
        by_name["ОчиститьПакетныеДанныеПараметрыСохранения"].rstrip(),
        "",
        by_name["ОбработатьПачкуДиспетчером"].rstrip(),
        "",
        "#КонецОбласти\n",
    ]
    return "\n".join(parts)


def patch_document_manager(cf_text: str) -> str:
    body = extract_method(cf_text, "ПолучитьСуммыРСА_СЧА")
    intercept = make_intercept(body, "ПолучитьСуммыРСА_СЧА", "4")

    bu_marker = (
        "\t\tЗапрос.Текст =\n"
        '\t\t"ВЫБРАТЬ\n'
        "\t\t|\tХозрасчетныйОстатки.Счет КАК ИсточникПоказателя,"
    )
    uu_marker = (
        "\t\tЗапросУУ.Текст = \n"
        '\t\t"ВЫБРАТЬ\n'
        "\t\t|\tСтоимостьАктивовУправленческийОстатки.Актив КАК Показатель,"
    )
    ss_marker = (
        "\t\t\tЗапрос.Текст = \n"
        '\t\t\t"ВЫБРАТЬ\n'
        "\t\t\t|\tСправедливаяСтоимостьСделокTn.ПлановаяПозиция,"
    )

    intercept = wrap_assignment(
        intercept,
        bu_marker,
        "\t\tЗапрос.Текст = ТекстЗапросаБУ(Ложь);",
        "wrap BU",
    )
    intercept = wrap_assignment(
        intercept,
        uu_marker,
        "\t\tЗапросУУ.Текст = ТекстЗапросаУУ(Ложь);",
        "wrap UU",
    )
    intercept = wrap_assignment(
        intercept,
        ss_marker,
        "\t\t\tЗапрос.Текст = ТекстЗапросаСС(Ложь);",
        "wrap SS",
    )

    bu_literal = extract_query_literal(cf_text, bu_marker, "extract BU")
    uu_literal = extract_query_literal(cf_text, uu_marker, "extract UU")
    ss_literal = extract_query_literal(cf_text, ss_marker, "extract SS")

    uu_markers = [
        "СтоимостьАктивовУправленческийОстатки.Актив КАК Показатель,",
        "НачисленныйКупонныйДоходУправленческийОстатки.Облигация,",
        "УУ_ЦенныеБумагиHTMОстатки.Партия,",
        "УУ_НКДПоЦеннымБумагамHTMОстатки.Партия,",
        "КорректировкиПоЭСПОблигации.Партия,",
        "НачисленныеПроцентыПоБанковскимСчетамУправленческийОстатки.АналитическийСчет,",
        "ЗадолженностьЭмитентаПоОблигациямУУОстатки.Актив,",
        "ЗадолженностьЭмитентаПоКупонномуДоходуУУОстатки.Облигация,",
        "ЗадолженностьЭмитентаПоДивидендамУУОстатки.Актив,",
        "ДенежныеСредстваУправленческийОстатки.АналитическийСчет,",
        "ОпционныеПремииОстатки.Опцион,",
        "СтоимостьАктивовПоСделкамРЕПОУправленческийОстатки.Актив,",
        "НачисленныеПроцентыПоРЕПОУправленческийОстатки.СделкаРЕПО,",
        "НачисленныйКупонныйДоходПоСделкамРЕПОУправленческийОстатки.Облигация,",
        "РасчетыРЕПОДебиторскаяЗадолженностьПоТелуОстатки.БизнесПроцесс,",
        "РасчетыРЕПОДебиторскаяЗадолженностьПоКупонуОстатки.Контрагент,",
        "РасчетыРЕПОКредиторскаяЗадолженностьПоТелуОстатки.БизнесПроцесс,",
        "РасчетыРЕПОКредиторскаяЗадолженностьПоКупонуОстатки.Контрагент,",
        "СформированныеРезервыОстатки.Аналитика,",
        "ВТ_ПромежуточнаяТаблица.Показатель КАК Показатель,",
    ]
    for marker in uu_markers:
        must_count(uu_literal, marker, f"UU marker {marker[:40]}")

    must_count(bu_literal, "ХозрасчетныйОстатки.Счет КАК ИсточникПоказателя,", "BU field")
    must_count(bu_literal, "ДоговорДУ = &ДоговорДУ", "BU filter")
    must_count(ss_literal, "СправедливаяСтоимостьСделокTn.ПлановаяПозиция,", "SS field")
    must_count(ss_literal, "ДоговорДУ = &ДоговорДУ", "SS filter")

    # After | there must be a tab in CF literals.
    for label, literal in (("BU", bu_literal), ("UU", uu_literal), ("SS", ss_literal)):
        if "|\t" not in literal:
            raise SystemExit(f"{label} query has no tab after |")

    packet = load_text(ROOT / "stage34_packet.bsl")
    packet = packet.replace("|TAB|", "|\t")
    packet = packet.replace(
        "<<<QUERY_BU_FUNC>>>",
        make_query_func(
            "ТекстЗапросаОднодоговорныйБУ",
            "Возвращает однодоговорной текст запроса БУ (копия области ТЕКСТ_ЗАПРОСА, "
            "ПолучитьСуммыРСА_СЧА). Единственный источник методики БУ.",
            bu_literal,
        ).rstrip(),
    )
    packet = packet.replace(
        "<<<QUERY_UU_FUNC>>>",
        make_query_func(
            "ТекстЗапросаОднодоговорныйУУ",
            "Возвращает однодоговорной текст запроса УУ (копия области ТЕКСТ_ЗАПРОСА, "
            "ПолучитьСуммыРСА_СЧА). Единственный источник методики УУ.",
            uu_literal,
        ).rstrip(),
    )
    packet = packet.replace(
        "<<<QUERY_SS_FUNC>>>",
        make_query_func(
            "ТекстЗапросаОднодоговорныйСС",
            "Возвращает однодоговорной текст запроса СС незавершенных сделок "
            "(ПолучитьСуммыРСА_СЧА). Параметр периода в запросе называется Период, не ДатаОстатков.",
            ss_literal,
        ).rstrip(),
    )
    if "<<<QUERY_" in packet:
        raise SystemExit("query placeholders were not replaced")

    return (
        "#Область ПрограммныйИнтерфейс\n\n"
        "#Область IMDEV_8663_2_Перехваты\n\n"
        f"{intercept.rstrip()}\n\n"
        "#КонецОбласти\n\n"
        f"{packet.rstrip()}\n\n"
        "#КонецОбласти\n"
    )


def patch_object_module(cf_text: str) -> str:
    body = extract_method(cf_text, "ПолучитьСуммыРСАСЧА")
    extra = (
        'Процедура IM86632_ПолучитьСуммыРСАСЧА(Отказ = Неопределено, ТекстОтказа = "") Экспорт',
        "Процедура IM86632_ПолучитьСуммыРСАСЧА(Отказ = Неопределено, ТекстОтказа = \"\", "
        "ГотовыеДанные = Неопределено) Экспорт",
    )
    intercept = make_intercept(body, "ПолучитьСуммыРСАСЧА", "3", extra)

    old_call = (
        "\tДокументы.РасчетСЧА_РСА.ПолучитьСуммыРСА_СЧА(ДоговорДУ, "
        "ПолучитьДатуСВременемОкончанияРабочегоДня(Дата), РСА, СЧА, СуммаРСА, СуммаСЧА,  "
        "ТЗДанныеПоБУ, ТЗДанныеПоУУ, Отказ, ТекстОтказа, Ссылка);"
    )
    new_call = (
        "\t#Удаление\n"
        f"{old_call}\n"
        "\t#КонецУдаления\n"
        "\t#Вставка\n"
        "\t// IMDEV-8663.2 этап 3: используем пакетно рассчитанные данные, если они переданы и корректны\n"
        '\tИспользоватьГотовыеДанные = ТипЗнч(ГотовыеДанные) = Тип("Структура")\n'
        '\t\tИ ГотовыеДанные.Свойство("ТаблицаБУ")\n'
        '\t\tИ ГотовыеДанные.Свойство("ТаблицаУУ")\n'
        '\t\tИ ТипЗнч(ГотовыеДанные.ТаблицаБУ) = Тип("ТаблицаЗначений")\n'
        '\t\tИ ТипЗнч(ГотовыеДанные.ТаблицаУУ) = Тип("ТаблицаЗначений");\n'
        "\t// Пустая ТЗ - валидный пакетный результат (нулевые остатки), не повод для fallback.\n"
        "\t\n"
        "\tЕсли ИспользоватьГотовыеДанные Тогда\n"
        "\t\tТЗДанныеПоБУ = ГотовыеДанные.ТаблицаБУ;\n"
        "\t\tТЗДанныеПоУУ = ГотовыеДанные.ТаблицаУУ;\n"
        "\tИначе\n"
        "\t\tДокументы.РасчетСЧА_РСА.ПолучитьСуммыРСА_СЧА(ДоговорДУ, "
        "ПолучитьДатуСВременемОкончанияРабочегоДня(Дата), РСА, СЧА, СуммаРСА, СуммаСЧА, "
        "ТЗДанныеПоБУ, ТЗДанныеПоУУ, Отказ, ТекстОтказа, Ссылка);\n"
        "\tКонецЕсли;\n"
        "\t#КонецВставки"
    )
    intercept = replace_once(intercept, old_call, new_call, "object ready data")

    header = (
        "// Описание: Заполняет табличные части документа данными расчета РСА/СЧА.\n"
        "//\n"
        "// Параметры:\n"
        "//  Отказ         - Булево    - признак отказа\n"
        "//  ТекстОтказа   - Строка    - текст отказа\n"
        "//  ГотовыеДанные - Структура - IMDEV-8663.2 этап 3, необязательный. "
        "Предрассчитанные пакетно данные:\n"
        "//                  * ТаблицаБУ - ТаблицаЗначений - строки по данным БУ для этого договора\n"
        "//                  * ТаблицаУУ - ТаблицаЗначений - строки по данным УУ для этого договора\n"
        "//                  Если не передан - расчет выполняется обычным (однодоговорным) способом.\n"
        "//\n"
    )
    return (
        "#Область IMDEV_8663_2_Перехваты\n\n"
        f"{header}"
        f"{intercept.rstrip()}\n\n"
        "#КонецОбласти\n"
    )


def patch_common_module(cf_text: str) -> str:
    body = extract_method(cf_text, "Операция_1000_РасчетРСА_СЧА")
    extra = (
        "Процедура IM86632_Операция_1000_РасчетРСА_СЧА(ЗакрытиеПериода, Дата, ДоговорДУ, "
        "СписокОпераций, Отказ, ТекстОтказа) Экспорт",
        "Процедура IM86632_Операция_1000_РасчетРСА_СЧА(ЗакрытиеПериода, Дата, ДоговорДУ, "
        "СписокОпераций, Отказ, ТекстОтказа, ДополнительныеДанные = Неопределено) Экспорт",
    )
    intercept = make_intercept(body, "Операция_1000_РасчетРСА_СЧА", "3", extra)

    old_call = "\tДокументРасчетСЧА_РСА.ПолучитьСуммыРСАСЧА(Отказ, ТекстОтказа);"
    new_call = (
        "\t#Удаление\n"
        f"{old_call}\n"
        "\t#КонецУдаления\n"
        "\t#Вставка\n"
        "\t// IMDEV-8663.2 этап 3: передаем пакетные данные операции 1000, если они есть\n"
        "\tДокументРасчетСЧА_РСА.ПолучитьСуммыРСАСЧА(Отказ, ТекстОтказа, ДополнительныеДанные);\n"
        "\t#КонецВставки"
    )
    intercept = replace_once(intercept, old_call, new_call, "operation 1000 call")

    header = (
        "// IMDEV-8663.2 этап 3: добавлен необязательный 7-й параметр ДополнительныеДанные.\n"
        "// Механизм передачи - штатный (IMAPPS-35037): ВыполнитьИсполняемуюПроцедуруЗакрытияПериода\n"
        "// передает 7-й параметр, если в СоответствиеОперацияТаблица есть ключ с именем этой процедуры.\n"
        "//\n"
    )
    return (
        "#Область IMDEV_8663_2_Перехваты\n\n"
        f"{header}"
        f"{intercept.rstrip()}\n\n"
        "#КонецОбласти\n"
    )


def forbidden_tokens(text: str, label: str) -> None:
    for token in ("&amp;", "&lt;", "&gt;", "&quot;"):
        if token in text:
            raise SystemExit(f"{label}: HTML entity {token}")
    if "Операция_1010" in text and "IM86632_Операция_1010" in text:
        raise SystemExit(f"{label}: unexpected intercept of 1010")


def main() -> int:
    cf_cat = load_text(CF / "Catalogs" / "РегламентныеПериоды" / "Ext" / "ManagerModule.bsl")
    cf_doc = load_text(CF / "Documents" / "РасчетСЧА_РСА" / "Ext" / "ManagerModule.bsl")
    cf_obj = load_text(CF / "Documents" / "РасчетСЧА_РСА" / "Ext" / "ObjectModule.bsl")
    cf_cm = load_text(
        CF / "CommonModules" / "ИсполняемыеПроцедурыЗакрытияПериода" / "Ext" / "Module.bsl"
    )

    existing = load_text(
        EXT / "Catalogs" / "РегламентныеПериоды" / "Ext" / "ManagerModule.bsl"
    )
    marker_pred = "#Область IMDEV_8663_2_Предподготовка"
    if marker_pred in existing:
        head = existing[: existing.find(marker_pred)].rstrip() + "\n\n"
    else:
        if existing.count("#КонецОбласти") < 2:
            raise SystemExit("unexpected catalog manager structure")
        last = existing.rstrip().rfind("#КонецОбласти")
        head = existing.rstrip()[:last].rstrip() + "\n\n"

    pred = load_text(ROOT / "stage34_predpodgotovka.bsl")
    intercepts = patch_catalog_manager(cf_cat)
    catalog = head + pred.rstrip() + "\n\n" + intercepts.rstrip() + "\n\n#КонецОбласти\n"

    doc_manager = patch_document_manager(cf_doc)
    obj_module = patch_object_module(cf_obj)
    cm_module = patch_common_module(cf_cm)

    forbidden_tokens(catalog, "catalog")
    forbidden_tokens(doc_manager, "document manager")
    forbidden_tokens(obj_module, "object")
    forbidden_tokens(cm_module, "common")

    for label, text in (
        ("catalog", catalog),
        ("document", doc_manager),
        ("object", obj_module),
        ("common", cm_module),
    ):
        if "#Вставка" not in text:
            raise SystemExit(f"{label}: missing #Вставка")
        if "&ИзменениеИКонтроль" not in text:
            raise SystemExit(f"{label}: missing interceptor")

    write_bsl(EXT / "Catalogs" / "РегламентныеПериоды" / "Ext" / "ManagerModule.bsl", catalog)
    write_bsl(EXT / "Documents" / "РасчетСЧА_РСА" / "Ext" / "ManagerModule.bsl", doc_manager)
    write_bsl(EXT / "Documents" / "РасчетСЧА_РСА" / "Ext" / "ObjectModule.bsl", obj_module)
    write_bsl(
        EXT / "CommonModules" / "ИсполняемыеПроцедурыЗакрытияПериода" / "Ext" / "Module.bsl",
        cm_module,
    )

    print("OK catalog", catalog.count("\n"), "lines")
    print("OK document manager", doc_manager.count("\n"), "lines")
    print("OK object", obj_module.count("\n"), "lines")
    print("OK common", cm_module.count("\n"), "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
