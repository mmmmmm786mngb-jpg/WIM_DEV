# -*- coding: utf-8 -*-
"""IMDEV-9746. Сборка диагностики лимитов для Т-1 и ее проверочный прогон на разработческой ФО.

    python diag_t1.py build      Т-1/src -> Т-1/ДиагностикаЛимитовТ1.epf (против wim_fo, -Checks off)
    python diag_t1.py run [дней] [объект] сбор лога на dev через внешнее соединение -> Тестирование/reports/diag_dev_*.txt
"""
import datetime
import glob
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
NAME = "ДиагностикаЛимитовТ1"
EPF = os.path.join(TASK, "Т-1", NAME + ".epf")
REGISTRY = r"C:\1c\Cursor_1c\WIM_DEV\.v8-project.json"
BUILD = os.path.join(os.path.expanduser("~"), ".claude", "skills", "epf-build", "scripts", "epf-build.ps1")
V8 = r"C:\Program Files\1cv8\8.3.27.2214\bin"


def build():
    with open(REGISTRY, encoding="utf-8-sig") as f:
        db = next(d for d in json.load(f)["databases"] if d["id"] == "wim_fo")
    cmd = ["powershell.exe", "-NoProfile", "-File", BUILD, "-V8Path", V8, "-InfoBaseServer", db["server"],
           "-InfoBaseRef", db["ref"], "-SourceFile", os.path.join(TASK, "Т-1", "src", NAME + ".xml"),
           "-OutputFile", EPF, "-Checks", "off"]
    if db.get("user"):
        cmd += ["-UserName", db["user"], "-Password", db.get("password", "")]
    result = subprocess.run(cmd, capture_output=True)
    print((result.stdout or b"").decode("utf-8", errors="replace").strip()[-600:])
    sys.exit(result.returncode)


def register(fo):
    """Регистрирует диагностику в справочнике дополнительных обработок dev (для запуска в фоновом задании)."""
    q = fo.NewObject("Запрос")
    q.Текст = ("ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
               "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления")
    q.УстановитьПараметр("Имя", NAME)
    sel = q.Выполнить().Выбрать()
    item = sel.Ссылка.ПолучитьОбъект() if sel.Следующий() else fo.Справочники.ДополнительныеОтчетыИОбработки.СоздатьЭлемент()
    item.Наименование = "T9746 " + NAME
    item.ИмяОбъекта = NAME
    item.ИмяФайла = os.path.basename(EPF)
    item.БезопасныйРежим = False
    item.Вид = fo.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
    item.Публикация = fo.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    item.ХранилищеОбработки = fo.NewObject("ХранилищеЗначения", fo.NewObject("ДвоичныеДанные", EPF))
    item.ОбменДанными.Загрузка = True
    item.Записать()
    return item.Ссылка


def run_background(fo, days, object_name):
    """Сбор в фоновом задании: во внешнем соединении не компилируется модуль объекта справочника Лимиты."""
    ref = register(fo)
    params = fo.NewObject("Структура")
    params.Вставить("ДнейИстории", days)
    params.Вставить("ИмяОбъекта", object_name)
    task = fo.NewObject("Структура")
    task.Вставить("ИмяОбработки", NAME)
    task.Вставить("ИмяМетода", "СобратьЛогВФоне")
    task.Вставить("ПараметрыВыполнения", params)
    task.Вставить("ЭтоВнешняяОбработка", True)
    task.Вставить("ДополнительнаяОбработкаСсылка", ref)
    text = None
    for attempt in range(2):  # первый запуск после регистрации иногда без результата в хранилище
        address = fo.ПоместитьВоВременноеХранилище(None, fo.NewObject("УникальныйИдентификатор"))
        args = fo.NewObject("Массив")
        args.Добавить(task)
        args.Добавить(address)
        job = fo.ФоновыеЗадания.Выполнить("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", args, "",
                                          "IMDEV-9746 диагностика лимитов")
        uid = job.УникальныйИдентификатор
        while fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid).Состояние == fo.СостояниеФоновогоЗадания.Активно:
            time.sleep(0.5)
        job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
        if job.ИнформацияОбОшибке is not None:
            raise SystemExit(fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке))
        for _ in range(5):
            text = fo.ПолучитьИзВременногоХранилища(address)
            if text:
                return text
            time.sleep(1)
    raise SystemExit("задание завершилось без результата")


def run(days):
    sys.path.insert(0, glob.glob(r"C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО")[0])
    from stand_common import connect  # noqa: E402
    fo = connect("wim_fo")
    started = time.time()
    text = run_background(fo, days, sys.argv[3] if len(sys.argv) > 3 else "")
    out = os.path.join(TASK, "Тестирование", "reports", "diag_dev_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print("сбор %.1f с, строк %d, файл %s" % (time.time() - started, text.count("\n") + 1, out))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build()
    else:
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
