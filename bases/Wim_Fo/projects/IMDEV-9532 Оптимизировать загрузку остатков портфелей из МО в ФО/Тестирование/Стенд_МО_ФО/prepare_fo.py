# -*- coding: utf-8 -*-
"""Подготовка ФО (WIN_FO_server) для стенда выгрузки МО -> ФО.

Шаги (по умолчанию все, можно указать выборочно аргументами):
  props         свойства доп. сведений «Лимиты ...», по которым обмен пишет флаги;
  places        места хранения T9532_DEPO и T9532_BANK с внешними кодами, как их ищет обмен;
  shares        акции T9532 Акция 1..3 (копии существующей) и их активы с внешними кодами T9532_SH1..3;
  portfolios    портфели T9532_0001..N (копии существующего портфеля) с внешними кодами мандатов МО;
  subportfolios субпортфели по счетам мандатов МО (код счета и UUID счета в МО как внешний код);
  epf           регистрация обработок «Удаление блокировок», «Перерасчет РСА», «Операции после обмена»,
                их настройки и константа «Операции после обмена»;
  log           включение лога веб-сервиса Avancore (по нему считаются длительности вызовов).
Исходные значения констант и настроек сохраняются в state.json, их восстанавливает cleanup.py.
Рассылка перерасчета РСА не настраивается: тест писем не отправляет.
"""
import os
import shutil
import sys
import tempfile
import time

from stand_common import (PREFIX, N_PORTFOLIOS, SHARES, EPF_DIR, FLAG_KEYS, DATE_RECALC, FO_EPFS, connect, query,
                          mandate_code, share_code, load_state, save_state)


def find_ref(conn, text_, params=None):
    rows = query(conn, text_, params)
    return rows[0]["Ссылка"] if rows else None


def remember_original(fo, state, key, getter):
    """Сохраняет исходное значение в state один раз (строкой внутреннего формата 1С)."""
    originals = state.setdefault("originals", {})
    if key not in originals:
        originals[key] = fo.ЗначениеВСтрокуВнутр(getter())
        save_state(state)


def step_props(fo, state):
    created = state.setdefault("created_properties", [])
    for name in FLAG_KEYS + [DATE_RECALC]:
        ref = find_ref(fo, "ВЫБРАТЬ Св.Ссылка КАК Ссылка ИЗ ПланВидовХарактеристик.ДополнительныеРеквизитыИСведения КАК Св "
                           "ГДЕ Св.Наименование = &Имя", {"Имя": name})
        if ref is not None:
            print(f"  свойство есть: {name}")
            continue
        obj = fo.ПланыВидовХарактеристик.ДополнительныеРеквизитыИСведения.СоздатьЭлемент()
        obj.Наименование = name
        obj.Заголовок = name
        obj.Имя = name.replace(" ", "_")
        obj.ТипЗначения = fo.NewObject("ОписаниеТипов", "Дата" if name == DATE_RECALC else "Булево")
        obj.ЭтоДополнительноеСведение = True
        obj.Доступен = True
        obj.Виден = True
        obj.Записать()
        created.append(name)
        save_state(state)
        print(f"  создано свойство: {name}")


def step_places(fo, state):
    """Место хранения ФО - обертка над счетом (Объект обязателен). Счет создается копией существующего,
    место хранения к нему создает подписка «СинхронизацияМестХранения», ему проставляется внешний код.
    В разработческой ФО нет счетов депо, поэтому оба места хранения - на копиях банковского счета: вид счета
    при записи фактической позиции не проверяется, а место хранения ЦБ здесь не обязательно."""
    for code, name, catalog in [(f"{PREFIX}_DEPO", f"{PREFIX} Счет депо", "БанковскиеСчета"),
                                (f"{PREFIX}_BANK", f"{PREFIX} Банковский счет", "БанковскиеСчета")]:
        ref = find_ref(fo, "ВЫБРАТЬ Мх.Ссылка КАК Ссылка ИЗ Справочник.МестаХранения КАК Мх ГДЕ Мх.ВнешнийКод = &Код",
                       {"Код": code})
        if ref is not None:
            print(f"  место хранения есть: {code}")
            continue
        sample = find_ref(fo, f"ВЫБРАТЬ ПЕРВЫЕ 1 Сч.Ссылка КАК Ссылка ИЗ Справочник.{catalog} КАК Сч "
                              f"ГДЕ НЕ Сч.ПометкаУдаления И НЕ Сч.Наименование ПОДОБНО &Маска УПОРЯДОЧИТЬ ПО Сч.Наименование",
                          {"Маска": PREFIX + "%"})
        if sample is None:
            raise SystemExit(f"В ФО нет ни одного элемента {catalog} для копирования")
        account = sample.Скопировать()
        account.Наименование = name
        account.Записать()
        place = find_ref(fo, "ВЫБРАТЬ Мх.Ссылка КАК Ссылка ИЗ Справочник.МестаХранения КАК Мх ГДЕ Мх.Объект = &Объект",
                         {"Объект": account.Ссылка})
        if place is None:
            obj = fo.Справочники.МестаХранения.СоздатьЭлемент()
            obj.Объект = account.Ссылка
        else:
            obj = place.ПолучитьОбъект()
        obj.Наименование = name
        obj.ВнешнийКод = code
        obj.Записать()
        print(f"  создано место хранения: {code} ({catalog})")


