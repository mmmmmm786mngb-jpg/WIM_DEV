#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сводка по выгрузке справочника Лимиты и установок."""

import collections
import hashlib
import json
import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Лимиты_и_справочная информация"))
FOLDER = sys.argv[1] if len(sys.argv) > 1 else "FO_обычное"
ROOT = os.path.join(BASE, FOLDER)
OUT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "Тестирование", "reports",
    "limits_catalog_profile_%s.txt" % FOLDER))
TODAY = "2026-09-24"


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def pres(value):
    if not isinstance(value, dict):
        return ""
    return value.get("Представление") or value.get("Имя") or ""


def empty_ref(value):
    return not isinstance(value, dict) or value.get("Пустая") or not value.get("Представление")


def walk_filter(items, depth=1):
    count = 0
    max_depth = 0
    fields = []
    comparisons = collections.Counter()
    if not items:
        return count, max_depth, fields, comparisons
    max_depth = depth
    for item in items:
        count += 1
        if item.get("Вид") == "Группа":
            nested, nested_depth, nested_fields, nested_cmp = walk_filter(item.get("Элементы") or [], depth + 1)
            count += nested
            max_depth = max(max_depth, nested_depth)
            fields.extend(nested_fields)
            comparisons.update(nested_cmp)
        else:
            fields.append(str(item.get("ЛевоеЗначение") or ""))
            comparisons[str(item.get("ВидСравнения") or "")] += 1
    return count, max_depth, fields, comparisons


def query_features(text):
    upper = (text or "").upper()
    return {
        "len": len(text or ""),
        "joins": upper.count("СОЕДИНЕНИЕ") + upper.count(" JOIN"),
        "selects": upper.count("ВЫБРАТЬ"),
        "temp": upper.count("ПОМЕСТИТЬ"),
        "ukr": upper.count("УКР"),
    }


