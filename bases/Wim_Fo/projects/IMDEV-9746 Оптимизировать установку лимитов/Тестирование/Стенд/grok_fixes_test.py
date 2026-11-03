# -*- coding: utf-8 -*-
"""IMDEV-9746. Проверка правок 1.17 по замечаниям внешнего ревью (сброс отказа по классу, проверки обработчика порогов).

    python grok_fixes_test.py mark     обычный ФО: настройка порогов эталона помечена на удаление, по запуску 1.16 и 1.17;
                                       ожидание - в обеих версиях пороги не записаны, письмо с флагом FAIL
    python grok_fixes_test.py classes  розница: у комплаенса отказ (подтвержденный лимит с расширенным подтверждением),
                                       у рисков клиенты есть, а пар нет (внешний код эталона рисков не найден);
                                       ожидание - письмо рисков в 1.17 без флага FAIL

Временные признаки возвращаются в finally. Темы писем - из results/mail (заглушка mock_smtp.py).
"""
import email
import email.header
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_versions as cv  # noqa: E402
import run_stand as rs  # noqa: E402

OUT = os.path.join(rs.RESULTS, "grok_fixes.jsonl")
log = rs.log


def set_attr(fo, ref, name, value):
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "РеквизитОбъекта")
    p.Вставить("Ссылка", ref)
    p.Вставить("Реквизит", name)
    p.Вставить("Значение", value)
    return rs.checked(rs.scenario(fo, p, f"реквизит {name} = {value}", retry=True))["данные"].Было


def subjects(names):
    result = []
    for n in names:
        msg = email.message_from_bytes(open(os.path.join(cv.MAIL_DIR, n), "rb").read())
        parts = email.header.decode_header(msg.get("Subject", ""))
        result.append("".join(t.decode(c or "utf-8") if isinstance(t, bytes) else t for t, c in parts))
    return result


def run_version(fo, test, mode, version):
    before, _ = cv.letters_since([])
    cv.run(fo, mode, version, 1)
    after, _ = cv.letters_since([])
    with open(cv.OUT, encoding="utf-8") as f:
        record = json.loads(f.readlines()[-1])
    record["тест"] = test
    record["темы"] = subjects([n for n in after if n not in before])
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    log(f"  {version}: данные {record['данные']}")
    for s in record["темы"]:
        log(f"    письмо: {s}")


def etalon_setting(fo, mode):
    rows = rs.query(fo, """ВЫБРАТЬ РАЗЛИЧНЫЕ П.НастройкаПороговДляПроверкиЛимитов КАК Настройка
        ИЗ РегистрСведений.ПорогиЛимитов КАК П ГДЕ П.Портфель = &Эталон""", {"Эталон": rs.portfolio(fo, rs.MODES[mode]["эталон"])})
    return [r["Настройка"] for r in rows]


def test_mark(fo):
    settings = etalon_setting(fo, "o")
    log(f"настроек порогов у эталона: {len(settings)}")
    was = [set_attr(fo, s, "ПометкаУдаления", True) for s in settings]
    try:
        for version in ("1.16", "1.17"):
            run_version(fo, "mark", "o", version)
    finally:
        for s, w in zip(settings, was):
            set_attr(fo, s, "ПометкаУдаления", w)
        log(f"пометки возвращены: {was}")


def set_risk_code(fo, refs, code):
    props = rs.properties(fo)
    records = fo.NewObject("Массив")
    for ref in refs:
        rec = fo.NewObject("Структура")
        rec.Вставить("Объект", ref)
        rec.Вставить("Свойство", props["ВнешнийКодЭталонногоПортфеляРиски"])
        rec.Вставить("Значение", code)
        records.Добавить(rec)
    p = fo.NewObject("Структура")
    p.Вставить("Сценарий", "Сведения")
    p.Вставить("Записи", records)
    rs.checked(rs.scenario(fo, p, f"внешний код эталона рисков = {code}", retry=True))


def test_classes(fo):
    klass = rs.limit_class(fo, "Compliance")
    limit = rs.mode_limits(fo, "r", "комплаенс")[0]
    log(f"лимит комплаенса розницы: {fo.String(limit)}")
    was_class = set_attr(fo, klass, "РасширенноеПодтверждение", True)
    was_limit = set_attr(fo, limit, "Подтвержден", True)
    try:
        for version in ("1.16", "1.17"):
            batch = rs.next_clients(fo, "r", 2)
            set_risk_code(fo, [r["Ссылка"] for r in batch], "T9746_NO_ETALON")
            try:
                run_version(fo, "classes", "r", version)
            finally:
                set_risk_code(fo, [r["Ссылка"] for r in batch], rs.MODES["r"]["эталон"])
    finally:
        set_attr(fo, limit, "Подтвержден", was_limit)
        set_attr(fo, klass, "РасширенноеПодтверждение", was_class)
        log(f"возвращено: класс {was_class}, лимит {was_limit}")


def main():
    fo = rs.connect("wim_fo")
    rs.register(fo)
    {"mark": test_mark, "classes": test_classes}[sys.argv[1]](fo)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