def ensure_currency_asset(fo):
    rub = find_ref(fo, "ВЫБРАТЬ Вал.Ссылка КАК Ссылка ИЗ Справочник.Валюты КАК Вал ГДЕ Вал.Код = &Код", {"Код": "643"})
    if rub is None:
        raise SystemExit("В ФО нет валюты с кодом 643")
    asset = find_ref(fo, "ВЫБРАТЬ Ак.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК Ак ГДЕ Ак.Объект = &Объект", {"Объект": rub})
    if asset is None:
        obj = fo.Справочники.Активы.СоздатьЭлемент()
        obj.Наименование = "RUB"
        obj.Объект = rub
        obj.ВидАктива = fo.ПланыВидовХарактеристик.ВидыАктивов.Валюты
        obj.Записать()
        print("  создан актив для валюты RUB")
    else:
        print("  актив для валюты RUB есть")


def step_shares(fo, state):
    ensure_currency_asset(fo)
    sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 Ак.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК Ак "
                          "ГДЕ НЕ Ак.ПометкаУдаления И НЕ Ак.Наименование ПОДОБНО &Маска УПОРЯДОЧИТЬ ПО Ак.Наименование",
                      {"Маска": PREFIX + "%"})
    if sample is None:
        raise SystemExit("В ФО нет ни одной акции для копирования")
    for k in range(1, SHARES + 1):
        code = share_code(k)
        asset = find_ref(fo, "ВЫБРАТЬ Ак.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК Ак ГДЕ Ак.ВнешнийКод = &Код", {"Код": code})
        if asset is not None:
            print(f"  актив есть: {code}")
            continue
        # Актив ФО при записи берет внешний код из объекта (акции), поэтому код ставится на акцию.
        existing = find_ref(fo, "ВЫБРАТЬ Ак.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК Ак ГДЕ Ак.Наименование = &Имя",
                            {"Имя": f"{PREFIX} Акция {k}"})
        share = existing.ПолучитьОбъект() if existing is not None else sample.Скопировать()
        share.Наименование = f"{PREFIX} Акция {k}"
        share.ВнешнийКод = code
        share.ISIN = ""
        share.НомерГосРегистрацииВыпуска = ""
        share.БиржиЛистинга.Очистить()
        share.Записать()
        asset = find_ref(fo, "ВЫБРАТЬ Ак.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК Ак ГДЕ Ак.Объект = &Объект",
                         {"Объект": share.Ссылка})
        if asset is None:
            obj = fo.Справочники.Активы.СоздатьЭлемент()
            obj.Объект = share.Ссылка
            obj.ВидАктива = share.ВидАктива
        else:
            obj = asset.ПолучитьОбъект()
        obj.Наименование = f"{PREFIX} Акция {k}"
        obj.ВнешнийКод = code
        obj.ISIN = ""
        obj.Записать()
        print(f"  создана акция и актив: {code}")


