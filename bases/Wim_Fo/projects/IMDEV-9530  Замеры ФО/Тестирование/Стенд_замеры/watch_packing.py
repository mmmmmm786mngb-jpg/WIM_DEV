# -*- coding: utf-8 -*-
"""Наблюдение за упаковкой данных на разработческой ФО.

Шаг КэшВмОписания.Упаковать после архивации удаляет подробные кэши архивированных проверок наборами записей по
каждому вместилищу и регистру. Основной объем - регистр КэшВмДетально (миллионы записей), поэтому считаются
только два больших регистра, каждый своим запросом: общий запрос по всем КэшВм* выполняется дольше интервала.
Строка печатается на каждом опросе: записи, удалено с начала, скорость, оценка оставшегося времени до объема
проверок моложе суток (они не архивируются и остаются). Наблюдение заканчивается вместе с заданием упаковки.

    python watch_packing.py [интервал_секунд]   (по умолчанию 600)
"""
import datetime
import glob
import sys
import time

STAND = glob.glob(r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО')[0]
sys.path.insert(0, STAND)
from stand_common import connect, query  # noqa: E402

REGISTERS = ["КэшВмДетально", "КэшВмКратко"]


def count(fo, name):
    return int(query(fo, f"ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Н ИЗ РегистрСведений.{name} КАК Т")[0]["Н"])


def kept_rows(fo):
    """Записи КэшВмДетально проверок, которые упаковка оставляет (не в архиве)."""
    return int(query(fo, """
        ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Н
        ИЗ РегистрСведений.КэшВмДетально КАК Т
        ГДЕ Т.Вместилище В (ВЫБРАТЬ О.Вместилище ИЗ РегистрСведений.КэшВмОписания КАК О ГДЕ НЕ О.Архив)""")[0]["Н"])


def packing_active(fo):
    jobs = fo.ФоновыеЗадания.ПолучитьФоновыеЗадания(
        fo.NewObject("Структура", "Состояние", fo.СостояниеФоновогоЗадания.Активно))
    return any("УпаковкаДанных" in jobs.Получить(i).ИмяМетода for i in range(jobs.Количество()))


def now():
    return datetime.datetime.now().strftime("%H:%M:%S")


def main():
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    fo = connect("wim_fo")
    started = time.time()
    first = {n: count(fo, n) for n in REGISTERS}
    kept = kept_rows(fo)
    print(now(), "старт:", ", ".join(f"{k} {v:,}".replace(",", " ") for k, v in first.items()),
          f"; остается после упаковки (проверки моложе суток) КэшВмДетально {kept:,}".replace(",", " "), flush=True)
    while True:
        time.sleep(interval)
        try:
            current = {n: count(fo, n) for n in REGISTERS}
            active = packing_active(fo)
        except Exception as error:  # noqa: BLE001 - сбой одного опроса не прерывает наблюдение
            print(now(), "ОШИБКА опроса:", str(error)[:200], flush=True)
            continue
        minutes = (time.time() - started) / 60
        deleted = first["КэшВмДетально"] - current["КэшВмДетально"]
        rate = deleted / minutes if minutes else 0
        left = max(current["КэшВмДетально"] - kept, 0)
        eta = f"{left / rate:.0f} мин" if rate > 0 else "-"
        print(now(), ", ".join(f"{k} {v:,}".replace(",", " ") for k, v in current.items()),
              f"| удалено КэшВмДетально {deleted:,}, {rate:,.0f} в минуту, осталось удалить {left:,}, оценка {eta}".replace(",", " "),
              "| задание активно" if active else "| задание завершено", flush=True)
        if not active:
            break


if __name__ == "__main__":
    main()
