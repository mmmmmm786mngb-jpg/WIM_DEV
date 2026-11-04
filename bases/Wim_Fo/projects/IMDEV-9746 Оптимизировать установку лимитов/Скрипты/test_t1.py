# -*- coding: utf-8 -*-
"""IMDEV-9746. Обработка сравнения 1.16 и 1.17 для Т-1: сборка и проверочный прогон на разработческой ФО.

    python test_t1.py build            УСКОРЕНО_1_17/*.epf -> макет Версия117; Т-1/src_test -> Т-1/ТестРаспространенияЛимитовТ1.epf
    python test_t1.py dev <o|r> [запусков]   прогон теста на dev в фоновом задании с настройками стенда режима
                                       -> Тестирование/reports/test_t1_dev_<режим>_*.txt

Перед dev-прогоном: заглушка почты Тестирование/Стенд/mock_smtp.py, run_stand.py subs on (рабочие имена свойств стенда,
их находят подписки ВТБ_Прод). Рабочей обработке на время прогона записываются настройки стенда режима и возвращаются
исходные. После: run_stand.py subs off, run_stand.py restore.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
NAME = "ТестРаспространенияЛимитовТ1"
SRC = os.path.join(TASK, "Т-1", "src_test")
EPF = os.path.join(TASK, "Т-1", NAME + ".epf")
V117 = os.path.join(TASK, "УСКОРЕНО_1_17", "внРаспространениеПравилСОдногоКлиентаНаСписокКлиентов.epf")
TEMPLATE = os.path.join(SRC, NAME, "Templates", "Версия117", "Ext", "Template.bin")
REGISTRY = r"C:\1c\Cursor_1c\WIM_DEV\.v8-project.json"
BUILD = os.path.join(os.path.expanduser("~"), ".claude", "skills", "epf-build", "scripts", "epf-build.ps1")
V8 = r"C:\Program Files\1cv8\8.3.27.2214\bin"
STORAGE_KEY = "IMDEV-9746 тест распространения Т-1"


def build():
    shutil.copyfile(V117, TEMPLATE)
    with open(REGISTRY, encoding="utf-8-sig") as f:
        db = next(d for d in json.load(f)["databases"] if d["id"] == "wim_fo")
    cmd = ["powershell.exe", "-NoProfile", "-File", BUILD, "-V8Path", V8, "-InfoBaseServer", db["server"],
           "-InfoBaseRef", db["ref"], "-SourceFile", os.path.join(SRC, NAME + ".xml"), "-OutputFile", EPF,
           "-Checks", "off"]
    if db.get("user"):
        cmd += ["-UserName", db["user"], "-Password", db.get("password", "")]
    result = subprocess.run(cmd, capture_output=True)
    print((result.stdout or b"").decode("utf-8", errors="replace").strip()[-600:])
    sys.exit(result.returncode)


def register(fo):
    """Регистрирует обработку теста в справочнике дополнительных обработок dev (для запуска в фоновом задании)."""
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


def run_test(fo, ref, runs, per_run):
    params = fo.NewObject("Структура")
    params.Вставить("КодыКлиентов", "")
    params.Вставить("Запусков", runs)
    params.Вставить("КлиентовНаЗапуск", per_run)
    task = fo.NewObject("Структура")
    task.Вставить("ИмяОбработки", NAME)
    task.Вставить("ИмяМетода", "ВыполнитьТестВФоне")
    task.Вставить("ПараметрыВыполнения", params)
    task.Вставить("ЭтоВнешняяОбработка", True)
    task.Вставить("ДополнительнаяОбработкаСсылка", ref)
    fo.ХранилищеОбщихНастроек.Удалить(STORAGE_KEY, "Лог", fo.ИмяПользователя())
    address = fo.ПоместитьВоВременноеХранилище(None, fo.NewObject("УникальныйИдентификатор"))
    args = fo.NewObject("Массив")
    args.Добавить(task)
    args.Добавить(address)
    job = fo.ФоновыеЗадания.Выполнить("ДлительныеОперации.ВыполнитьПроцедуруМодуляОбъектаОбработки", args, "",
                                      "IMDEV-9746 тест распространения")
    uid = job.УникальныйИдентификатор
    while fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid).Состояние == fo.СостояниеФоновогоЗадания.Активно:
        time.sleep(1)
    job = fo.ФоновыеЗадания.НайтиПоУникальномуИдентификатору(uid)
    if job.ИнформацияОбОшибке is not None:
        return "ОШИБКА ЗАДАНИЯ: " + fo.ПодробноеПредставлениеОшибки(job.ИнформацияОбОшибке)
    for _ in range(5):
        text = fo.ПолучитьИзВременногоХранилища(address) or fo.ХранилищеОбщихНастроек.Загрузить(STORAGE_KEY, "Лог")
        if text:
            return text
        time.sleep(1)
    return "задание завершилось без лога"


def dev(mode, runs):
    sys.path.insert(0, os.path.join(TASK, "Тестирование", "Стенд"))
    import run_stand as rs  # noqa: E402
    fo = rs.connect("wim_fo")
    state = rs.load_state()
    rs.ensure_conditions(fo, state)
    settings = rs.settings(fo, mode, rs.properties(fo), rs.mailing(fo))
    item = rs.work_item(fo).ПолучитьОбъект()
    saved = fo.XMLСтрока(item.ХранилищеНастроек)
    item.ХранилищеНастроек = fo.NewObject("ХранилищеЗначения", settings)
    item.ОбменДанными.Загрузка = True
    item.Записать()
    try:
        ref = register(fo)
        started = time.time()
        text = run_test(fo, ref, runs, 1 if mode == "o" else 2)
    finally:
        item = rs.work_item(fo).ПолучитьОбъект()
        item.ХранилищеНастроек = fo.XMLЗначение(fo.NewObject("ОписаниеТипов", "ХранилищеЗначения").Типы().Получить(0), saved)
        item.ОбменДанными.Загрузка = True
        item.Записать()
        print("рабочей обработке возвращены исходные настройки")
    out = os.path.join(TASK, "Тестирование", "reports",
                       "test_t1_dev_%s_%s.txt" % (mode, datetime.datetime.now().strftime("%Y%m%d_%H%M")))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print("тест %.1f с, строк %d, файл %s" % (time.time() - started, text.count("\n") + 1, out))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build()
    else:
        dev(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