def step_portfolios(fo, state):
    existing = {r["Код"] for r in query(fo, "ВЫБРАТЬ П.ВнешнийКод КАК Код ИЗ Справочник.Портфели КАК П "
                                            "ГДЕ П.ВнешнийКод ПОДОБНО &Маска", {"Маска": PREFIX + "%"})}
    sample = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П "
                          "ГДЕ НЕ П.ПометкаУдаления И НЕ П.Предопределенный И П.ВнешнийКод = \"\" "
                          "УПОРЯДОЧИТЬ ПО П.Наименование")
    if sample is None:
        raise SystemExit("В ФО нет портфеля для копирования")
    created = 0
    started = time.perf_counter()
    for i in range(1, N_PORTFOLIOS + 1):
        code = mandate_code(i)
        if code in existing:
            continue
        obj = sample.Скопировать()
        obj.Наименование = f"{PREFIX} Портфель {i:04d}"
        obj.ВнешнийКод = code
        obj.НомерДоговора = code
        obj.Записать()
        created += 1
        if created % 50 == 0:
            print(f"  портфелей создано {created}, {time.perf_counter() - started:.0f} с")
    print(f"  портфелей создано {created}, всего тестовых {len(existing) + created}")


def step_subportfolios(fo, state):
    mo = connect("wim_mo")
    accounts = query(mo, "ВЫБРАТЬ С.КодСчета КАК Код, С.Владелец.КодМандата КАК Мандат, С.Ссылка КАК Ссылка "
                         "ИЗ Справочник.СчетаМандатов КАК С ГДЕ С.КодСчета ПОДОБНО &Маска", {"Маска": PREFIX + "%"})
    if not accounts:
        raise SystemExit("В МО нет тестовых счетов мандатов: сначала prepare_mo.py")
    uuids = {a["Код"]: mo.XMLСтрока(a["Ссылка"]) for a in accounts}
    portfolios = {r["Код"]: r["Ссылка"] for r in query(
        fo, "ВЫБРАТЬ П.ВнешнийКод КАК Код, П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П ГДЕ П.ВнешнийКод ПОДОБНО &Маска",
        {"Маска": PREFIX + "%"})}
    existing = {r["Код"] for r in query(fo, "ВЫБРАТЬ С.КодСчета КАК Код ИЗ Справочник.Субпортфели КАК С "
                                            "ГДЕ С.КодСчета ПОДОБНО &Маска", {"Маска": PREFIX + "%"})}
    created = 0
    for account in accounts:
        code = account["Код"]
        if code in existing:
            continue
        obj = fo.Справочники.Субпортфели.СоздатьЭлемент()
        obj.Наименование = code
        obj.КодСчета = code
        obj.ВнешнийКод = uuids[code]
        obj.Портфель = portfolios.get(account["Мандат"])
        obj.Записать()
        created += 1
    print(f"  субпортфелей создано {created}, всего тестовых {len(existing) + created}")


def register_epf(fo, object_name, settings):
    path = os.path.join(EPF_DIR, object_name + ".epf")
    if not os.path.exists(path):
        raise SystemExit(f"Нет собранной обработки {path}: сначала build_fo_epf.ps1")
    tmp = os.path.join(tempfile.gettempdir(), object_name + ".epf")
    shutil.copyfile(path, tmp)
    processor = fo.ВнешниеОбработки.Создать(tmp, False)
    info = processor.СведенияОВнешнейОбработке()
    ref = find_ref(fo, "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
                       "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления", {"Имя": object_name})
    item = ref.ПолучитьОбъект() if ref is not None else fo.Справочники.ДополнительныеОтчетыИОбработки.СоздатьЭлемент()
    item.Наименование = processor.Метаданные().Представление()
    item.ИмяОбъекта = object_name
    item.ИмяФайла = object_name + ".epf"
    item.Версия = info.Версия
    item.БезопасныйРежим = info.БезопасныйРежим
    item.Вид = fo.Перечисления.ВидыДополнительныхОтчетовИОбработок.ДополнительнаяОбработка
    item.Публикация = fo.Перечисления.ВариантыПубликацииДополнительныхОтчетовИОбработок.Используется
    item.ХранилищеОбработки = fo.NewObject("ХранилищеЗначения", fo.NewObject("ДвоичныеДанные", path))
    item.Команды.Очистить()
    for i in range(info.Команды.Количество()):
        src = info.Команды.Получить(i)
        cmd = item.Команды.Добавить()
        cmd.Идентификатор = src.Идентификатор
        cmd.Представление = src.Представление
        cmd.ВариантЗапуска = fo.Перечисления.СпособыВызоваДополнительныхОбработок.ОткрытиеФормы
    if settings is not None:
        item.ХранилищеНастроек = fo.NewObject("ХранилищеЗначения", settings)
    item.ОбменДанными.Загрузка = True
    item.Записать()
    os.remove(tmp)
    print(f"  зарегистрирована обработка {object_name} версии {info.Версия}")
    return item.Ссылка


