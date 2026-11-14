#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Общие функции стенда замеров уровня 5.

Подключение берется из реестра баз. Пароли в этот модуль не записываются.
"""

import json
import os

import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(HERE))
# Реестр баз: рядом с WIM_DEV-раскладкой, иначе фиксированный путь WIM_DEV (запуск из TestProject)
_REGISTRY_CANDIDATES = (
    os.path.normpath(os.path.join(PROJECT_DIR, "..", "..", "..", "..", ".v8-project.json")),
    r"C:\1c\Cursor_1c\WIM_DEV\.v8-project.json",
)
REGISTRY = next((p for p in _REGISTRY_CANDIDATES if os.path.exists(p)), _REGISTRY_CANDIDATES[-1])
STATE_FILE = os.path.join(HERE, "state.json")
PREFIX = "T5L5"
PROBE_KEY = "СтендУровень5.Проба"
CONSTANT_NAME = "ВыполнятьЗамерыПроизводительности"


def registry_db(base_id):
    with open(REGISTRY, encoding="utf-8") as handle:
        registry = json.load(handle)
    return next(item for item in registry["databases"] if item["id"] == base_id)


def connect(base_id):
    """Внешнее соединение с базой из реестра. base_id: wim_fo или wim_mo."""
    pythoncom.CoInitialize()
    db = registry_db(base_id)
    base = "Srvr='%s';Ref='%s';" % (db["server"], db["ref"])
    variants = [base + "Locale=ru_RU;"]
    if db.get("user"):
        with_user = base + "Usr='%s';Pwd='%s';Locale=ru_RU;" % (db["user"], db.get("password", ""))
        variants.insert(0 if base_id != "wim_mo" else 1, with_user)
    connector = win32com.client.Dispatch("V83.COMConnector")
    last_error = None
    for variant in variants:
        try:
            return connector.Connect(variant)
        except Exception as error:
            last_error = error
    raise last_error


def query_rows(conn, text, params=None):
    request = conn.NewObject("Запрос")
    request.Текст = text
    for name, value in (params or {}).items():
        request.УстановитьПараметр(name, value)
    table = request.Выполнить().Выгрузить()
    columns = [table.Колонки.Получить(i).Имя for i in range(table.Колонки.Количество())]
    rows = []
    for index in range(table.Количество()):
        row = table.Получить(index)
        rows.append({column: row.Получить(pos) for pos, column in enumerate(columns)})
    return rows


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)


def run_epf_method_bg(conn, epf_path, method, timeout=1800, job_key="T5L5LOAD"):
    """Фоновое задание ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки.

    Нужен серверный контекст: во внешнем соединении недоступны модули с
    ВнешнееСоединение=Ложь (подписка УК_* на запись ДополнительныхСведений).
    Возвращает (состояние_строкой, текст_ошибки_или_пусто).
    """
    import time
    call = conn.NewObject("Структура")
    inner = conn.NewObject("Структура")
    call.Вставить("ЭтоВнешняяОбработка", True)
    call.Вставить("ИмяОбработки", epf_path)
    call.Вставить("ИмяМетода", method)
    call.Вставить("ПараметрыВыполнения", inner)
    address = conn.ПоместитьВоВременноеХранилище("", conn.NewObject("УникальныйИдентификатор"))
    args = conn.NewObject("Массив")
    args.Добавить(call)
    args.Добавить(address)
    job = conn.ФоновыеЗадания.Выполнить(
        "ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", args, None, job_key)
    uid = job.УникальныйИдентификатор
    active = conn.СостояниеФоновогоЗадания.Активно
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = conn.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.Состояние != active:
            break
        time.sleep(3)
    error = ""
    if job.ИнформацияОбОшибке is not None:
        error = conn.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
    return conn.String(job.Состояние), error
