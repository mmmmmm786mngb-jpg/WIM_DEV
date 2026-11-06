"""Стенд IM9434_Риск на dev WIM_DU (localhost\\WIM_DU, COM, вход по ОС).

prepare - в два проведенных расчета СЧА/РСА от 12.09.2026 (ДоговорДУ_1, ДоговорДУ_2) добавляет строку таблицы
          РасчетСЧА с показателем-строкой и создает по документу контроля допустимого уровня риска на тот же день;
info    - показывает документы стенда и их ВерсияДанных (по ней видно, перезаписывался ли документ);
cleanup - удаляет документы риска стенда, строки T9434R из таблиц СЧА и сохраненный отбор admin этого списка.
Состояние стенда: stand_9434r_state.json рядом со скриптом.
"""
import datetime
import json
import os
import sys

import win32com.client

CONN = 'Srvr="localhost";Ref="WIM_DU";'
MARK = "T9434R"
BOND = {"ДоговорДУ_1": "T9434R ЗПИФ недвижимости РД", "ДоговорДУ_2": "T9434R Другая бумага"}
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stand_9434r_state.json")
SETTINGS_KEY = ("Обработка.ГрупповоеПерезаполнениеДокументов.Форма.Форма.СписокДокументов"
                "/ТекущиеПользовательскиеНастройки")


def connect():
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN)


def scha_docs(c):
    q = c.NewObject("Запрос")
    q.Текст = ("ВЫБРАТЬ Расчеты.Ссылка КАК Ссылка, ПРЕДСТАВЛЕНИЕ(Расчеты.ДоговорДУ) КАК Договор "
               "ИЗ Документ.РасчетСЧА_РСА КАК Расчеты ГДЕ Расчеты.Проведен "
               "И Расчеты.Дата МЕЖДУ ДАТАВРЕМЯ(2026, 9, 12) И ДАТАВРЕМЯ(2026, 9, 12, 23, 59, 59)")
    v = q.Выполнить().Выбрать()
    out = []
    while v.Следующий():
        out.append((v.Ссылка, v.Договор))
    return out


def ref_by_uuid(c, manager, uid):
    return manager.ПолучитьСсылку(c.NewObject("УникальныйИдентификатор", uid))


def prepare(c):
    state = {"risk": [], "scha": []}
    for ref, contract in scha_docs(c):
        obj = ref.ПолучитьОбъект()
        if not any(MARK in c.String(row.Показатель) for row in obj.РасчетСЧА):
            row = obj.РасчетСЧА.Добавить()
            row.Показатель = BOND.get(contract, MARK + " бумага")
            row.Сумма = 1
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
        state["scha"].append(c.String(ref.УникальныйИдентификатор()))

        risk = c.Документы.КонтрольДопустимогоУровняРиска.СоздатьДокумент()
        risk.Дата = datetime.datetime(2026, 9, 12, 13, 0, 0)
        risk.ДоговорДУ = obj.ДоговорДУ
        risk.ДокументОснование = ref
        try:
            risk.Записать(c.РежимЗаписиДокумента.Проведение)
            posted = True
        except Exception as err:  # проведение может не пройти на данных dev - фиксируем и пишем без проведения
            print("проведение документа риска не прошло:", contract, err)
            risk.Записать(c.РежимЗаписиДокумента.Запись)
            posted = False
        state["risk"].append({"uuid": c.String(risk.Ссылка.УникальныйИдентификатор()),
                              "contract": contract, "posted": posted})
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    info(c)


def info(c):
    if not os.path.exists(STATE):
        print("стенд не подготовлен")
        return
    state = json.load(open(STATE, encoding="utf-8"))
    for uid in state["scha"]:
        ref = ref_by_uuid(c, c.Документы.РасчетСЧА_РСА, uid)
        rows = [c.String(r.Показатель) for r in ref.РасчетСЧА]
        print("СЧА ", ref.Номер, c.String(ref.ДоговорДУ), "проведен", ref.Проведен, "версия", ref.ВерсияДанных,
              "строк", len(rows), [r for r in rows if MARK in r])
    for item in state["risk"]:
        ref = ref_by_uuid(c, c.Документы.КонтрольДопустимогоУровняРиска, item["uuid"])
        print("Риск", ref.Номер, c.String(ref.Дата), c.String(ref.ДоговорДУ), "проведен", ref.Проведен,
              "версия", ref.ВерсияДанных)


def cleanup(c):
    if os.path.exists(STATE):
        state = json.load(open(STATE, encoding="utf-8"))
        for item in state["risk"]:
            ref = ref_by_uuid(c, c.Документы.КонтрольДопустимогоУровняРиска, item["uuid"])
            obj = ref.ПолучитьОбъект()
            if obj is not None:
                obj.ОбменДанными.Загрузка = True
                obj.Удалить()
        for uid in state["scha"]:
            obj = ref_by_uuid(c, c.Документы.РасчетСЧА_РСА, uid).ПолучитьОбъект()
            rows = [r for r in obj.РасчетСЧА if MARK in c.String(r.Показатель)]
            for r in rows:
                obj.РасчетСЧА.Удалить(r)
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
        os.remove(STATE)
    c.ХранилищеСистемныхНастроек.Удалить(SETTINGS_KEY, "", "admin")
    print("стенд убран")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "info"
    {"prepare": prepare, "info": info, "cleanup": cleanup}[action](connect())
