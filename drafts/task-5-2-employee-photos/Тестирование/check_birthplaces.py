# -*- coding: utf-8 -*-
"""Проверяет таблицу мест рождения в хранилище настроек и запись идентификатора у сотрудника."""

import pythoncom
import win32com.client

CONNECT = "File='C:\\Users\\Acer\\Documents\\1C\\EmployeePhotos';App='PyCOM';Locale=ru_RU;"


def main():
    pythoncom.CoInitialize()
    try:
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONNECT)
        module = conn.МестаРожденияСервер
        places = module.ТаблицаМест()
        print("places", places.Количество())
        regions = module.СписокРегионов()
        print("regions", regions.Количество())
        moscow_id = ""
        for row in places:
            if str(row.Наименование) == "Москва" and str(row.Регион) == "Москва":
                moscow_id = str(row.Идентификатор)
                break
        if not moscow_id:
            raise SystemExit("ERROR moscow row missing")
        card = module.КарточкаМеста(moscow_id)
        region = module.КарточкаРегиона(card.КодРегиона)
        print("moscow region", str(region.Наименование), str(region.Округ))
        if str(region.Округ) != "Центральный":
            raise SystemExit("ERROR district")
        manager = conn.NewObject("СправочникМенеджер.Сотрудники")
        ref = manager.НайтиПоНаименованию("Соколова Мария", True)
        item = ref.ПолучитьОбъект()
        item.ИдентификаторМестаРождения = moscow_id
        item.Записать()
        again = ref.ПолучитьОбъект()
        if str(again.ИдентификаторМестаРождения) != moscow_id:
            raise SystemExit("ERROR id not saved")
        if str(module.ПредставлениеМеста(again.ИдентификаторМестаРождения)) != "Москва":
            raise SystemExit("ERROR presentation")
        print("OK employee link")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
