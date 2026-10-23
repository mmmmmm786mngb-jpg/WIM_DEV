# -*- coding: utf-8 -*-
"""Стенд: серверная часть режима «Мой компьютер» обработки CSV 2.03 без формы.

python run_csv_client_mode.py <номер> [файлы через запятую, по умолчанию все]

Для каждого файла (R1-R11, затем sr_sved_purcb) вызывает ВыгрузитьВФоне с ИмяФайлаДляКлиента, как форма,
берет архив из результата (Архив), сохраняет и распаковывает его в ../Результаты/csv_<номер>/client.
Печатает время, размеры CSV и архива, источник строк; проверяет, что во временном каталоге сервера
не осталось каталогов csv577. Сравнение с эталоном - compare_csv.py.
"""
import glob
import os
import sys
import time
import zipfile

import stand

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.normpath(os.path.join(HERE, "..", ".."))
EPF = os.path.join(TASK, "csv_РабочийКод", "СформироватьВыгрузкуCSVПоток.epf")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number = sys.argv[1]
    files = [(f"R{n}.csv", f"Раздел{n}") for n in range(1, 12)] + [("sr_sved_purcb.csv", "")]
    if len(sys.argv) > 2:
        wanted = sys.argv[2].split(",")
        files = [f for f in files if f[0] in wanted]
    out = os.path.join(TASK, "Тестирование", "Результаты", f"csv_{number}", "client")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))

    conn = stand.connect()
    ref = stand.doc_by_number(conn, number)
    server_tmp = conn.КаталогВременныхФайлов()
    before = set(glob.glob(os.path.join(server_tmp, "*csv577*")))
    protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    processing = conn.ВнешниеОбработки.Создать(EPF, False, protection)
    form_id = conn.NewObject("УникальныйИдентификатор")
    counters = conn.NewObject("Структура")
    total_csv = total_zip = 0
    t_all = time.time()
    for file_name, section in files:
        params = conn.NewObject("Структура")
        params.Вставить("ДокументСсылка", ref)
        params.Вставить("ИмяФайлаДляКлиента", file_name)
        params.Вставить("ИмяРаздела", section)
        params.Вставить("СчетчикиРазделов", counters)
        address = conn.ПоместитьВоВременноеХранилище(None, form_id)
        t0 = time.time()
        processing.ВыгрузитьВФоне(params, address)
        t_server = time.time() - t0
        result = conn.ПолучитьИзВременногоХранилища(address)
        if section:
            counters.Вставить(section, result.КоличествоСтрок)
        zip_path = os.path.join(out, file_name + ".zip")
        result.Архив.Записать(zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            archive.extractall(out)
        os.remove(zip_path)
        total_csv += result.РазмерCSV
        total_zip += result.РазмерАрхива
        print(f"{file_name}: {result.Описание}; CSV {result.РазмерCSV:,} байт, архив {result.РазмерАрхива:,} "
              f"(в {result.РазмерCSV / max(result.РазмерАрхива, 1):.1f} раза), сервер {t_server:.1f} s, в архиве {names}")
    left = set(glob.glob(os.path.join(server_tmp, "*csv577*"))) - before
    print(f"Итого: CSV {total_csv:,} байт, архивы {total_zip:,} байт, {time.time() - t_all:.1f} s")
    print("Временные каталоги csv577 на сервере после выгрузки:", sorted(left) if left else "нет")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
