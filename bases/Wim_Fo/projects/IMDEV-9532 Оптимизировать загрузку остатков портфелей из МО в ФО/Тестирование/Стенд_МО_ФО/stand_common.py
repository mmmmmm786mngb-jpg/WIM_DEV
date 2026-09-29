# -*- coding: utf-8 -*-
"""Общие настройки и функции стенда тестовой выгрузки остатков МО -> ФО (IMDEV-9532).

Стенд работает на разработческих базах локального сервера 1С: WIM_MO и WIN_FO_server.
ФО опубликована на http://localhost/win_fo, МО-обработка вызывает ее веб-сервис Avancore.
Все тестовые объекты имеют код или наименование с префиксом PREFIX, чтобы их можно было найти и удалить.
Параметры подключения берутся из реестра баз .v8-project.json (пароли в код не пишутся).
"""
import datetime
import json
import os
import sys

import pythoncom
import win32com.client

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(os.path.dirname(HERE))
REGISTRY = r"C:\1c\Cursor_1c\WIM_DEV\.v8-project.json"

PREFIX = "T9532"
N_PORTFOLIOS = 450
PACKET_SIZE = 45
SHARES = 3
TEST_DATE = datetime.datetime(2026, 9, 29)
WS_BASE = "http://localhost/win_fo"
WS_NAME = "avancore_ws"
EXTERNAL_IB_NAME = f"{PREFIX} ФО стенд"
EPF_DIR = os.path.join(HERE, "epf")
MO_EPF = os.path.join(EPF_DIR, "внВыгрузкаОстатковМО_ФО.epf")
RESULTS_DIR = os.path.join(HERE, "results")
STATE_FILE = os.path.join(HERE, "state.json")

FLAG_POSITION = "Лимиты позиция_выгружена"
FLAG_RECALC = "Лимиты требуется_перерасчет_РСА"
FLAG_ERRORS = "Лимиты есть_ошибки_выгрузки_позиции"
DATE_RECALC = "Лимиты дата_пересчета_РСА"
FLAG_KEYS = [FLAG_POSITION, FLAG_RECALC, FLAG_ERRORS]

FO_EPFS = ["внУдалениеБлокировок", "внПерерасчетСтоимостиФактическойПозицииИ_РСА_СЧА", "внОперацииПослеОбмена"]


def mandate_code(i):
    return f"{PREFIX}_{i:04d}"


def account_code(i, kind):
    return f"{mandate_code(i)}_{kind}"


def share_code(k):
    return f"{PREFIX}_SH{k}"


def _registry_db(base_id):
    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)
    return next(d for d in registry["databases"] if d["id"] == base_id)


def connect(base_id):
    """Открывает внешнее соединение с базой из реестра. base_id: wim_mo или wim_fo."""
    pythoncom.CoInitialize()
    db = _registry_db(base_id)
    base = f"Srvr='{db['server']}';Ref='{db['ref']}';"
    variants = [base + "Locale=ru_RU;"]
    if db.get("user"):
        with_user = base + f"Usr='{db['user']}';Pwd='{db.get('password', '')}';Locale=ru_RU;"
        # В WIM_MO нет пользователей ИБ: сначала пробуем без пользователя.
        variants.insert(1 if base_id == "wim_mo" else 0, with_user)
    connector = win32com.client.Dispatch("V83.COMConnector")
    last_error = None
    for variant in variants:
        try:
            return connector.Connect(variant)
        except Exception as error:  # noqa: BLE001 - перебор вариантов подключения
            last_error = error
    raise last_error


def query(conn, text, params=None):
    """Выполняет запрос 1С и возвращает список словарей с сырыми значениями COM."""
    table = query_table(conn, text, params)
    columns = [table.Колонки.Получить(i).Имя for i in range(table.Колонки.Количество())]
    rows = []
    for i in range(table.Количество()):
        row = table.Получить(i)
        rows.append({c: row.Получить(j) for j, c in enumerate(columns)})
    return rows


def query_table(conn, text, params=None):
    """Выполняет запрос 1С и возвращает ТаблицуЗначений (для загрузки в табличные части)."""
    q = conn.NewObject("Запрос")
    q.Текст = text
    for name, value in (params or {}).items():
        q.УстановитьПараметр(name, value)
    return q.Выполнить().Выгрузить()


def to_array(conn, values):
    """Массив 1С из списка значений Python/COM."""
    array = conn.NewObject("Массив")
    for value in values:
        array.Добавить(value)
    return array


def date_1c(conn, value):
    """Дата 1С из datetime Python. Через XMLЗначение, а не VT_DATE: pywin32 считает дату без часового пояса
    местным временем и переводит ее в UTC, из-за чего дата в 1С сдвигается на смещение пояса."""
    date_type = conn.NewObject("ОписаниеТипов", "Дата").Типы().Получить(0)
    return conn.XMLЗначение(date_type, value.strftime("%Y-%m-%dT%H:%M:%S"))


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def now_stamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
