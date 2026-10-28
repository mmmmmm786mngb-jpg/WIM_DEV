# -*- coding: utf-8 -*-
"""Проверка расширения ПИФ_ДепозитыОдноЧтение на dev ПИФ (WIM_PIF): ответ getDeposits до и после.

    python test_pif_deposits_ext.py state                      - расширения базы и их активность
    python test_pif_deposits_ext.py set <Имя> <on|off> [safe]  - включить/выключить расширение (safe - снять безопасный режим)
    python test_pif_deposits_ext.py call <метка> [YYYY-MM-DD]  - вызвать getDeposits по SOAP, ответ в reports/getDeposits_<метка>.xml
    python test_pif_deposits_ext.py compare <метка1> <метка2>  - построчная сверка двух ответов по всем полям

Подключение COM и учетная запись SOAP берутся из реестра баз C:\\1c\\Cursor_1c\\WIM_DEV\\.v8-project.json (id wim_pif).
"""
import base64
import datetime
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
REPORTS = os.path.join(HERE, "reports")
STAND = os.path.join(os.path.dirname(PROJECT), "IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО",
                     "Тестирование", "Стенд_МО_ФО")
sys.path.insert(0, STAND)
import stand_common  # noqa: E402

URL = "http://localhost/wim_pif/ws/deposits"
NS = "http://www.avancore.ru/deposits"


def registry_db():
    return stand_common._registry_db("wim_pif")


def extensions(conn):
    return {e.Имя: e for e in conn.РасширенияКонфигурации.Получить()}


def cmd_state():
    conn = stand_common.connect("wim_pif")
    for name, ext in extensions(conn).items():
        print("%-25s активно=%s безопасный=%s версия=%s" % (name, ext.Активно, ext.БезопасныйРежим, ext.Версия))


def cmd_set(name, flag, safe_off=False):
    conn = stand_common.connect("wim_pif")
    ext = extensions(conn)[name]
    ext.Активно = flag == "on"
    if safe_off:
        ext.БезопасныйРежим = False
    ext.Записать()
    print("%s: активно=%s безопасный=%s" % (name, ext.Активно, ext.БезопасныйРежим))


def cmd_call(label, day):
    db = registry_db()
    envelope = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:d="%s">'
                '<soap:Body><d:getDeposits><d:ДатаВх>%s</d:ДатаВх></d:getDeposits></soap:Body></soap:Envelope>'
                % (NS, day))
    token = base64.b64encode(("%s:%s" % (db["user"], db.get("password", ""))).encode("utf-8")).decode("ascii")
    request = urllib.request.Request(URL, data=envelope.encode("utf-8"), headers={
        "Content-Type": "text/xml; charset=utf-8", "SOAPAction": "%s#deposits:getDeposits" % NS,
        "Authorization": "Basic " + token})
    started = time.time()
    with urllib.request.urlopen(request, timeout=3600) as response:
        body = response.read()
    elapsed = time.time() - started
    os.makedirs(REPORTS, exist_ok=True)
    path = os.path.join(REPORTS, "getDeposits_%s.xml" % label)
    with open(path, "wb") as handle:
        handle.write(body)
    print("%s: %.2f с, депозитов %d, файл %s" % (label, elapsed, len(rows(path)), path))


def rows(path):
    root = ET.parse(path).getroot()
    result = []
    for deposit in root.iter("{%s}deposit" % NS):
        result.append({child.tag.split("}")[1]: (child.text or "") for child in deposit})
    return result


def cmd_compare(first, second):
    a = rows(os.path.join(REPORTS, "getDeposits_%s.xml" % first))
    b = rows(os.path.join(REPORTS, "getDeposits_%s.xml" % second))
    canon = lambda items: sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in items)
    ca, cb = canon(a), canon(b)
    print("строк %d / %d" % (len(a), len(b)))
    if ca == cb:
        print("СОВПАДАЕТ: все строки и поля одинаковы")
        return
    only_a = [r for r in ca if r not in cb]
    only_b = [r for r in cb if r not in ca]
    print("РАСХОЖДЕНИЯ: только в %s %d, только в %s %d" % (first, len(only_a), second, len(only_b)))
    for r in (only_a + only_b)[:10]:
        print("  " + r)


def main():
    command = sys.argv[1]
    if command == "state":
        cmd_state()
    elif command == "set":
        cmd_set(sys.argv[2], sys.argv[3], len(sys.argv) > 4 and sys.argv[4] == "safe")
    elif command == "call":
        day = sys.argv[3] if len(sys.argv) > 3 else datetime.date.today().isoformat()
        cmd_call(sys.argv[2], day)
    elif command == "compare":
        cmd_compare(sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
