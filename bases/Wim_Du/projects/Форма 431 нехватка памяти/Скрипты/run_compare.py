# Сверка доходности 1.07 и 1.08 на стенде dev WIM_MO (данные stand_mo.py fill).
# Запуск из каталога Скрипты: python run_compare.py
# Тестовая обработка ..\Тестирование\T431_Сверка.epf = модуль 1.08 + функция Т431_Сверка.
import os
import sys
import time
from datetime import datetime
from decimal import Decimal

import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
EPF = os.path.normpath(os.path.join(HERE, "..", "Тестирование", "T431_Сверка.epf"))
DU = 'Srvr="localhost";Ref="WIM_DU";'
MO = 'Srvr="localhost";Ref="WIM_MO";'
START = datetime(2026, 1, 1)
END = datetime(2026, 10, 31, 23, 59, 59)

# (особая стратегия, размер пачки, дубли)
QUICK = [(False, None, True), (True, None, True)]  # None: пачка по умолчанию (500)
SCENARIOS = [
    (False, 5000, False),
    (False, 5000, True),
    (False, 7, True),
    (True, 5000, False),
    (True, 5000, True),
    (True, 7, True),
    (True, 1, True),
]


def main():
    keys = [l.strip() for l in open(os.path.join(HERE, "stand_mandates.txt"), encoding="utf-8") if l.strip()]
    c = win32com.client.Dispatch("V83.COMConnector").Connect(DU)
    obj = c.ВнешниеОбработки.Создать(EPF, False)
    no_positions = "rows" in sys.argv  # свертка по позициям отключена: проверка построчного пути
    obj.Т431_ОтключитьСверткуПоПозициям(no_positions)
    print("свертка по позициям", "ОТКЛЮЧЕНА" if no_positions else "включена")
    total_bad = 0
    out = []
    for special, size, dups in (QUICK if "quick" in sys.argv else SCENARIOS):
        t = time.time()
        res = obj.Т431_Сверка(MO, ",".join(keys), START, END, special, size, dups)
        dt = time.time() - t
        meta = [l for l in res.split("\n") if l.startswith("#")]
        lines = [meta[0]] + [l for l in res.split("\n") if not l.startswith("#")]
        rows_twr = meta[0].split(";")[1]
        chunks = meta[1].split(";")
        bad = 0
        nonzero = 0
        maxdiff = Decimal(0)
        for l in lines[1:]:
            k, old, new = l.split(";")
            d = abs(Decimal(old) - Decimal(new))
            maxdiff = max(maxdiff, d)
            if Decimal(old) != 0:
                nonzero += 1
            if d != 0:
                bad += 1
                out.append(f"  DIFF {k} old={old} new={new}")
        total_bad += bad
        out.append(f"особая={special} пачка={size} дубли={dups}: мандатов {len(lines)-1}, ненулевых {nonzero}, "
                   f"строк TWR 1.07 {rows_twr}, пачек 1.08 {chunks[1]} (построчно {chunks[3]}), расхождений {bad}, макс.разница {maxdiff}, {dt:.1f} с")
        if special and size in (5000, None) and not dups:
            out.append("  пример: " + " | ".join(lines[1:4]))
    print("\n".join(out))
    print("ИТОГО расхождений:", total_bad)
    sys.exit(1 if total_bad else 0)


if __name__ == "__main__":
    main()
