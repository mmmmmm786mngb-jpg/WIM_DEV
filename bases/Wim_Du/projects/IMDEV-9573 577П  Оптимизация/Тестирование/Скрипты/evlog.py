# События журнала регистрации WIM_DU за интервал (UTC ISO из браузера -> локальное время +3).
import sys, os, datetime
sys.stdout.reconfigure(encoding="utf-8")
import stand
c = stand.connect()
def loc(iso):  # '2026-10-07T08:17:20.747Z' -> локальная строка 1С
    d = datetime.datetime.fromisoformat(iso.replace("Z", "")) + datetime.timedelta(hours=3)
    return d.strftime("%Y-%m-%dT%H:%M:%S")
t = c.NewObject("ТаблицаЗначений")
f = c.NewObject("Структура")
f.Вставить("ДатаНачала", stand.date_1c(c, loc(sys.argv[1])))
f.Вставить("ДатаОкончания", stand.date_1c(c, loc(sys.argv[2])))
c.ВыгрузитьЖурналРегистрации(t, f)
for i in range(t.Количество()):
    r = t.Получить(i)
    print(c.String(r.Дата), r.Событие, c.String(r.Данные)[:60], c.String(r.Комментарий)[:200].replace("\n", " "))
sys.stdout.flush(); os._exit(0)
