# -*- coding: utf-8 -*-
"""Стенд IMDEV-9573 на dev-базе WIM_DU (localhost): COM-помощники.

Команды:
  python stand.py info                         - расширения, тестовые объекты
  python stand.py ext <имя> <active> <safe>    - свойства расширения (1/0)
  python stand.py prepare                      - тестовая УК "T9573 УК тест"
  python stand.py rows <N>                     - строк на раздел для генератора (0 - выкл.)
  python stand.py docs                         - тестовые документы 577-П
  python stand.py snap <номер>                 - снимок документа в ../Результаты/snap_<номер>_<метка>.txt
  python stand.py xml <номер>                  - размер и MD5 файла ВыгрузитьОтчет()
  python stand.py dump <номер> <ТЧ>            - построчная выгрузка табличной части
  python stand.py newdoc <номер> [posted]      - документ с тестовой УК, июнь 2026
  python stand.py delete <номер>               - удалить тестовый документ
  python stand.py link <номер>                 - навигационная ссылка документа
COM-скрипты завершаются os._exit: процесс с V83.COMConnector может зависнуть на выходе.
"""
import os
import sys
import time

import win32com.client

CONN_STR = 'Srvr="localhost";Ref="WIM_DU";Usr="";Pwd="";'
UK_NAME = "T9573 УК тест"
DOC = "РО_XBRL6_1_ОтчетПоВнутреннемуУчету_577П"
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Результаты")


def connect():
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN_STR)


def query(conn, text, **params):
    q = conn.NewObject("Запрос")
    q.Текст = text
    for k, v in params.items():
        q.УстановитьПараметр(k, v)
    return q.Выполнить().Выгрузить()


def rows(conn, table, cols):
    return [{c: getattr(table.Получить(i), c) for c in cols} for i in range(table.Количество())]


def uk(conn):
    t = query(conn, "ВЫБРАТЬ К.Ссылка КАК Ссылка ИЗ Справочник.Контрагенты КАК К ГДЕ К.Наименование = &Имя", Имя=UK_NAME)
    return t.Получить(0).Ссылка if t.Количество() else None


def doc_by_number(conn, number):
    t = query(conn, f"ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Документ.{DOC} КАК Д ГДЕ Д.Номер = &Н", Н=number)
    if not t.Количество():
        raise SystemExit(f"нет документа {number}")
    return t.Получить(0).Ссылка


def date_1c(conn, iso):
    date_type = conn.NewObject("ОписаниеТипов", "Дата").Типы().Получить(0)
    return conn.XMLЗначение(date_type, iso)


def cmd_info(conn):
    exts = conn.РасширенияКонфигурации.Получить()
    for i in range(exts.Количество()):
        e = exts.Получить(i)
        print("ext", e.Имя, e.Версия, "Активно=", e.Активно, "БезопасныйРежим=", e.БезопасныйРежим)
    print("UK", conn.String(uk(conn)) if uk(conn) else None)
    print("rows", conn.ХранилищеОбщихНастроек.Загрузить("T9573", "КоличествоСтрок"))
    cmd_docs(conn)


def cmd_ext(conn, name, active, safe):
    exts = conn.РасширенияКонфигурации.Получить()
    for i in range(exts.Количество()):
        e = exts.Получить(i)
        if e.Имя == name:
            e.Активно = active == "1"
            e.БезопасныйРежим = safe == "1"
            protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
            protection.ПредупреждатьОбОпасныхДействиях = False
            e.ЗащитаОтОпасныхДействий = protection
            e.Записать()
            print("ok", e.Имя, e.Активно, e.БезопасныйРежим)
            return
    print("не найдено", name)


def cmd_prepare(conn):
    if uk(conn):
        print("УК уже есть")
        return
    obj = conn.Справочники.Контрагенты.СоздатьЭлемент()
    obj.Наименование = UK_NAME
    obj.УправляющаяКомпания = True
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    print("создана", conn.String(obj.Ссылка))


