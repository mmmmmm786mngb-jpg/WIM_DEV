# -*- coding: utf-8 -*-
"""Стенд: зарегистрировать потоковую обработку CSV в справочнике ДополнительныеОтчетыИОбработки
(безопасный режим выключен, вид ЗаполнениеОбъекта) для фонового запуска штатным путем БСП.
Повторный запуск обновляет файл обработки в той же карточке. Тестовый объект стенда, удалить после проверок.

python register_epf.py
"""
import os
import sys

import stand

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
NEW_EPF = os.path.join(TASK, "csv_РабочийКод", "СформироватьВыгрузкуCSVПоток.epf")
NAME = "T9573 Выгрузка CSV 577-П поток (стенд)"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    conn = stand.connect()
    found = conn.Справочники.ДополнительныеОтчетыИОбработки.НайтиПоНаименованию(NAME, True)
    obj = found.ПолучитьОбъект() if not found.Пустая() else conn.Справочники.ДополнительныеОтчетыИОбработки.СоздатьЭлемент()
    obj.Наименование = NAME
    obj.ИмяОбъекта = "СформироватьВыгрузкуCSVПоток"
    obj.ИмяФайла = "СформироватьВыгрузкуCSVПоток.epf"
    obj.Версия = "2.00"
    obj.Вид = conn.Перечисления.ВидыДополнительныхОтчетовИОбработок.ЗаполнениеОбъекта
    obj.Публикация = conn.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    obj.БезопасныйРежим = False
    obj.ХранилищеОбработки = conn.NewObject("ХранилищеЗначения", conn.NewObject("ДвоичныеДанные", NEW_EPF))
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    print("зарегистрирована", conn.String(obj.Ссылка), conn.ПолучитьНавигационнуюСсылку(obj.Ссылка))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
