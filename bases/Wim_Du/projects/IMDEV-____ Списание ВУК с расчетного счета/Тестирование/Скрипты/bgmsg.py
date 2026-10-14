# -*- coding: utf-8 -*-
"""Сообщения пользователю из фоновых заданий порций (по наименованию задания), за последние N минут.

python bgmsg.py <подстрока наименования> [минут]
"""
import datetime as dt
import os
import sys

import stand


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    c = stand.connect()
    name = sys.argv[1]
    minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    flt = c.NewObject("Структура")
    flt.Вставить("Начало", stand.date_1c(c, dt.datetime.now() - dt.timedelta(minutes=minutes)))
    jobs = c.ФоновыеЗадания.ПолучитьФоновыеЗадания(flt)
    seen = 0
    for i in range(jobs.Количество()):
        j = jobs.Получить(i)
        if name not in j.Наименование:
            continue
        seen += 1
        msgs = j.ПолучитьСообщенияПользователю(False)
        texts = [msgs.Получить(k).Текст.replace("\n", " | ") for k in range(msgs.Количество())] if msgs else []
        print(j.Наименование, "|", c.String(j.Состояние), "| сообщений", len(texts))
        for t in texts[:6]:
            print("   ", t[:400])
    print("заданий:", seen)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
