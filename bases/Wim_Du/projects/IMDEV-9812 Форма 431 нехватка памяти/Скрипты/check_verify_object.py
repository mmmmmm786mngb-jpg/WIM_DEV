# Проверка модуля объекта Верификация431 на стенде dev: РасчетВерсии107 и РасчетВерсии108 на 2000 мандатах
# (обычная и особая стратегия), сравнение доходности по каждому мандату.
import os
import sys
from datetime import datetime
from decimal import Decimal

import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
EPF = os.path.join(os.path.dirname(HERE), "Верификация", "Верификация431.epf")


def main():
    keys = [l.strip() for l in open(os.path.join(HERE, "stand_mandates.txt"), encoding="utf-8") if l.strip()]
    du = win32com.client.Dispatch("V83.COMConnector").Connect('Srvr="localhost";Ref="WIM_DU";')
    mo = win32com.client.Dispatch("V83.COMConnector").Connect('Srvr="localhost";Ref="WIM_MO";')
    obj = du.ВнешниеОбработки.Создать(EPF, False)
    obj.УстановитьНастройки(False, True, False, True, 500)
    arr = mo.NewObject("Массив")
    refs = du.NewObject("Массив")
    for k in keys:
        r = mo.Справочники.Мандаты.ПолучитьСсылку(mo.NewObject("УникальныйИдентификатор", k))
        arr.Добавить(r)
        refs.Добавить(r)
    strat = mo.Справочники.Стратегии.ПустаяСсылка()  # None из Python приходит в 1С как Null, а не Неопределено
    for special in (False, True):
        r7 = obj.РасчетВерсии107(mo, arr, refs, strat, datetime(2026, 1, 1), datetime(2026, 10, 31), special)
        r8 = obj.РасчетВерсии108(mo, arr, refs, strat, datetime(2026, 1, 1), datetime(2026, 10, 31), special)
        d7 = {k: Decimal(du.XMLСтрока(r7.Доходности.Получить(k))) for k in keys}
        d8 = {k: Decimal(du.XMLСтрока(r8.Доходности.Получить(k))) for k in keys}
        bad = sum(1 for k in keys if d7[k] != d8[k])
        nz = sum(1 for k in keys if d7[k] != 0)
        print(f"особая={special}: мандатов {len(keys)}, ненулевых {nz}, расхождений {bad}; 1.07 строк {r7.СтрокTWR} "
              f"TWR {r7.СекTWR:.1f} с + сбор {r7.СекСбора:.1f} с; 1.08 пачек {r8.Пачек}, {r8.Сек:.1f} с")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
