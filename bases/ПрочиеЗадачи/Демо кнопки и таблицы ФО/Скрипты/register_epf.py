#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Регистрация обработки FO_ButtonsTablesDemo в справочнике "Дополнительные отчеты и обработки" базы WIN_FO_server.

Создает или обновляет элемент по ИмяОбъекта: хранилище EPF, вид, версия, публикация и таблица команд
из СведенияОВнешнейОбработке(). После регистрации обработка открывается кнопкой "Выполнить" в карточке.
"""
import os, sys, tempfile, shutil
sys.stdout.reconfigure(encoding="utf-8")
import pythoncom, win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
EPF = os.path.join(os.path.dirname(HERE), "build", "FO_ButtonsTablesDemo.epf")
CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
NAME = "FO_ButtonsTablesDemo"


def main():
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)

    # Файл на сервере 1С: копия EPF во временный каталог (сервер и клиент COM на одной машине).
    tmp = os.path.join(tempfile.gettempdir(), NAME + ".epf")
    shutil.copyfile(EPF, tmp)
    processor = conn.ВнешниеОбработки.Создать(tmp, False)
    info = processor.СведенияОВнешнейОбработке()

    query = conn.NewObject("Запрос")
    query.Текст = ("ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                   "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления")
    query.УстановитьПараметр("Имя", NAME)
    sel = query.Выполнить().Выбрать()
    item = sel.Ссылка.ПолучитьОбъект() if sel.Следующий() else conn.Справочники.ДополнительныеОтчетыИОбработки.СоздатьЭлемент()

    item.Наименование = processor.Метаданные().Представление()
    item.ИмяОбъекта = NAME
    item.ИмяФайла = NAME + ".epf"
    item.Версия = info.Версия
    item.БезопасныйРежим = info.БезопасныйРежим
    item.Вид = conn.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
    item.Публикация = conn.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    item.ХранилищеОбработки = conn.NewObject("ХранилищеЗначения", conn.NewObject("ДвоичныеДанные", EPF))

    item.Команды.Очистить()
    for i in range(info.Команды.Количество()):
        src = info.Команды.Получить(i)
        cmd = item.Команды.Добавить()
        cmd.Идентификатор = src.Идентификатор
        cmd.Представление = src.Представление
        cmd.ПоказыватьОповещение = src.ПоказыватьОповещение
        cmd.ВариантЗапуска = conn.Перечисления.СпособыВызоваДополнительныхОбработок.ОткрытиеФормы

    item.ОбменДанными.Загрузка = True
    item.Записать()
    print("OK:", item.Наименование, "| версия", item.Версия, "| команд", item.Команды.Количество(),
          "| ссылка", conn.XMLСтрока(item.Ссылка))
    os.remove(tmp)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
