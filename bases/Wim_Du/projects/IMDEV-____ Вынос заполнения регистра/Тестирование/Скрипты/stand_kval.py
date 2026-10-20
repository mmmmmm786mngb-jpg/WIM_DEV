"""Стенд заполнения ИсторияСтатусаЦБДляКвалИнвестора на dev-базе WIM_DU (вход по ОС, COM).

Команды:
  info     - сколько бумаг обработает обработчик (всего и тестовых T_KVAL)
  prepare  - создать тестовые бумаги, активы и версии (объем ~1/10 PROD)
  run      - прогоны: обработчик как есть, его копия по этапам, новый по этапам, новый как в рабочем коде,
             новый с записью набором по активу;
             перед каждым регистр по тестовым активам очищается, после - снимок для сверки
Результат run пишется в Тестирование/Результаты/stand_kval_<время>.json.
"""
import datetime as dt
import json
import pathlib
import sys

import win32com.client

ROOT = pathlib.Path(__file__).resolve().parents[1]
EPF = ROOT / "Обработки" / "СтендКвал.epf"
RESULTS = ROOT / "Результаты"
CONN = 'Srvr="localhost";Ref="WIM_DU";'


def connect():
    c = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    protection = c.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    return c, c.ВнешниеОбработки.Создать(str(EPF), False, protection)


def as_dict(c, struct):
    out = {}
    for key in ("Всего,Запрос,Распаковка,Разбор,РазборВерсии,Срез,Запись,Регистр,"
                "Версий,ВызововРегистра,Записей,Ошибок").split(","):
        out[key] = getattr(struct, key)
    return out


def cmd_info(c, stand):
    info = stand.СоставПрогона()
    print(f"бумаг в прогоне: {info.Всего}, тестовых: {info.Тестовых}, версий: {info.Версий}, байт: {info.Байт}")


def cmd_prepare(c, stand):
    params = c.NewObject("Структура")
    params.Вставить("Облигаций", 190)
    params.Вставить("Акций", 100)
    params.Вставить("Паев", 14)
    params.Вставить("Зерно", 7)
    res = stand.СоздатьДанные(params)
    print(f"создано бумаг: {res.Бумаг}, версий: {res.Версий}, байт: {res.Байт}, "
          f"средний размер версии: {res.Байт / max(res.Версий, 1):.0f} Б, время: {res.Мс / 1000:.1f} с")


def snapshot(stand):
    snap = stand.СнимокРегистра()
    return snap.ЧислоЗаписей, snap.Записи


def cmd_run(c, stand, only=None):
    info = stand.СоставПрогона()
    if info.Всего != info.Тестовых:
        raise SystemExit(f"в базе есть не тестовые бумаги для обработчика ({info.Всего} против {info.Тестовых})")
    result = {"время": dt.datetime.now().isoformat(timespec="seconds"),
              "бумаг": info.Всего, "версий": info.Версий, "байт": info.Байт, "прогоны": {}}
    snaps = {}
    runs = [("старый_как_есть", lambda: {"Всего": stand.ПрогонОбработчика()}),
            ("старый_по_этапам", lambda: as_dict(c, stand.ПрогонСтарогоПоЭтапам())),
            ("новый_по_этапам", lambda: as_dict(c, stand.ПрогонНового(True))),
            ("новый_как_в_коде", lambda: as_dict(c, stand.ПрогонНового(False))),
            ("новый_набором", lambda: as_dict(c, stand.ПрогонНовогоНабором()))]
    for name, func in runs:
        if only and name not in only:
            continue
        removed = stand.ОчиститьРегистр()
        timing = func()
        count, records = snapshot(stand)
        snaps[name] = records
        timing["записей_в_регистре"] = count
        timing["удалено_перед_прогоном"] = removed
        result["прогоны"][name] = timing
        print(name, json.dumps(timing, ensure_ascii=False))
    base = next(iter(snaps.values()))
    result["сверка"] = {name: records == base for name, records in snaps.items()}
    print("сверка с первым прогоном:", result["сверка"])
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"stand_kval_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (RESULTS / (out.stem + "_снимок.txt")).write_text(base, encoding="utf-8")
    print("результат:", out)


def main():
    cmd = sys.argv[1]
    c, stand = connect()
    if cmd == "info":
        cmd_info(c, stand)
    elif cmd == "prepare":
        cmd_prepare(c, stand)
    elif cmd == "run":
        cmd_run(c, stand, set(sys.argv[2:]) or None)
    else:
        raise SystemExit("команды: info, prepare, run [имена прогонов]")


if __name__ == "__main__":
    main()
