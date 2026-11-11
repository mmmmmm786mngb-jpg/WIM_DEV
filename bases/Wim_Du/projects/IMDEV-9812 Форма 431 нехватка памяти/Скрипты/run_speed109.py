# Стенд скорости: особая стратегия одним вызовом TWR (версия PROD) против пачек версии 1.09 (1, 2, 4, 8 пачек).
# Каждый вариант - отдельное фоновое задание БСП в dev WIM_DU (карточка "T431 Сверка TWR (стенд)" с файлом
# ..\Тестирование\T431_109.epf, процедура Т431_ЗамерСкорости109), как серверный вызов заполнения.
# Память - пик MemoryCurrent сеанса фонового задания по данным агента кластера (memwatch.py).
#   python run_speed109.py register     - записать T431_109.epf в карточку
#   python run_speed109.py [повторов]    - замер, варианты поочередно
import csv
import os
import subprocess
import sys
import time
from datetime import datetime

import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
RES = os.path.join(TASK, "Тестирование", "Замеры")
EPF = os.path.join(TASK, "Тестирование", "T431_109.epf")
DU = 'Srvr="localhost";Ref="WIM_DU";'
MO = 'Srvr="localhost";Ref="WIM_MO";'
CARD = "T431 Сверка TWR (стенд)"
# (вариант, размер пачки) для 2003 мандатов стенда: 1 вызов; пачки 3000 (1 пачка), 1000 (3), 500 (5), 250 (9)
VARIANTS = [("один вызов", 0), ("пачки", 3000), ("пачки", 1000), ("пачки", 500), ("пачки", 250)]


def register(c):
    card = c.Справочники.ДополнительныеОтчетыИОбработки.НайтиПоНаименованию(CARD, True)
    obj = card.ПолучитьОбъект()
    obj.ХранилищеОбработки = c.NewObject("ХранилищеЗначения", c.NewObject("ДвоичныеДанные", EPF))
    obj.Версия = "1.09-T431"
    obj.ИмяФайла = "T431_109.epf"
    obj.Записать()
    print("карточка обновлена", c.XMLСтрока(card))


def run_job(c, card, keys, variant, size):
    p = c.NewObject("Структура")
    p.Вставить("Вариант", variant)
    p.Вставить("СтрокаСоединенияМО", MO)
    p.Вставить("МандатыXML", ",".join(keys))
    p.Вставить("НачалоПериодаTWR", datetime(2026, 1, 1))
    p.Вставить("КонецПериода", datetime(2026, 10, 31))
    p.Вставить("РазмерПорции", size)
    jp = c.NewObject("Структура")
    jp.Вставить("ИмяМетода", "Т431_ЗамерСкорости109")
    jp.Вставить("ПараметрыВыполнения", p)
    jp.Вставить("ЭтоВнешняяОбработка", True)
    jp.Вставить("ИмяОбработки", "")
    jp.Вставить("ДополнительнаяОбработкаСсылка", card)
    rp = c.ДлительныеОперации.ПараметрыВыполненияВФоне(c.NewObject("УникальныйИдентификатор"))
    rp.НаименованиеФоновогоЗадания = f"T431 скорость {variant} {size}"
    rp.ОжидатьЗавершение = 0
    rp.ЗапуститьВФоне = True
    op = c.ДлительныеОперации.ВыполнитьВФоне("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", jp, rp)
    while True:
        job = c.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(op.ИдентификаторЗадания)
        if job.Состояние != c.СостояниеФоновогоЗадания.Активно:
            break
        time.sleep(1)
    if job.ИнформацияОбОшибке is not None:
        return None, "ОШИБКА " + c.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
    r = c.ПолучитьИзВременногоХранилища(op.АдресРезультата)
    return r, ""


def peak(path, t0, t1):
    best = 0
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if t0 <= float(r["t"]) <= t1 and r["ib"] == "WIM_DU" and r["app"] == "BackgroundJob":
            best = max(best, int(r["mem_current"]))
    return best


def main():
    c = win32com.client.Dispatch("V83.COMConnector").Connect(DU)
    if len(sys.argv) > 1 and sys.argv[1] == "register":
        register(c)
        return
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    os.makedirs(RES, exist_ok=True)
    keys = [l.strip() for l in open(os.path.join(HERE, "stand_mandates.txt"), encoding="utf-8") if l.strip()]
    card = c.Справочники.ДополнительныеОтчетыИОбработки.НайтиПоНаименованию(CARD, True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log = os.path.join(RES, f"memwatch_speed109_{stamp}.csv")
    watcher = subprocess.Popen([sys.executable, os.path.join(HERE, "memwatch.py"), log])
    time.sleep(3)
    lines = [f"Скорость 1.09 против одного вызова {stamp}: особая стратегия, мандатов {len(keys)}, "
             f"период 01.01.2026-31.10.2026, вводы-выводы есть"]
    try:
        for n in range(repeats):
            for variant, size in VARIANTS:
                t0 = time.time()
                r, err = run_job(c, card, keys, variant, size)
                time.sleep(1.5)
                mem = peak(log, t0, time.time()) / 2**20
                if r is None:
                    lines.append(f"прогон {n + 1}; {variant} {size}; {err}")
                else:
                    lines.append(f"прогон {n + 1}; {variant}; пачка {size or '-'}; пачек {r.Пачек}; "
                                 f"{r.Секунд:.1f} с; память {mem:.0f} МБ; мандатов {r.Мандатов}; "
                                 f"сумма {r.СуммаДоходности:.6f}")
                print(lines[-1], flush=True)
    finally:
        watcher.kill()
    with open(os.path.join(RES, f"итог_speed109_{stamp}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