def property_ref(fo, name):
    return find_ref(fo, "ВЫБРАТЬ Св.Ссылка КАК Ссылка ИЗ ПланВидовХарактеристик.ДополнительныеРеквизитыИСведения КАК Св "
                        "ГДЕ Св.Наименование = &Имя", {"Имя": name})


def step_epf(fo, state):
    remember_original(fo, state, "ОперацииПослеОбмена", lambda: fo.Константы.ОперацииПослеОбмена.Получить())
    remember_original(fo, state, "ИспользоватьДополнительныеОтчетыИОбработки",
                      lambda: fo.Константы.ИспользоватьДополнительныеОтчетыИОбработки.Получить())
    if not fo.Константы.ИспользоватьДополнительныеОтчетыИОбработки.Получить():
        fo.Константы.ИспользоватьДополнительныеОтчетыИОбработки.Установить(True)
        print("  включена функциональная опция дополнительных обработок")

    refs = {}
    refs["внУдалениеБлокировок"] = register_epf(fo, "внУдалениеБлокировок", None)

    default_assets = fo.NewObject("СписокЗначений")
    for row in query(fo, "ВЫБРАТЬ Ак.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК Ак ГДЕ Ак.ВнешнийКод ПОДОБНО &Маска",
                     {"Маска": PREFIX + "_SH%"}):
        default_assets.Добавить(row["Ссылка"])
    exchange = find_ref(fo, "ВЫБРАТЬ ПЕРВЫЕ 1 Б.Ссылка КАК Ссылка ИЗ Справочник.Биржи КАК Б ГДЕ НЕ Б.ПометкаУдаления")
    recalc_settings = fo.NewObject("Структура")
    recalc_settings.Вставить("ПризнакДляПерерасчетаПортфеля", property_ref(fo, FLAG_KEYS[1]))
    recalc_settings.Вставить("ПризнакПозицияВыгружена", property_ref(fo, FLAG_KEYS[0]))
    recalc_settings.Вставить("ПризнакЕстьОшибкиВыгрузкиПозиции", property_ref(fo, FLAG_KEYS[2]))
    recalc_settings.Вставить("ПризнакДатаПересчетаРСА", property_ref(fo, DATE_RECALC))
    recalc_settings.Вставить("СписокДефолтныхАктивов", default_assets)
    recalc_settings.Вставить("СписокПортфелейИсключаемыхИзПересчета", fo.NewObject("СписокЗначений"))
    if exchange is not None:
        recalc_settings.Вставить("БиржаКотировок", exchange)
    refs["внПерерасчетСтоимостиФактическойПозицииИ_РСА_СЧА"] = register_epf(
        fo, "внПерерасчетСтоимостиФактическойПозицииИ_РСА_СЧА", recalc_settings)

    after_settings = fo.NewObject("Структура")
    after_settings.Вставить("ОбработкаПерерасчетаСтоимости", refs["внПерерасчетСтоимостиФактическойПозицииИ_РСА_СЧА"])
    after_settings.Вставить("ОбработкаУдаленияБлокировок", refs["внУдалениеБлокировок"])
    refs["внОперацииПослеОбмена"] = register_epf(fo, "внОперацииПослеОбмена", after_settings)

    fo.Константы.ОперацииПослеОбмена.Установить(refs["внОперацииПослеОбмена"])
    state["registered_epf"] = list(FO_EPFS)
    save_state(state)
    print("  константа «Операции после обмена» заполнена")


def step_log(fo, state):
    remember_original(fo, state, "НастройкиСобытийВнешнихСервисов",
                      lambda: fo.Константы.НастройкиСобытийВнешнихСервисов.Получить())
    manager = fo.РегистрыСведений.СобытияВнешнихСервисов
    settings = manager.НовыеНастройкиСобытий()
    settings.Периодичность.Использовать = True
    manager.ЗаписатьНастройкиСобытий("Avancore", settings)
    print("  лог веб-сервиса Avancore включен")


STEPS = {"props": step_props, "places": step_places, "shares": step_shares, "portfolios": step_portfolios,
         "subportfolios": step_subportfolios, "epf": step_epf, "log": step_log}


def main():
    wanted = sys.argv[1:] or list(STEPS)
    fo = connect("wim_fo")
    state = load_state()
    for name in wanted:
        print(f"ФО: {name}")
        STEPS[name](fo, state)
    print("ФО: готово")


if __name__ == "__main__":
    main()
