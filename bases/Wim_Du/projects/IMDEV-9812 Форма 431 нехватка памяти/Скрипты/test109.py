# Проверка версии 1.09 (ОПТИМИЗИРОВАНО_11112026) на dev:
#   build   - тестовая копия 1.09 + Тестирование\test_harness_109.bsl -> Тестирование\T431_109.epf
#   special [пачка] - доходность особой стратегии 1.09 против 1.07 на мандатах стенда (stand_mandates.txt)
#   queries - запросы ДУ до разделов (в том числе правки IMAPPS-39338) на dev ДУ
#   metric  - запись замера ЗафиксироватьЗамерЗаполнения и чтение ее из регистра ЗамерыВремени
import os
import shutil
import subprocess
import sys
from datetime import datetime
from decimal import Decimal

import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
NAME = "внЗаполнениеРеглОтчетаПоДоговорамДУ_0420431_71"
SRC = os.path.join(TASK, "ОПТИМИЗИРОВАНО_11112026", "src")
DST = os.path.join(TASK, "Тестирование", "T431_109_src")
EPF = os.path.join(TASK, "Тестирование", "T431_109.epf")
DU = 'Srvr="localhost";Ref="WIM_DU";'
MO = 'Srvr="localhost";Ref="WIM_MO";'


def build():
    shutil.rmtree(DST, ignore_errors=True)
    shutil.copytree(SRC, DST)
    p = os.path.join(DST, NAME, "Ext", "ObjectModule.bsl")
    s = open(p, encoding="utf-8-sig").read().replace("\r\n", "\n")
    k = "Перем МассивСоединений;"
    f = "Функция РазмерПорцииМандатовTWR()\n"
    assert s.count(k) == 1 and s.count(f) == 1
    s = s.replace(k, k + "\nПерем Т431_РазмерПорции;", 1)
    s = s.replace(f, f + "\tЕсли Т431_РазмерПорции <> Неопределено Тогда\n\t\tВозврат Т431_РазмерПорции;\n\tКонецЕсли;\n")
    h = open(os.path.join(TASK, "Тестирование", "test_harness_109.bsl"), encoding="utf-8").read()
    s = s.rstrip("\n") + "\n" + h
    open(p, "w", encoding="utf-8-sig", newline="\r\n").write(s)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-File",
                        os.path.expanduser("~/.claude/skills/epf-build/scripts/epf-build.ps1"),
                        "-InfoBaseServer", "localhost", "-InfoBaseRef", "WIM_DU", "-Checks", "off",
                        "-SourceFile", os.path.join(DST, NAME + ".xml"), "-OutputFile", EPF],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-200:], "epf", os.path.exists(EPF))


def special(size):
    keys = [l.strip() for l in open(os.path.join(HERE, "stand_mandates.txt"), encoding="utf-8") if l.strip()]
    du = win32com.client.Dispatch("V83.COMConnector").Connect(DU)
    obj = du.ВнешниеОбработки.Создать(EPF, False)
    for dups in (False, True):
        res = obj.Т431_Особые109(MO, ",".join(keys), datetime(2026, 1, 1), datetime(2026, 10, 31), size, dups)
        lines = res.split("\n")
        meta = {l.split(";")[0]: l.split(";")[1] for l in lines if l.startswith("#")}
        data = [l.split(";") for l in lines if not l.startswith("#")]
        bad = sum(1 for _, o, n in data if Decimal(o) != Decimal(n))
        nz = sum(1 for _, o, n in data if Decimal(o) != 0)
        print(f"особая, пачка {meta['#пачка']}, дубли={dups}: мандатов {len(data)}, ненулевых {nz}, "
              f"строк TWR 1.07 {meta['#строк_TWR_1_07']}, расхождений {bad}")


def queries():
    du = win32com.client.Dispatch("V83.COMConnector").Connect(DU)
    obj = du.ВнешниеОбработки.Создать(EPF, False)
    q = du.NewObject("Запрос")
    q.Текст = ("ВЫБРАТЬ ПЕРВЫЕ 1 Д.УправляющаяКомпания КАК УК, КОЛИЧЕСТВО(*) КАК Кол ИЗ Справочник.ДоговорДУ КАК Д "
               "ГДЕ Д.УправляющаяКомпания <> ЗНАЧЕНИЕ(Справочник.Контрагенты.ПустаяСсылка) "
               "СГРУППИРОВАТЬ ПО Д.УправляющаяКомпания УПОРЯДОЧИТЬ ПО Кол УБЫВ")
    s = q.Выполнить().Выбрать()
    s.Следующий()
    print("УК:", du.String(s.УК), "договоров", s.Кол)
    print(obj.Т431_ЗапросыДУ(s.УК, datetime(2026, 10, 1), datetime(2026, 10, 31)))


def metric():
    du = win32com.client.Dispatch("V83.COMConnector").Connect(DU)
    obj = du.ВнешниеОбработки.Создать(EPF, False)
    print(obj.Т431_ЗамерЗаполнения("Форма431.ТестT431"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "special":
        special(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "queries":
        queries()
    elif cmd == "metric":
        metric()
    elif cmd == "cleanup":
        du = win32com.client.Dispatch("V83.COMConnector").Connect(DU)
        op = du.Справочники.КлючевыеОперации.НайтиПоРеквизиту("Имя", "Форма431.ТестT431")
        if not op.Пустая():
            rs = du.РегистрыСведений.ЗамерыВремени.СоздатьНаборЗаписей()
            rs.Отбор.КлючеваяОперация.Установить(op)
            rs.Записать(True)
            op.ПолучитьОбъект().Удалить()
            print("удалены тестовые замеры и ключевая операция Форма431.ТестT431")
    sys.stdout.flush()
    os._exit(0)
