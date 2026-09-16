#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register NomineeOwnersLoad.epf 1.0.7 in additional processings catalog."""

import os
import pythoncom
import win32com.client

EPF = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "build", "NomineeOwnersLoad.epf"
))
CONN = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
NAME = "ЗаполнениеСпискаВладельцевНД"
TITLE = "Заполнение списка владельцев НД (тонкий клиент)"
OUT = os.path.join(os.path.dirname(__file__), "reports", "form_open", "register.txt")


def com_err(exc):
    try:
        return str(exc.args[2][2])
    except Exception:
        return repr(exc)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = ["epf=" + EPF, "exists=" + str(os.path.isfile(EPF)),
             "size=" + str(os.path.getsize(EPF) if os.path.isfile(EPF) else 0)]
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect(CONN)
        prot = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
        prot.ПредупреждатьОбОпасныхДействиях = False
        proc = conn.ВнешниеОбработки.Создать(EPF, False, prot)
        sved = proc.СведенияОВнешнейОбработке()
        lines.append("sved.version=" + str(sved.Версия))
        lines.append("sved.safe=" + str(sved.БезопасныйРежим))
        md = proc.Метаданные()
        lines.append("default_form=" + md.ОсновнаяФорма.Имя)

        bin_data = conn.NewObject("ДвоичныеДанные", EPF)
        storage = conn.NewObject("ХранилищеЗначения", bin_data)
        q = conn.NewObject("Запрос")
        q.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка, Наименование, Версия, ИмяОбъекта "
            "ИЗ Справочник.ДополнительныеОтчетыИОбработки "
            "ГДЕ ИмяОбъекта = &Имя ИЛИ Наименование ПОДОБНО &Наим"
        )
        q.УстановитьПараметр("Имя", NAME)
        q.УстановитьПараметр("Наим", "%владельцев НД%")
        res = q.Выполнить()
        if res.Пустой():
            cat = conn.NewObject("СправочникМенеджер.ДополнительныеОтчетыИОбработки")
            item = cat.СоздатьЭлемент()
            lines.append("action=create")
        else:
            row = res.Выгрузить()[0]
            item = row.Ссылка.ПолучитьОбъект()
            lines.append("action=update")
            lines.append("old_name=" + str(row.Наименование))
            lines.append("old_ver=" + str(row.Версия))
        item.Наименование = TITLE
        item.ИмяОбъекта = NAME
        item.ИмяФайла = "ЗаполнениеСпискаВладельцевНД.epf"
        item.Версия = "1.0.7"
        item.Вид = conn.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
        item.Публикация = conn.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
        item.БезопасныйРежим = False
        item.ХранилищеОбработки = storage
        item.Информация = "Регистрация автотеста открытия формы 1.0.7"
        if item.Команды.Количество() == 0:
            cmd = item.Команды.Добавить()
            cmd.Представление = TITLE
            cmd.Идентификатор = NAME
            cmd.ВариантЗапуска = conn.Перечисления.СпособыВызоваДополнительныхОбработок.ОткрытиеФормы
            cmd.ПоказыватьОповещение = False
        else:
            item.Команды[0].Представление = TITLE
            item.Команды[0].Идентификатор = NAME
            item.Команды[0].ВариантЗапуска = conn.Перечисления.СпособыВызоваДополнительныхОбработок.ОткрытиеФормы
        item.Записать()
        lines.append("saved=" + conn.String(item.Ссылка))
        lines.append("new_ver=" + str(item.Версия))
        lines.append("commands=" + str(item.Команды.Количество()))
        lines.append("sections=" + str(item.Разделы.Количество()))
        lines.append("OK")
    except Exception as exc:
        lines.append("FAIL")
        lines.append(com_err(exc))
        raise
    finally:
        pythoncom.CoUninitialize()
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
