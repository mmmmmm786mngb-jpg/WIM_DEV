# -*- coding: utf-8 -*-
"""Исходники тестовой обработки T9573_ЗамерCSV: модуль потоковой выгрузки CSV плюс функция Замер
из bench_csv.bsl с вариантами внутреннего цикла. Не для поставки.
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC_XML = os.path.join(ROOT, "src", "СформироватьВыгрузкуCSVПоток.xml")
SRC_BSL = os.path.join(ROOT, "src", "СформироватьВыгрузкуCSVПоток", "Ext", "ObjectModule.bsl")
OUT = os.path.join(ROOT, "Тестирование", "Обработки")
NAME = "T9573_ЗамерCSV"


def main():
    module = open(SRC_BSL, encoding="utf-8-sig").read().replace("\r\n", "\n")
    module += open(os.path.join(HERE, "bench_csv.bsl"), encoding="utf-8-sig").read()
    ext = os.path.join(OUT, NAME, "Ext")
    os.makedirs(ext, exist_ok=True)
    with open(os.path.join(ext, "ObjectModule.bsl"), "w", encoding="utf-8-sig") as f:
        f.write(module)
    tpl = open(SRC_XML, encoding="utf-8-sig").read()
    tpl = re.sub(r"\s*<Attribute uuid.*?</Attribute>", "", tpl, flags=re.S)
    tpl = re.sub(r"\s*<Form>.*?</Form>", "", tpl)
    tpl = re.sub(r"<ChildObjects>\s*</ChildObjects>", "<ChildObjects/>", tpl)
    tpl = re.sub(r"<DefaultForm>.*?</DefaultForm>", "<DefaultForm/>", tpl)
    tpl = tpl.replace("СформироватьВыгрузкуCSVПоток", NAME).replace("Выгрузка CSV 577-П (поток)", "Тест: замер выгрузки CSV 577-П")
    for old in set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", tpl)):
        if old != "c3831ec8-d8d5-4f93-8a22-f9bfae07327f":
            tpl = tpl.replace(old, str(uuid.uuid4()))
    with open(os.path.join(OUT, NAME + ".xml"), "w", encoding="utf-8") as f:
        f.write(tpl)
    print("ok", len(module.splitlines()))


if __name__ == "__main__":
    main()
