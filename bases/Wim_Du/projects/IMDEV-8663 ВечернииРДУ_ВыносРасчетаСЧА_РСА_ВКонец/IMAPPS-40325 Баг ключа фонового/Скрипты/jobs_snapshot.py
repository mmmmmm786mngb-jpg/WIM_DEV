# -*- coding: utf-8 -*-
"""IMAPPS-40325: снимок фоновых заданий порций регламента (ключ IM8663_...) - активные и недавние."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stand
c = stand.connect()
for attempt in range(int(sys.argv[1]) if len(sys.argv) > 1 else 1):
    jobs = c.ФоновыеЗадания.ПолучитьФоновыеЗадания()
    rows = []
    for i in range(jobs.Количество()):
        j = jobs.Получить(i)
        key = str(j.Ключ)
        if key.startswith('IM8663_'):
            rows.append((str(j.Начало), str(j.Состояние), key, str(j.Наименование)))
    print('--- снимок', attempt + 1, 'порций:', len(rows))
    for r in sorted(rows):
        print(' | '.join(r))
    sys.stdout.flush()
sys.stdout.flush(); os._exit(0)
