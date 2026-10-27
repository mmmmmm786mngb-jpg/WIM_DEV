# -*- coding: utf-8 -*-
"""IMAPPS-40325: свойства расширения IMAPPS40325 в dev WIM_DU; аргумент safe-off выключает безопасный режим."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stand
c = stand.connect()
for e in c.РасширенияКонфигурации.Получить():
    if e.Имя == 'IMAPPS40325':
        print('до:', e.Имя, e.Версия, 'Активно', e.Активно, 'БезопасныйРежим', e.БезопасныйРежим)
        if len(sys.argv) > 1 and sys.argv[1] == 'safe-off' and e.БезопасныйРежим:
            e.БезопасныйРежим = False
            e.Записать()
            print('безопасный режим выключен')
for e in c.РасширенияКонфигурации.Получить():
    print(e.Имя, e.Версия, 'Активно', e.Активно, 'БезопасныйРежим', e.БезопасныйРежим)
sys.stdout.flush(); os._exit(0)
