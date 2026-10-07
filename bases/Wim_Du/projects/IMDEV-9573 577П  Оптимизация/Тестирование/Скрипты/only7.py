# Оставляет в документах только раздел 7 (ВыгружатьРаздел7), для T0009 сразу заполняет на сервере и записывает.
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8")
import stand
c = stand.connect()
for num in ["T0009", "T0010", "T0011"]:
    o = stand.doc_by_number(c, num).ПолучитьОбъект()
    for n in range(1, 12):
        setattr(o, f"ВыгружатьРаздел{n}", n == 7)
    if num == "T0009":
        t = time.time(); o.ЗаполнитьОтчет(); print(num, "fill", round(time.time() - t, 1), "s, Раздел7 =", o.Раздел7.Количество())
    o.ОбменДанными.Загрузка = True
    o.Записать()
    print(num, "записан, Раздел7 =", o.Раздел7.Количество())
sys.stdout.flush(); os._exit(0)
