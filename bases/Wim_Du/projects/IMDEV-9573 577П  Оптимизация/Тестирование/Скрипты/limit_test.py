# Проверка: записывается ли документ 577-П, у которого в одном разделе (7) больше 99 999 строк.
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8")
import stand
c = stand.connect()
o = stand.doc_by_number(c, "T0004").ПолучитьОбъект()
for n in range(1, 12):
    setattr(o, f"ВыгружатьРаздел{n}", n == 7)
t = time.time(); o.ЗаполнитьОтчет(); print("fill", round(time.time() - t, 1), "s, Раздел7 =", o.Раздел7.Количество())
o.ОбменДанными.Загрузка = True
try:
    t = time.time(); o.Записать(); print("write OK", round(time.time() - t, 1), "s")
except Exception as e:
    print("write ERROR:", str(e)[:600])
sys.stdout.flush(); os._exit(0)