def cmd_rows(conn, n):
    conn.ХранилищеОбщихНастроек.Сохранить("T9573", "КоличествоСтрок", int(n))
    print("КоличествоСтрок =", conn.ХранилищеОбщихНастроек.Загрузить("T9573", "КоличествоСтрок"))


def cmd_docs(conn):
    t = query(conn, f"""ВЫБРАТЬ Д.Номер КАК Номер, Д.Дата КАК Дата, Д.Проведен КАК Проведен,
        Д.ПометкаУдаления КАК ПометкаУдаления
        ИЗ Документ.{DOC} КАК Д УПОРЯДОЧИТЬ ПО Д.Номер""")
    for r in rows(conn, t, ["Номер", "Дата", "Проведен", "ПометкаУдаления"]):
        print("doc", r)


def cmd_snap(conn, number, label):
    ref = doc_by_number(conn, number)
    t0 = time.time()
    text = conn.T9573Д_Сверка.СнимокДокумента(ref)
    os.makedirs(RES, exist_ok=True)
    path = os.path.join(RES, f"snap_{number.strip()}_{label}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"snap {path} ({time.time() - t0:.1f} s)")
    print("\n".join(l for l in text.splitlines() if l.startswith(("Проведен", "Вложений", "ТЧ."))))


def cmd_xml(conn, number):
    ref = doc_by_number(conn, number)
    t0 = time.time()
    print("xml", conn.T9573Д_Сверка.ХешФайлаВыгрузки(ref), f"({time.time() - t0:.1f} s)")


def cmd_dump(conn, number, ts):
    ref = doc_by_number(conn, number)
    print(conn.T9573Д_Сверка.ВыгрузкаТабличнойЧасти(ref, ts))


def cmd_newdoc(conn, number, posted=""):
    obj = getattr(conn.Документы, DOC).СоздатьДокумент()
    obj.Заполнить(None)
    obj.Дата = date_1c(conn, "2026-10-07T12:00:00")
    obj.Номер = number
    obj.УправляющаяКомпания = uk(conn)
    obj.НачалоПериода = date_1c(conn, "2026-06-01T00:00:00")
    obj.КонецПериода = date_1c(conn, "2026-06-30T00:00:00")
    obj.ПредставлениеПериода = "июнь 2026"
    for n in range(1, 12):
        setattr(obj, f"ВыгружатьРаздел{n}", True)
    obj.НаименованиеПрофУчастника = "T9573 Проф участник"
    obj.ИННПрофУчастника = "7700000000"
    mode = conn.РежимЗаписиДокумента.Проведение if posted else conn.РежимЗаписиДокумента.Запись
    obj.Записать(mode)
    print("создан", conn.String(obj.Ссылка), "Проведен=", obj.Проведен)


def cmd_delete(conn, number):
    obj = doc_by_number(conn, number).ПолучитьОбъект()
    obj.Удалить()
    print("удален", number)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    conn = connect()
    cmd = args[0]
    if cmd == "info":
        cmd_info(conn)
    elif cmd == "ext":
        cmd_ext(conn, *args[1:4])
    elif cmd == "prepare":
        cmd_prepare(conn)
    elif cmd == "rows":
        cmd_rows(conn, args[1])
    elif cmd == "docs":
        cmd_docs(conn)
    elif cmd == "snap":
        cmd_snap(conn, args[1], args[2] if len(args) > 2 else "x")
    elif cmd == "xml":
        cmd_xml(conn, args[1])
    elif cmd == "dump":
        cmd_dump(conn, args[1], args[2])
    elif cmd == "newdoc":
        cmd_newdoc(conn, *args[1:3])
    elif cmd == "link":
        print(conn.ПолучитьНавигационнуюСсылку(doc_by_number(conn, args[1])))
    elif cmd == "delete":
        cmd_delete(conn, args[1])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # COM-ошибки 1С печатаем целиком
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
