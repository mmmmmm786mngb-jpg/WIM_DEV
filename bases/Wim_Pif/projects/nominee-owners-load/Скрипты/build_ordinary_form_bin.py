#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch ordinary Form.bin in-place: empty controls, BeforeOpen opens managed form."""

from pathlib import Path

SRC = Path(
    r"bases/Wim_Pif/projects/IMAPPS-36058 ПИФ Тест"
    r"/МногопоточноеПерепроведение58/Forms/ФормаОбычная/Ext/Form.bin"
)
DEST = Path(
    r"bases/Wim_Pif/projects/nominee-owners-load/src"
    r"/ЗаполнениеСпискаВладельцевНД/Forms/ФормаОбычная/Ext/Form.bin"
)

MODULE = (
    "\ufeff\r\n"
    "Процедура ПередОткрытием(Отказ, СтандартнаяОбработка)\r\n"
    "\r\n"
    "    Отказ = Истина;\r\n"
    "    ИмяОбработки = Метаданные().Имя;\r\n"
    "    ПутьКФайлу = ИспользуемоеИмяФайла;\r\n"
    "    Если ЗначениеЗаполнено(ПутьКФайлу) Тогда\r\n"
    "        ИмяОбработки = ВнешниеОбработки.Подключить(ПутьКФайлу, , Ложь);\r\n"
    "    КонецЕсли;\r\n"
    "    ОткрытьФорму(\"ВнешняяОбработка.\" + ИмяОбработки + \".Форма.Форма\");\r\n"
    "\r\n"
    "КонецПроцедуры\r\n"
    "\r\n"
    "Процедура КнопкаВыполнитьНажатие(Элемент)\r\n"
    "КонецПроцедуры\r\n"
    "\r\n"
    "Процедура РежимПерепроведенияСделокПриИзменении(Элемент)\r\n"
    "КонецПроцедуры\r\n"
)


def pad(data, size):
    if len(data) > size:
        raise RuntimeError("payload %s longer than slot %s" % (len(data), size))
    fill = size - len(data)
    return data + (b"\r\n" * (fill // 2) + b" " * (fill % 2))


def replace_slot(blob, marker, new_payload):
    idx = blob.find(marker)
    if idx < 0:
        raise RuntimeError("marker not found")
    line_end = blob.find(b"\r\n", idx)
    size = int(marker.split()[0], 16)
    start = line_end + 2
    padded = pad(new_payload, size)
    return blob[:start] + padded + blob[start + size:]


def strip_controls(form_payload):
    text = form_payload.decode("utf-8")
    bom = ""
    if text.startswith("\ufeff"):
        bom = "\ufeff"
        text = text[1:]
    ctrl = text.find("{10,")
    evt = text.find("{59d6c227-97d3-46f6-84a0-584c5a2807e1")
    if ctrl < 0 or evt < 0:
        raise RuntimeError("cannot find controls/events")
    text = text[:ctrl] + "{10,\r\n{e69bf21d-97b2-4f37-86db-675aea9ec2cb,0}\r\n},\r\n" + text[evt:]
    text = text.replace(
        '{"ru","Обработка  Многопоточное перепроведение документов 58 счета"}',
        '{"ru","Заполнение списка владельцев НД"}',
    )
    return (bom + text).encode("utf-8")


def main():
    blob = SRC.read_bytes()
    mod_marker = b"000005b7 000005b7 7fffffff"
    blob = replace_slot(blob, mod_marker, MODULE.encode("utf-8"))
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(blob)
    print("OK size=%s" % len(blob))


if __name__ == "__main__":
    main()