def main():
    index = load(os.path.join(ROOT, "index.json"))
    lines = []

    def add(text=""):
        lines.append(text)

    add("config %s %s exported %s" % (index.get("Конфигурация"), index.get("ВерсияКонфигурации"), index.get("ДатаВыгрузки")))
    add("elements %s groups %s installation docs %s errors %s" % (
        index.get("КоличествоЭлементов"), index.get("КоличествоГрупп"),
        index.get("КоличествоДокументовУстановок"), len(index.get("Ошибки") or [])))

    rows = index["Лимиты"]
    groups = [row for row in rows if row.get("ЭтоГруппа")]
    items = [row for row in rows if not row.get("ЭтоГруппа")]
    add("index groups %s items %s" % (len(groups), len(items)))
    add("groups: " + "; ".join(row.get("Наименование") or "" for row in groups))

    def tally(source, key):
        counter = collections.Counter()
        for row in source:
            value = row.get(key)
            if isinstance(value, dict):
                value = pres(value) or "(empty)"
            elif value is None:
                value = "(none)"
            counter[str(value)] += 1
        return counter

    add("")
    add("== index items ==")
    for title, counter in (
        ("deleted", tally(items, "ПометкаУдаления")),
        ("test", tally(items, "Тестовый")),
        ("confirmed", tally(items, "Подтвержден")),
        ("kind", tally(items, "ВидЛимита")),
        ("class", tally(items, "КлассЛимита")),
        ("method", tally(items, "СпособНастройкиЛимита")),
        ("dataset", tally(items, "НаборДанных")),
    ):
        add(title)
        for name, count in counter.most_common(25):
            add("  %s | %s" % (count, name))

    kind_by_code = {}
    for row in items:
        kind_by_code[row.get("УникальныйИдентификатор")] = pres(row.get("ВидЛимита"))

    limits_dir = os.path.join(ROOT, "limits")
    files = [name for name in os.listdir(limits_dir) if name.endswith(".json")]
    stats = []
    field_counter = collections.Counter()
    comparison_counter = collections.Counter()
    dataset_flags = collections.Counter()
    source_kinds = collections.Counter()
    algorithms = collections.Counter()
    modifiers = collections.Counter()
    threshold_variants = collections.Counter()
    query_hashes = collections.defaultdict(list)
    position_parts = collections.Counter()
    flag_names = [
        "ПакетныйРежим",
        "ГруппироватьРезультатПоЭмитенту",
        "ДополнятьОстаткамиПозиции",
        "ИспользоватьПулДанныхИзМодификатора",
        "НеИспользоватьОсновнойПулДанных",
        "НеРаскрыватьПаи",
        "Тестовый",
        "Подтвержден",
        "ПометкаУдаления",
        "ЛимитПеренесенНеПолностью",
        "НастройкиПодготовкиСпискаАктивовНеактуальны",
    ]
    flag_counts = collections.Counter()

    for name in files:
        data = load(os.path.join(limits_dir, name))
        attrs = data.get("Реквизиты") or {}
        for flag in flag_names:
            if attrs.get(flag) is True:
                flag_counts[flag] += 1
        settings = ((attrs.get("НастройкиПодготовкиСпискаАктивов") or {}).get("Значение") or {})
        filt_count, filt_depth, fields, comparisons = walk_filter(settings.get("Отбор") or [])
        field_counter.update(fields)
        comparison_counter.update(comparisons)
        main_query = attrs.get("УсловияОтбораОсновные") or ""
        features = query_features(main_query)
        qualifiers = (data.get("ТабличныеЧасти") or {}).get("Квалификаторы") or []
        qualifier_len = 0
        qualifier_nodes = 0
        for qualifier in qualifiers:
            qualifier_len += len(qualifier.get("УсловияОтбора") or "")
            qualifier_settings = ((qualifier.get("Квалификатор") or {}).get("Значение") or {})
            nodes, _, qualifier_fields, qualifier_cmp = walk_filter(qualifier_settings.get("Отбор") or [])
            qualifier_nodes += nodes
            field_counter.update(qualifier_fields)
            comparison_counter.update(qualifier_cmp)
        parameters = (data.get("ТабличныеЧасти") or {}).get("ПараметрыЗапросов") or []
        related = data.get("Связанные") or {}
        dataset = related.get("НаборДанныхДляПроверкиЛимитов") or {}
        dataset_attrs = dataset.get("Реквизиты") or {}
        for flag in (
            "ИспользоватьРепрайсинг",
            "ИспользоватьУКР",
            "ИспользоватьСвойДеноминатор",
            "ТолькоФактическаяПозиция",
            "ИсключитьНеторговые",
            "ВсегдаИспользоватьСоставПозицииИзНабораДанных",
            "ОграничиватьПлановуюПозициюПоДатеРасчетов",
            "ПриводитьКВалютеПорогов",
        ):
            if dataset_attrs.get(flag) is True:
                dataset_flags[flag] += 1
        source = dataset_attrs.get("ИсточникДанных") or {}
        source_kinds[pres(source) or "(no source)"] += 1
        algorithm = attrs.get("Алгоритм") or {}
        if not empty_ref(algorithm):
            algorithms[pres(algorithm)] += 1
        modifier = attrs.get("Модификатор") or {}
        if not empty_ref(modifier):
            modifiers[pres(modifier)] += 1
        variant = related.get("ВариантПроверкиПорога") or {}
        variant_attrs = variant.get("Реквизиты") or {}
        variant_name = pres(variant) or "(empty)"
        function_name = pres(variant_attrs.get("Вариант")) or pres(variant_attrs.get("ФункцияПроверкиПорога"))
        threshold_variants["%s / %s" % (variant_name, function_name)] += 1
        parts = ((dataset.get("ТабличныеЧасти") or {}).get("СоставПозиции") or [])
        for part in parts:
            position_parts[pres(part.get("ВидПозиции")) or str(part.get("ВидПозиции"))] += 1
        query_key = hashlib.sha1(main_query.encode("utf-8")).hexdigest() if main_query else ""
        if query_key:
            query_hashes[query_key].append(data.get("Наименование") or "")
        stats.append({
            "name": data.get("Наименование") or "",
            "code": data.get("Код") or "",
            "uuid": data.get("УникальныйИдентификатор") or "",
            "kind": pres(attrs.get("ВидЛимита")),
            "class": pres(attrs.get("КлассЛимита")),
            "method": pres(attrs.get("СпособНастройкиЛимита")),
            "dataset": pres(attrs.get("НаборДанныхДляПроверкиЛимитов")),
            "deleted": bool(attrs.get("ПометкаУдаления")),
            "test": bool(attrs.get("Тестовый")),
            "confirmed": bool(attrs.get("Подтвержден")),
            "filter_nodes": filt_count,
            "filter_depth": filt_depth,
            "query_len": features["len"],
            "joins": features["joins"],
            "selects": features["selects"],
            "temp_tables": features["temp"],
            "qualifiers": len(qualifiers),
            "qualifier_len": qualifier_len,
            "qualifier_nodes": qualifier_nodes,
            "parameters": len(parameters),
            "repricing": dataset_attrs.get("ИспользоватьРепрайсинг") is True,
            "ukr": dataset_attrs.get("ИспользоватьУКР") is True,
            "batch": attrs.get("ПакетныйРежим") is True,
            "query_key": query_key,
        })

    add("")
    add("== files %s ==" % len(stats))
    add("flags true")
    for name, count in flag_counts.most_common():
        add("  %s | %s" % (count, name))
    add("dataset flags true")
    for name, count in dataset_flags.most_common():
        add("  %s | %s" % (count, name))
    add("sources")
    for name, count in source_kinds.most_common(20):
        add("  %s | %s" % (count, name))
    add("algorithms")
    for name, count in algorithms.most_common():
        add("  %s | %s" % (count, name))
    add("modifiers")
    for name, count in modifiers.most_common(20):
        add("  %s | %s" % (count, name))
    add("threshold variants")
    for name, count in threshold_variants.most_common(20):
        add("  %s | %s" % (count, name))
    add("position parts on datasets, row occurrences")
    for name, count in position_parts.most_common(20):
        add("  %s | %s" % (count, name))
    add("top filter fields")
    for name, count in field_counter.most_common(30):
        add("  %s | %s" % (count, name))
    add("comparisons")
    for name, count in comparison_counter.most_common(15):
        add("  %s | %s" % (count, name))

    live = [row for row in stats if not row["deleted"] and not row["test"]]
    add("")
    add("live not deleted not test %s" % len(live))
    for title, key in (("kind", "kind"), ("class", "class"), ("method", "method")):
        counter = collections.Counter(row[key] or "(empty)" for row in live)
        add(title)
        for name, count in counter.most_common():
            add("  %s | %s" % (count, name))

    def top(source, key, limit=15):
        return sorted(source, key=lambda row: row[key], reverse=True)[:limit]

    add("")
    add("== heaviest live by query length ==")
    for row in top(live, "query_len"):
        add("%s | q=%s joins=%s selects=%s qual=%s nodes=%s | %s | %s" % (
            row["code"], row["query_len"], row["joins"], row["selects"], row["qualifiers"],
            row["filter_nodes"], row["kind"], row["name"][:140]))
    add("== heaviest live by filter nodes ==")
    for row in top(live, "filter_nodes"):
        add("%s | nodes=%s depth=%s q=%s | %s | %s" % (
            row["code"], row["filter_nodes"], row["filter_depth"], row["query_len"], row["kind"], row["name"][:140]))
    add("== heaviest live by qualifiers ==")
    for row in top([row for row in live if row["qualifiers"]], "qualifiers"):
        add("%s | qual=%s qlen=%s nodes=%s | %s | %s" % (
            row["code"], row["qualifiers"], row["qualifier_len"], row["qualifier_nodes"], row["kind"], row["name"][:140]))

    duplicated = [names for names in query_hashes.values() if len(names) > 1]
    duplicated.sort(key=len, reverse=True)
    add("")
    add("duplicate main query texts %s groups, largest %s" % (
        len(duplicated), len(duplicated[0]) if duplicated else 0))
    for names in duplicated[:12]:
        add("  %s | %s" % (len(names), " || ".join(name[:80] for name in names[:4])))

    empty_query = [row for row in live if row["query_len"] == 0]
    add("live with empty main query %s" % len(empty_query))
    add("live repricing %s ukr dataset %s batch %s" % (
        sum(1 for row in live if row["repricing"]),
        sum(1 for row in live if row["ukr"]),
        sum(1 for row in live if row["batch"])))

    installations = load(os.path.join(ROOT, "installations.json"))
    documents = installations.get("Документы") or []
    add("")
    add("== installations docs %s ==" % len(documents))
    posted = [doc for doc in documents if doc.get("Проведен")]
    confirmed_docs = [doc for doc in posted if doc.get("Подтвержден")]
    open_docs = []
    ended = 0
    target_types = collections.Counter()
    for doc in posted:
        end = doc.get("ДатаОкончанияДействия") or ""
        target_types[str((doc.get("ОбъектНазначения") or {}).get("Тип") or "")] += 1
        if end in ("", "0001-01-01T00:00:00") or end >= TODAY:
            open_docs.append(doc)
        else:
            ended += 1
    add("posted %s confirmed %s open-or-future %s ended before today %s" % (
        len(posted), len(confirmed_docs), len(open_docs), ended))
    add("target types among posted")
    for name, count in target_types.most_common():
        add("  %s | %s" % (count, name))

    def pairs(docs):
        result = []
        for doc in docs:
            target = doc.get("ОбъектНазначения") or {}
            for line in doc.get("Лимиты") or []:
                limit = line.get("Лимит") or {}
                result.append({
                    "portfolio": pres(target),
                    "portfolio_id": target.get("УникальныйИдентификатор") or "",
                    "target_type": target.get("Тип") or "",
                    "limit_id": limit.get("УникальныйИдентификатор") or "",
                    "limit": pres(limit),
                    "class": pres(doc.get("КлассЛимита")),
                    "confirmed_doc": bool(doc.get("Подтвержден")),
                    "settings": bool(line.get("НастройкиУстановлены")),
                    "end": doc.get("ДатаОкончанияДействия") or "",
                    "date": doc.get("Дата") or "",
                })
        return result

    open_pairs = pairs(open_docs)
    confirmed_open = [row for row in open_pairs if row["confirmed_doc"]]
    add("open pairs portfolio-limit %s confirmed-doc pairs %s" % (len(open_pairs), len(confirmed_open)))
    add("distinct portfolios open %s limits open %s" % (
        len({row["portfolio_id"] for row in open_pairs}),
        len({row["limit_id"] for row in open_pairs})))
    by_limit = collections.defaultdict(set)
    by_portfolio = collections.defaultdict(set)
    for row in open_pairs:
        by_limit[row["limit_id"]].add(row["portfolio_id"])
        by_portfolio[row["portfolio_id"]].add(row["limit_id"])
    fanout = sorted(((len(ports), limit_id) for limit_id, ports in by_limit.items()), reverse=True)
    per_portfolio = sorted(len(limits) for limits in by_portfolio.values())
    if per_portfolio:
        add("limits per open target min %s p50 %s p95 %s max %s" % (
            per_portfolio[0], per_portfolio[len(per_portfolio) // 2],
            per_portfolio[min(len(per_portfolio) - 1, int(len(per_portfolio) * 0.95))],
            per_portfolio[-1]))
    stat_by_id = {row["uuid"]: row for row in stats}
    add("top acting limits by target count")
    for count, limit_id in fanout[:25]:
        info = stat_by_id.get(limit_id) or {}
        add("  %s targets | %s | %s | q=%s nodes=%s qual=%s | %s" % (
            count, info.get("kind") or kind_by_code.get(limit_id) or "",
            info.get("code") or "", info.get("query_len") or 0, info.get("filter_nodes") or 0,
            info.get("qualifiers") or 0, (info.get("name") or "")[:120]))

    weight_by_kind = collections.Counter()
    weight_by_dataset = collections.Counter()
    for limit_id, ports in by_limit.items():
        info = stat_by_id.get(limit_id) or {}
        weight_by_kind[info.get("kind") or "(missing file)"] += len(ports)
        weight_by_dataset[info.get("dataset") or "(missing)"] += len(ports)
    add("open pair weight by kind")
    for name, count in weight_by_kind.most_common():
        add("  %s | %s" % (count, name))
    add("open pair weight by dataset")
    for name, count in weight_by_dataset.most_common(15):
        add("  %s | %s" % (count, name))

    acting_ids = set(by_limit)
    acting_live = [stat_by_id[item] for item in acting_ids if item in stat_by_id and not stat_by_id[item]["deleted"]]
    add("acting limits with file %s of which repricing %s ukr %s empty query %s qualifiers>0 %s" % (
        len(acting_live),
        sum(1 for row in acting_live if row["repricing"]),
        sum(1 for row in acting_live if row["ukr"]),
        sum(1 for row in acting_live if row["query_len"] == 0),
        sum(1 for row in acting_live if row["qualifiers"])))
    heavy_weight = []
    for row in acting_live:
        targets = len(by_limit.get(row["uuid"], ()))
        heavy_weight.append((row["query_len"] * max(targets, 1), targets, row))
    heavy_weight.sort(key=lambda item: item[0], reverse=True)
    add("top acting by query_len * targets")
    for score, targets, row in heavy_weight[:20]:
        add("  score=%s targets=%s q=%s nodes=%s | %s | %s" % (
            score, targets, row["query_len"], row["filter_nodes"], row["kind"], row["name"][:120]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("lines %s" % len(lines))
    print(OUT)


if __name__ == "__main__":
    main()
