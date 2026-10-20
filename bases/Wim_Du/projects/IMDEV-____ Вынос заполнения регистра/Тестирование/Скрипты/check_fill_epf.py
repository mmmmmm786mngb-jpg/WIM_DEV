"""Проверка обработки ЗаполнениеИсторииКвал на dev-базе WIM_DU с данными стенда T_KVAL.

1. Регистр заполняется вендорским обработчиком ОбновитьДо1_5_30_0 (через СтендКвал), снимок A.
2. Обработка заполнения со сверкой: ожидается полное совпадение, снимок после = A.
3. Регистр портится (удаляется одна запись, добавляется запись Ложь), снова прогон со сверкой:
   ожидается 1 запись "нет в прежнем" и 1 "нет в новом", снимок после = A.
4. Прогон без сверки: снимок после = A.
В базе меняется только регистр ИсторияСтатусаЦБДляКвалИнвестора (на dev в нем только записи стенда).
"""
import datetime as dt
import pathlib
import sys

import win32com.client

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILL_EPF = ROOT / "Обработки" / "ЗаполнениеИсторииКвал.epf"
STAND_EPF = ROOT / "Обработки" / "СтендКвал.epf"
CONN = 'Srvr="localhost";Ref="WIM_DU";'


def open_epf(c, path):
    protection = c.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    protection.ПредупреждатьОбОпасныхДействиях = False
    return c.ВнешниеОбработки.Создать(str(path), False, protection)


def fill(fill_epf, check):
    state = fill_epf.НовоеСостояние()
    portions = 1
    while not fill_epf.ОбработатьПорцию(state, 100):
        portions += 1
    result = fill_epf.Завершить(state, check)
    print(result.Текст)
    print("порций:", portions)
    return result


def spoil_register(c):
    """Удаляет одну запись Истина и добавляет запись Ложь на новый день того же актива."""
    q = c.NewObject("Запрос")
    q.Текст = """ВЫБРАТЬ ПЕРВЫЕ 1 ИсторияСтатуса.Актив КАК Актив, ИсторияСтатуса.Период КАК Период
        ИЗ РегистрСведений.ИсторияСтатусаЦБДляКвалИнвестора КАК ИсторияСтатуса
        УПОРЯДОЧИТЬ ПО ИсторияСтатуса.Период УБЫВ"""
    row = q.Выполнить().Выгрузить().Получить(0)
    manager = c.РегистрыСведений.ИсторияСтатусаЦБДляКвалИнвестора.СоздатьМенеджерЗаписи()
    manager.Актив = row.Актив
    manager.Период = row.Период
    manager.Прочитать()
    manager.Удалить()
    extra = c.РегистрыСведений.ИсторияСтатусаЦБДляКвалИнвестора.СоздатьМенеджерЗаписи()
    extra.Актив = row.Актив
    extra.Период = row.Период + dt.timedelta(days=31)
    extra.ЦБДляКвалИнвестора = False
    extra.Записать()


def main():
    c = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    stand = open_epf(c, STAND_EPF)
    fill_epf = open_epf(c, FILL_EPF)
    ok = True

    if "--skip-vendor" in sys.argv:
        # Шаг 1 уже пройден: обработка дает регистр, равный вендорскому. Восстанавливаем его ею же.
        fill(fill_epf, False)
        snap_a = stand.СнимокРегистра()
        print("снимок A (восстановлен обработкой), записей:", snap_a.ЧислоЗаписей)
    else:
        stand.ОчиститьРегистр()
        print("обработчик вендора, мс:", stand.ПрогонОбработчика())
        snap_a = stand.СнимокРегистра()
        print("снимок A, записей:", snap_a.ЧислоЗаписей)

        print("\n--- 1. со сверкой на регистре вендора")
        r = fill(fill_epf, True)
        s = r.Сверка
        step_ok = (s.Прежних == snap_a.ЧислоЗаписей and s.Совпало == snap_a.ЧислоЗаписей
                   and s.ТолькоНовые == 0 and s.ТолькоПрежние == 0
                   and stand.СнимокРегистра().Записи == snap_a.Записи)
        print("шаг 1:", "OK" if step_ok else "РАСХОЖДЕНИЕ")
        ok &= step_ok

    print("\n--- 2. со сверкой на испорченном регистре")
    spoil_register(c)
    r = fill(fill_epf, True)
    s = r.Сверка
    step_ok = (s.ТолькоНовые == 1 and s.ТолькоПрежние == 1
               and stand.СнимокРегистра().Записи == snap_a.Записи)
    print("шаг 2:", "OK" if step_ok else "РАСХОЖДЕНИЕ")
    ok &= step_ok

    print("\n--- 3. без сверки")
    r = fill(fill_epf, False)
    step_ok = r.Сверка is None and stand.СнимокРегистра().Записи == snap_a.Записи
    print("шаг 3:", "OK" if step_ok else "РАСХОЖДЕНИЕ")
    ok &= step_ok

    print("\nИТОГ:", "OK" if ok else "РАСХОЖДЕНИЕ")


if __name__ == "__main__":
    main()
