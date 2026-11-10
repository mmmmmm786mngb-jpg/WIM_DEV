# Замер памяти расчета доходности стратегии: 1.07 против 1.08 на стенде dev WIM_DU + dev WIM_MO.
# Каждый вариант - отдельное фоновое задание БСП в WIM_DU (карточка "T431 Сверка TWR (стенд)", процедура
# Т431_Замер), как серверный вызов заполнения. Параллельно memwatch.py снимает MemoryCurrent сеансов
# по данным агента кластера. Пик MemoryCurrent сеанса фонового задания = пик памяти вызова в ДУ.
# python run_memory.py [повторов]; варианты поочередно, чтобы кэш СУБД был в равных условиях
import csv
import os
import subprocess
import sys
import time
from datetime import datetime

import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), "Тестирование", "Замеры")
DU = 'Srvr="localhost";Ref="WIM_DU";'
MO = 'Srvr="localhost";Ref="WIM_MO";'
CARD = "T431 Сверка TWR (стенд)"
VARIANTS = [("1.07", None), ("1.08", None)]  # None: размер пачки из РазмерПорцииМандатовTWR (500)


def run_job(c, card, keys, variant, size):
    p = c.NewObject("Структура")
    p.Вставить("Вариант", variant)
    p.Вставить("СтрокаСоединенияМО", MO)
    p.Вставить("МандатыXML", ",".join(keys))
    p.Вставить("НачалоПериодаTWR", datetime(2026, 1, 1))
    p.Вставить("КонецПериода", datetime(2026, 10, 31, 23, 59, 59))
    p.Вставить("ФлагОсобыеСтратегии", False)
    p.Вставить("РазмерПорции", size)
    jp = c.NewObject("Структура")
    jp.Вставить("ИмяМетода", "Т431_Замер")
    jp.Вставить("ПараметрыВыполнения", p)
    jp.Вставить("ЭтоВнешняяОбработка", True)
    jp.Вставить("ИмяОбработки", "")
    jp.Вставить("ДополнительнаяОбработкаСсылка", card)
    rp = c.ДлительныеОперации.ПараметрыВыполненияВФоне(c.NewObject("УникальныйИдентификатор"))
    rp.НаименованиеФоновогоЗадания = f"T431 замер {variant} пачка {size or 500}"
    rp.ОжидатьЗавершение = 0
    rp.ЗапуститьВФоне = True
    op = c.ДлительныеОперации.ВыполнитьВФоне("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", jp, rp)
    job = None
    while True:
        job = c.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(op.ИдентификаторЗадания)
        if job.Состояние != c.СостояниеФоновогоЗадания.Активно:
            break
        time.sleep(1)
    if job.ИнформацияОбОшибке is not None:
        return "ОШИБКА " + c.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
    r = c.ПолучитьИзВременногоХранилища(op.АдресРезультата)
    return f"мандатов {r.Мандатов}, строк TWR {r.СтрокTWR}, сумма доходности {r.СуммаДоходности:.6f}, {r.Секунд:.1f} с, пачек {r.Пачек} (построчно {r.ПачекПоСтрокам})"


def peaks(path, t0, t1):
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if t0 <= float(r["t"]) <= t1]
    out = {}
    for r in rows:
        k = (r["ib"], r["app"], r["session"])
        out[k] = max(out.get(k, 0), int(r["mem_current"]))
    return {k: v for k, v in out.items() if v > 0}


def main():
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    os.makedirs(RES, exist_ok=True)
    keys = [l.strip() for l in open(os.path.join(HERE, "stand_mandates.txt"), encoding="utf-8") if l.strip()]
    c = win32com.client.Dispatch("V83.COMConnector").Connect(DU)
    card = c.Справочники.ДополнительныеОтчетыИОбработки.НайтиПоНаименованию(CARD, True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log = os.path.join(RES, f"memwatch_{stamp}.csv")
    watcher = subprocess.Popen([sys.executable, os.path.join(HERE, "memwatch.py"), log])
    time.sleep(3)
    lines = [f"Замер {stamp}: мандатов в списке {len(keys)}, период 01.01.2026-31.10.2026"]
    try:
        for n in range(repeats):
            for variant, size in VARIANTS:
                t0 = time.time()
                res = run_job(c, card, keys, variant, size)
                time.sleep(1.5)
                t1 = time.time()
                pk = peaks(log, t0, t1)
                bg = max((v for (ib, app, s), v in pk.items() if ib == "WIM_DU" and app == "BackgroundJob"), default=0)
                mo = max((v for (ib, app, s), v in pk.items() if ib == "WIM_MO"), default=0)
                lines.append(f"{variant} пачка {size or 'по умолчанию'}: пик вызова ДУ (фоновое) {bg / 2**20:.1f} МБ, "
                             f"пик вызова МО {mo / 2**20:.1f} МБ; {res}")
                print(lines[-1], flush=True)
    finally:
        watcher.kill()
    with open(os.path.join(RES, f"итог_{stamp}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)

