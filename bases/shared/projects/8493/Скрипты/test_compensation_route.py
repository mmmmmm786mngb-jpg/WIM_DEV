# -*- coding: utf-8 -*-
"""
Проверка маршрута создания документа компенсации в ФИН.
Сценарии повторяют условия модуля обработки ДУ версии 1.22.
"""
from pathlib import Path

ROOT = Path(r"c:\1c\Cursor_1c\WORK")
DU_OBJECT = ROOT / r"Wim_Du\SRC\epf\внРасторжениеДоговоровРозничногоДУ_epf\внРасторжениеДоговоровРозничногоДУ\Ext\ObjectModule.bsl"
DU_FORM = ROOT / r"Wim_Du\SRC\epf\внРасторжениеДоговоровРозничногоДУ_epf\внРасторжениеДоговоровРозничногоДУ\Forms\Форма\Ext\Form\Module.bsl"
DU_FORM_XML = ROOT / r"Wim_Du\SRC\epf\внРасторжениеДоговоровРозничногоДУ_epf\внРасторжениеДоговоровРозничногоДУ\Forms\Форма\Ext\Form.xml"
FIN_WS = ROOT / r"WIM_FIn\src\cf\WebServices\NDFL\Ext\Module.bsl"
OUT = Path(__file__).with_name("_route_test_result.txt")


def slice_proc(text, signature, end_token):
    start = text.find(signature)
    if start < 0:
        raise RuntimeError("not found: " + signature)
    end = text.find(end_token, start + len(signature))
    return text[start:end]


def fin_called(entry, cooling, mat_benefit, papers_sold, turnover, ndfl_done):
    """Повторяет развилку обработки ДУ. True, если уходит вызов createMatBenefits."""
    if entry != "button_nachitat":
        return False
    if not (papers_sold and turnover):
        return False
    if not (mat_benefit > 0 and cooling):
        return False
    if ndfl_done:
        return False
    return True


def main():
    lines = []
    object_text = DU_OBJECT.read_text(encoding="utf-8")
    form_text = DU_FORM.read_text(encoding="utf-8")
    form_xml = DU_FORM_XML.read_text(encoding="utf-8")
    ws_text = FIN_WS.read_text(encoding="utf-8")

    command_proc = slice_proc(object_text, "Процедура ВыполнитьКоманду(", "КонецПроцедуры")
    calc_proc = slice_proc(object_text, "Процедура ОбработкаДоговоровКРасторжению(", "КонецПроцедуры")
    form_proc = slice_proc(form_text, "Процедура ВыполнитьРасторжениеНаСервере(", "КонецПроцедуры")

    checks = [
        ("Фоновое ВыполнитьКоманду не вызывает расчет договоров", "ОбработкаДоговоровКРасторжению" not in command_proc),
        ("Фоновое ВыполнитьКоманду не вызывает веб-сервис", "ОтправитьМатВыгодуФИН" not in command_proc and "createMatBenefits" not in command_proc),
        ("Кнопка формы вызывает расчет договоров", "ОбработкаДоговоровКРасторжению()" in form_proc),
        ("Расчет договоров вызывает веб-сервис", "ОтправитьМатВыгодуФИН" in calc_proc),
        ("Веб-сервис ФИН создает документ компенсации", "СоздатьДокументНачисленияМатериальнойВыгоды" in ws_text),
        ("Веб-сервис проводит документ в той же транзакции, что и НДФЛ", "НачатьТранзакцию" in ws_text and "СоздатьНачислениеНДФЛ" in ws_text and "РежимЗаписиДокумента.Проведение" in ws_text),
        ("Подпись кнопки на форме ДУ - НАЧИТАТЬ", "<v8:content>НАЧИТАТЬ</v8:content>" in form_xml),
    ]
    failed = 0
    lines.append("SOURCE CHECKS")
    for title, ok in checks:
        lines.append(("OK" if ok else "FAIL") + " | " + title)
        if not ok:
            failed += 1

    scenarios = [
        ("Фоновое: данные из ДО", "schedule_do", True, 1000, True, True, False, False),
        ("Фоновое: расчет материальной выгоды", "schedule_mat", True, 1000, True, True, False, False),
        ("Раздел Закрытие периода, форма ФИН", "fin_form", True, 1000, True, True, False, False),
        ("Кнопка НАЧИТАТЬ, все условия есть", "button_nachitat", True, 1269.71, True, True, False, True),
        ("Кнопка НАЧИТАТЬ, нет периода охлаждения", "button_nachitat", False, 1269.71, True, True, False, False),
        ("Кнопка НАЧИТАТЬ, компенсация 0", "button_nachitat", True, 0, True, True, False, False),
        ("Кнопка НАЧИТАТЬ, бумаги не проданы", "button_nachitat", True, 1000, False, True, False, False),
        ("Кнопка НАЧИТАТЬ, нет оборота бумаг", "button_nachitat", True, 1000, True, False, False, False),
        ("Кнопка НАЧИТАТЬ, НДФЛ в ДУ уже начислен", "button_nachitat", True, 1000, True, True, True, False),
    ]
    lines.append("SCENARIOS")
    for name, entry, cooling, mat, papers, turnover, ndfl, expected in scenarios:
        actual = fin_called(entry, cooling, mat, papers, turnover, ndfl)
        ok = actual == expected
        if not ok:
            failed += 1
        lines.append(
            "%s | %s | call_fin=%s | expected=%s"
            % ("OK" if ok else "FAIL", name, actual, expected)
        )
    lines.append("FAILED %s" % failed)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
