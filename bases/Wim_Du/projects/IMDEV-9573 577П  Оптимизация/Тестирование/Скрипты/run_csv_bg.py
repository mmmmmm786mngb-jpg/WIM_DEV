# -*- coding: utf-8 -*-
"""Стенд: выгрузка CSV 577-П фоновым заданием, как из формы обработки: ДлительныеОперации.ВыполнитьВФоне
с процедурой ВыполнитьПроцедуруМодуляОбъектаОбработки, обработка из файла (ПутьEPF).

python run_csv_bg.py <номер> [reg]
reg - обработка из справочника ДополнительныеОтчетыИОбработки (register_epf.py), как у пользователей;
без reg - из файла epf.
Печатает и пишет в ../Результаты/csv_<номер>/фон.txt: начало и конец задания по данным платформы,
состояние, ошибку, итог обработки. Память вызова снимать параллельно sessmem.py (сеанс BackgroundJob).
"""
import os
import sys
import time

import stand

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
NEW_EPF = os.path.join(TASK, "csv_РабочийКод", "СформироватьВыгрузкуCSVПоток.epf")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number = sys.argv[1]
    base = os.path.join(TASK, "Тестирование", "Результаты", f"csv_{number}")
    out = os.path.join(base, "bg") + "\\"
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))

    conn = stand.connect()
    ref = stand.doc_by_number(conn, number)
    method_params = conn.NewObject("Структура")
    method_params.Вставить("ДокументСсылка", ref)
    method_params.Вставить("Каталог", out)
    registered = len(sys.argv) > 2 and sys.argv[2] == "reg"
    reg_ref = None
    if registered:
        reg_ref = conn.Справочники.ДополнительныеОтчетыИОбработки.НайтиПоНаименованию(
            "T9573 Выгрузка CSV 577-П поток (стенд)", True)
    else:
        method_params.Вставить("ПутьEPF", NEW_EPF)
    job_params = conn.NewObject("Структура")
    job_params.Вставить("ИмяМетода", "ВыгрузитьВФоне")
    job_params.Вставить("ПараметрыВыполнения", method_params)
    job_params.Вставить("ЭтоВнешняяОбработка", True)
    job_params.Вставить("ИмяОбработки", "" if registered else NEW_EPF)
    job_params.Вставить("ДополнительнаяОбработкаСсылка", reg_ref)
    run_params = conn.ДлительныеОперации.ПараметрыВыполненияВФоне(conn.NewObject("УникальныйИдентификатор"))
    run_params.НаименованиеФоновогоЗадания = f"Выгрузка 577-П в CSV {number} (стенд)"
    run_params.ОжидатьЗавершение = 0
    run_params.ЗапуститьВФоне = True

    t0 = time.time()
    operation = conn.ДлительныеОперации.ВыполнитьВФоне(
        "ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", job_params, run_params)
    print("операция: статус", operation.Статус, "задание", operation.ИдентификаторЗадания,
          "ошибка", operation.КраткоеПредставлениеОшибки if operation.Свойство("КраткоеПредставлениеОшибки") else "")
    job_id = operation.ИдентификаторЗадания
    if job_id is None:
        return
    while True:
        job = conn.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(job_id)
        state = conn.String(job.Состояние)
        if job.Состояние != conn.СостояниеФоновогоЗадания.Активно:
            break
        time.sleep(2)
    lines = [
        f"Фоновое задание {number} ({'из справочника' if registered else 'из файла'}): состояние {state}",
        f"  начало {conn.String(job.Начало)}, конец {conn.String(job.Конец)}, по часам скрипта {time.time() - t0:.1f} s",
    ]
    if job.ИнформацияОбОшибке is not None:
        lines.append("  ошибка: " + conn.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке))
    else:
        result = conn.ПолучитьИзВременногоХранилища(operation.АдресРезультата)
        lines.append("  " + (result.Описание.splitlines()[0] if result is not None else "результат в хранилище пуст"))
        messages = job.ПолучитьСообщенияПользователю(False)
        for i in range(messages.Количество()):
            lines.append("  сообщение: " + messages.Получить(i).Текст)
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(base, "фон.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M ") + text + "\n\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
