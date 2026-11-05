# -*- coding: utf-8 -*-
"""Проверка ОтчетДепозитыCalipso.epf на dev ФО (wim_fo) перед передачей на Т-1.

    python run_calipso_report_dev.py

SQL-сервер Calipso с dev недоступен, поэтому сопоставление проверяется на синтетических строках в формате ответа
запроса Calipso: номер сделки, который дает маску реального субпортфеля dev (ожидается "Найден"), несуществующий номер
("Не найден"), неизвестная валюта (депозит пропускается), нулевой номер (не переводится). Отдельно - чтение Calipso с
сервера 1С: на dev ожидается ошибка подключения с подсказкой в сводке. Отчет HTML - Тестирование/reports.
"""
import datetime
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
STAND = os.path.join(os.path.dirname(PROJECT), "IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО",
                     "Тестирование", "Стенд_МО_ФО")
sys.path.insert(0, STAND)
import stand_common  # noqa: E402

EPF = os.path.join(PROJECT, "Тестирование", "Т-1", "ДепозитыCalipso", "ОтчетДепозитыCalipso.epf")
REPORTS = os.path.join(PROJECT, "Тестирование", "reports")
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def from_base36(text):
    value = 0
    for char in text:
        value = value * 36 + ALPHABET.index(char)
    return value


def to_base36(value):
    text = ""
    while value:
        text = ALPHABET[value % 36] + text
        value //= 36
    return text


def find_dev_subportfolio(fo):
    """Субпортфель dev с кодом счета вида ...-D<base36>-..., у которого маска находит ровно один живой субпортфель."""
    rows = stand_common.query(fo, """
        ВЫБРАТЬ ПЕРВЫЕ 200 Субпортфели.КодСчета КАК КодСчета
        ИЗ Справочник.Субпортфели КАК Субпортфели
        ГДЕ НЕ Субпортфели.ПометкаУдаления И Субпортфели.КодСчета ПОДОБНО "%-D%-%" """)
    for row in rows:
        code = row["КодСчета"].strip()
        start = code.find("-D")
        end = code.find("-", start + 2)
        part = code[start + 2:end]
        if part and all(c in ALPHABET for c in part) and part[0] != "0":
            return code, part, from_base36(part)
    return None


def currency_with_asset(fo):
    rows = stand_common.query(fo, """
        ВЫБРАТЬ ПЕРВЫЕ 1 Валюты.Наименование КАК Наименование
        ИЗ Справочник.Активы КАК Активы
            ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Валюты КАК Валюты ПО Активы.Объект = Валюты.Ссылка
        ГДЕ НЕ Активы.ПометкаУдаления""")
    return rows[0]["Наименование"].strip()


def make_row(fo, trade_id, fund, client):
    row = fo.NewObject("Структура")
    for name, value in [("MV", 1000150.5), ("MX_Code", trade_id), ("Source", "CALIPSO"),
                        ("ContrPartyName", "TEST BANK"), ("Fund", fund), ("BenefitID", client),
                        ("BenefitName", "Тестовый клиент <" + client + "> & Ко"), ("Qty", 1000000.0),
                        ("InterestRate", 12.75), ("ProductDescription", "Deposit.Fixed"),
                        ("OpenDate", stand_common.date_1c(fo, datetime.datetime(2026, 10, 1))),
                        ("MaturityDate", "2026-12-31"),
                        ("DatePosition", stand_common.date_1c(fo, datetime.datetime(2026, 11, 4)))]:
        row.Вставить(name, value)
    return row


