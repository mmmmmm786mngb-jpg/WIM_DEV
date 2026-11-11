# Стенд проверки расчета TWR на dev WIM_MO: тестовые рыночные оценки мандатов.
# Записи регистра РыночнаяСтоимостьПозиции пишутся одним набором с фиксированным регистратором
# (ссылка документа РасчетРыночнойСтоимости с UUID стенда, сам документ не создается).
#   python stand_mo.py fill [N] - записать оценки N мандатов (по умолчанию 30), список -> stand_mandates.txt
#   python stand_mo.py clear  - удалить записи стенда (пустой набор по тому же регистратору)
#   python stand_mo.py mandates N - довести число мандатов со счетами до N: тестовые мандаты "T431 тестовый мандат"
#       с кодом T431-NNNN и одним счетом мандата каждый (ОбменДанными.Загрузка и без регистрации в планах обмена:
#       правила регистрации ИсточникиОбмена на dev МО падают)
import random
import sys
from datetime import date, datetime, timedelta

import win32com.client

CONN = 'Srvr="localhost";Ref="WIM_MO";'
RECORDER_UUID = "43100000-0431-0431-0431-000000000431"
START = date(2025, 12, 31)
END = date(2026, 10, 31)
N_DATA = int(sys.argv[2]) if len(sys.argv) > 2 else 30  # мандатов с оценками
N_EMPTY = 3      # мандатов без оценок


def connect():
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN)


def recorder(c):
    uid = c.NewObject("УникальныйИдентификатор", RECORDER_UUID)
    return c.Документы.РасчетРыночнойСтоимости.ПолучитьСсылку(uid)


def mandates(c, n):
    q = c.NewObject("Запрос")
    q.Текст = """ВЫБРАТЬ СМ.Владелец КАК Мандат, МАКСИМУМ(СМ.Ссылка) КАК Счет
        ИЗ Справочник.СчетаМандатов КАК СМ
        ГДЕ НЕ СМ.ПометкаУдаления И НЕ СМ.Владелец.ПометкаУдаления
        СГРУППИРОВАТЬ ПО СМ.Владелец
        УПОРЯДОЧИТЬ ПО СМ.Владелец.Код"""
    s = q.Выполнить().Выбрать()
    res = []
    while s.Следующий() and len(res) < n:
        res.append((s.Мандат, s.Счет))
    return res


def add_mandates(c, total):
    have = len(mandates(c, 100000))
    q = c.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Кол ИЗ Справочник.Мандаты КАК М ГДЕ М.Код ПОДОБНО \"T431-%\""
    s = q.Выполнить().Выбрать(); s.Следующий()
    n = int(s.Кол)
    for i in range(total - have):
        n += 1
        m = c.Справочники.Мандаты.СоздатьЭлемент()
        m.Код = f"T431-{n:04d}"
        m.Наименование = f"T431 тестовый мандат {n:04d}"
        m.ОбменДанными.Загрузка = True
        m.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
        m.Записать()
        a = c.Справочники.СчетаМандатов.СоздатьЭлемент()
        a.Владелец = m.Ссылка
        a.Наименование = f"T431 счет {n:04d}"
        a.ОбменДанными.Загрузка = True
        a.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
        a.Записать()
    print("мандатов со счетами было", have, "добавлено", max(0, total - have))


def series(i, rnd):
    days = (END - START).days + 1
    v = round(rnd.uniform(1e5, 5e6), 2)
    first = 0
    if 10 <= i < 20:
        first = rnd.randint(30, 200)          # мандат появился в середине года
    out = []
    for d in range(days):
        if d < first:
            continue
        v = round(v * (1 + rnd.uniform(-0.01, 0.012)), 2)
        mv = v
        if 20 <= i < 25 and d < first + 15:
            mv = 0                            # первые дни с нулевой оценкой
        if 25 <= i < 30 and rnd.random() < 0.03:
            mv = 0                            # провалы оценки в середине периода
        out.append((START + timedelta(days=d), mv))
    return out


def flows_recorder(c):
    uid = c.NewObject("УникальныйИдентификатор", "43100000-0431-0431-0431-000000000432")
    return c.Документы.Операция.ПолучитьСсылку(uid)


def add_flows(c, n):
    """Вводы-выводы стенда: каждому мандату с оценками - по одному обороту 15-го числа каждого месяца
    (январь-октябрь 2026), сумма от -50 до +100 тысяч рублей. В TWR у такого мандата появляется таблица
    вводов-выводов, дополненная до каждого дня окна, как на PROD."""
    rub = c.Справочники.Валюты.RUB
    rnd = random.Random(432)
    fs = c.РегистрыНакопления.ВводыВыводыВДУ.СоздатьНаборЗаписей()
    fs.Отбор.Регистратор.Установить(flows_recorder(c))
    fs.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
    rows = 0
    for m, acc in mandates(c, n + N_EMPTY)[:n]:
        for month in range(1, 11):
            r = fs.Добавить()
            r.Период = datetime(2026, month, 15)
            r.Мандат = m
            r.СчетМандата = acc
            r.Валюта = rub
            r.Сумма = round(rnd.uniform(-5e4, 1e5), 2)
            rows += 1
    fs.Записать(True)
    print("flows", rows)


def main():
    cmd = sys.argv[1]
    c = connect()
    rs = c.РегистрыСведений.РыночнаяСтоимостьПозиции.СоздатьНаборЗаписей()
    rs.Отбор.Регистратор.Установить(recorder(c))
    if cmd == "mandates":
        add_mandates(c, int(sys.argv[2]))
        return
    if cmd == "flows":
        add_flows(c, N_DATA)
        return
    if cmd == "clearflows":
        fs = c.РегистрыНакопления.ВводыВыводыВДУ.СоздатьНаборЗаписей()
        fs.Отбор.Регистратор.Установить(flows_recorder(c))
        fs.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
        fs.Записать(True)
        print("flows cleared")
        return
    if cmd == "clear":
        rs.Записать(True)
        print("cleared")
        return
    rub = c.Справочники.Валюты.RUB
    rnd = random.Random(431)
    ms = mandates(c, N_DATA + N_EMPTY)
    rows = 0
    for i, (m, acc) in enumerate(ms[:N_DATA]):
        for d, mv in series(i, rnd):
            r = rs.Добавить()
            r.Период = datetime(d.year, d.month, d.day)
            r.Мандат = m
            r.СчетМандата = acc
            r.Сумма = mv
            r.Валюта = rub
            rows += 1
    rs.Записать(True)
    with open("stand_mandates.txt", "w", encoding="utf-8") as f:
        for m, _ in ms:
            f.write(c.XMLСтрока(m) + "\n")
    print("rows", rows, "mandates", len(ms))


if __name__ == "__main__":
    main()