def main():
    fo = stand_common.connect("wim_fo")
    obj = fo.ВнешниеОбработки.Создать(EPF, False)
    results = []

    sample = find_dev_subportfolio(fo)
    temp_ref = None
    if sample is None:
        # На dev таких субпортфелей нет: временный субпортфель T9742 в первом портфеле, после прогона удаляется.
        portfolio = stand_common.query(fo, """
            ВЫБРАТЬ ПЕРВЫЕ 1 Портфели.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК Портфели
            ГДЕ НЕ Портфели.ПометкаУдаления""")[0]["Ссылка"]
        trade_found = 987654321
        part = to_base36(trade_found)
        code = f"T9742-D{part}-"
        item = fo.Справочники.Субпортфели.СоздатьЭлемент()
        item.Наименование = "T9742 тест депозита Calipso"
        item.КодСчета = code
        item.Портфель = portfolio
        item.ОбменДанными.Загрузка = True
        item.Записать()
        temp_ref = item.Ссылка
        print("создан временный субпортфель", code)
    else:
        code, part, trade_found = sample
    try:
        run_checks(fo, obj, results, code, part, trade_found)
    finally:
        if temp_ref is not None:
            temp_object = temp_ref.ПолучитьОбъект()
            temp_object.ОбменДанными.Загрузка = True  # подписки ПриЗаписи на dev падают без обработчика
            temp_object.Удалить()
            print("временный субпортфель удален")
    failed = [name for name, passed in results if not passed]
    print(f"Итог: {len(results) - len(failed)}/{len(results)} пройдено")


def run_checks(fo, obj, results, code, part, trade_found):
    fund = currency_with_asset(fo)
    print(f"dev: субпортфель с кодом счета {code}, часть {part} = сделка {trade_found}; валюта {fund}")

    rows = fo.NewObject("Массив")
    rows.Добавить(make_row(fo, 999999999999, fund, "CLIENT_NF"))
    rows.Добавить(make_row(fo, trade_found, fund, "CLIENT_OK"))
    rows.Добавить(make_row(fo, 123456, "ZZZ_НЕТ_ВАЛЮТЫ", "CLIENT_CUR"))
    rows.Добавить(make_row(fo, 0, fund, "CLIENT_ZERO"))
    reading = fo.NewObject("Структура")
    reading.Вставить("Строки", rows)
    reading.Вставить("Ошибка", "")
    reading.Вставить("Способ", "проверка на dev (синтетические строки)")

    report = obj.СформироватьОтчет(reading)
    html = report.HTML
    summary = report.Сводка
    print(summary)

    def check(name, passed):
        results.append((name, passed))
        print(("OK   " if passed else "FAIL ") + name)

    check("депозитов 4, найдено 1", report.Депозитов == 4 and report.Найдено == 1)
    check("маска найденного = -D" + part + "-", f"-D{part}-" in html and "Найден: портфель" in html
          and "Найден: портфель ," not in html)
    check("несуществующий номер: не найден",
          "содержит -D" + to_base36(999999999999) + "-" in html)
    check("неизвестная валюта: депозит пропускается", "не найдена валюта с наименованием" in html)
    check("нулевой номер: поиск не выполняется", "не удалось перевести" in html)
    check("экранирование HTML", "&lt;CLIENT_OK&gt; &amp; Ко" in html and "<CLIENT_OK>" not in html)
    check("строки упорядочены по номеру сделки", html.find("CLIENT_ZERO") < html.find("CLIENT_CUR")
          < html.find("CLIENT_OK") < html.find("CLIENT_NF"))
    check("дата строкой из SQL переведена в дд.мм.гггг", "31.12.2026" in html and "2026-12-31" not in html)
    check("в HTML нет путей и служебных слов", not any(w in html for w in ("C:\\", "file://", "Claude", "MCP", "Т-1")))

    os.makedirs(REPORTS, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(REPORTS, f"calipso_report_dev_{stamp}.html")
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(html)
    print("HTML:", out)

    started = time.time()
    server_reading = obj.ПрочитатьДепозитыCalipso()
    elapsed = time.time() - started
    error = server_reading.Ошибка
    print(f"Чтение Calipso с сервера 1С dev: {elapsed:.1f} с, строк {server_reading.Строки.Количество()}, "
          f"ошибка: {error}")
    server_reading.Вставить("Способ", "с сервера 1С")
    error_report = obj.СформироватьОтчет(server_reading)
    if error:
        check("ошибка подключения: HTML пустой, в сводке подсказка",
              error_report.HTML == "" and "Включите флажок подключения" in error_report.Сводка)
        server_reading.Вставить("Способ", "с компьютера пользователя")
        client_report = obj.СформироватьОтчет(server_reading)
        check("ошибка с компьютера пользователя: подсказка выключить флажок",
              client_report.HTML == "" and "Выключите флажок" in client_report.Сводка)
    else:
        check("чтение Calipso с dev прошло, отчет сформирован", error_report.HTML != "")


if __name__ == "__main__":
    main()
