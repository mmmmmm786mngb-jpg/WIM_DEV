# -*- coding: utf-8 -*-
"""Подготовка UI-теста 6.11 / 1.20 в тонком клиенте dev WIM_DU.

Выписку в форме загрузки пользователь получает кнопкой "Прочитать" с флажком "Тестовый режим": обработка
читает ответ банка из своего макета ПримерОтвета. Для стенда собирается копия 6.11, у которой отличается
только этот макет; модули и формы - файлы src_6_11 без изменений (проверяется командой build).

python ui_stand.py build <A|B>       - макет выписки, копия src_6_11, сборка на dev-базе, карточка выписки T8856
python ui_stand.py data <сценарий>   - тестовые начисления / поручения сценария (vuk6, vuk120, mismatch, vvod)
python ui_stand.py check <сценарий>  - что создано по данным сценария
python ui_stand.py measures <минут>  - записи ЗамерыВремени за последние N минут
Строка соединения - WIM_DU_CONN, учетная запись для сборки берется из нее же.
"""
import datetime as dt
import filecmp
import os
import re
import shutil
import subprocess
import sys

os.environ.setdefault("T8856_VARIANT", "v20")
import stand  # noqa: E402
import run  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(stand.EPF_DIR, "src_6_11")
OUT = os.path.join(stand.TASK, "Тестирование", "Обработки", "stand_6_11")
BIC = "044525187"
KS = "30101810700000000187"
DAY = run.DAY

SCEN = {
    # индексы договоров стенда и сумма начисления
    "vuk6": ([i for i in range(401, 407)], 410.0),
    "vuk120": ([i for i in range(300, 420)], 100.0),
    "vuk500": ([i for i in range(10, 510)], 100.0),
    "mismatch": ([i for i in range(401, 407)], 410.0),
}


def account(number):
    return (f"<ns0:НомерСчета>{number}</ns0:НомерСчета><ns0:Банк><ns0:БИК>{BIC}</ns0:БИК>"
            f"<ns0:КорСчет>{KS}</ns0:КорСчет></ns0:Банк>")


def payment(number, amount, payer, receiver, purpose):
    d = DAY.isoformat()
    return f"""
            <ns0:ПлатежныеДокументы>
               <ns0:Операция>Платежное поручение</ns0:Операция>
               <ns0:Дата>{d}</ns0:Дата>
               <ns0:Номер>{number}</ns0:Номер>
               <ns0:Сумма>{amount:.2f}</ns0:Сумма>
               <ns0:ДатаПоступления>{d}</ns0:ДатаПоступления>
               <ns0:ПлательщикСчет>{account(payer)}</ns0:ПлательщикСчет>
               <ns0:ПлательщикБИК>{BIC}</ns0:ПлательщикБИК>
               <ns0:ПолучательСчет>{account(receiver)}</ns0:ПолучательСчет>
               <ns0:ПолучательБИК>{BIC}</ns0:ПолучательБИК>
               <ns0:НазначениеПлатежа>{purpose}</ns0:НазначениеПлатежа>
               <ns0:ПлательщикИНН>7700000000</ns0:ПлательщикИНН>
               <ns0:Плательщик>T8856 плательщик</ns0:Плательщик>
               <ns0:ПлательщикБанк><ns0:БИК>{BIC}</ns0:БИК><ns0:КорСчет>{KS}</ns0:КорСчет></ns0:ПлательщикБанк>
               <ns0:ПолучательИНН>7700000000</ns0:ПолучательИНН>
               <ns0:Получатель>T8856 получатель</ns0:Получатель>
               <ns0:ПолучательБанк><ns0:БИК>{BIC}</ns0:БИК><ns0:КорСчет>{KS}</ns0:КорСчет></ns0:ПолучательБанк>
               <ns0:ВидПлатежа/>
               <ns0:ВидОплаты>01</ns0:ВидОплаты>
            </ns0:ПлатежныеДокументы>"""


def statement_xml(kind, vuk_amount=2460.0):
    if kind == "A":
        rows = [payment("5200", vuk_amount, stand.ACC_ERS, stand.ACC_UK, run.VUK_TEXT)]
        income, outcome = 0.0, vuk_amount
    else:
        rows = [payment("6200", 1500.0, stand.ACC_UK, stand.ACC_ERS, run.IN_TEXT)]
        income, outcome = 1500.0, 0.0
    d = DAY.isoformat()
    return f"""      <ns0:Корень xmlns:ns0="http://www.avancore.ru/bank_statements">
         <ns0:Выписки>
            <ns0:ДатаСоздания>{d}</ns0:ДатаСоздания>
            <ns0:ВремяСоздания>09:00:00</ns0:ВремяСоздания>
            <ns0:ДатаНачала>{d}</ns0:ДатаНачала>
            <ns0:ДатаКонца>{d}</ns0:ДатаКонца>
            <ns0:БанковскийСчет>{account(stand.ACC_ERS)}</ns0:БанковскийСчет>
            <ns0:НачальныйОстаток>100000.00</ns0:НачальныйОстаток>
            <ns0:ВсегоПоступило>{income:.2f}</ns0:ВсегоПоступило>
            <ns0:ВсегоСписано>{outcome:.2f}</ns0:ВсегоСписано>
            <ns0:КонечныйОстаток>{100000 + income - outcome:.2f}</ns0:КонечныйОстаток>{''.join(rows)}
         </ns0:Выписки>
      </ns0:Корень>
"""


def conn_parts():
    cs = os.environ["WIM_DU_CONN"]
    usr = re.search(r'Usr="([^"]*)"', cs).group(1)
    pwd = re.search(r'Pwd="([^"]*)"', cs).group(1)
    return usr, pwd


def cmd_build(kind):
    target = os.path.join(OUT, kind)
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(SRC, target)
    tpl = os.path.join(target, "ЗагрузкаВыписок", "Templates", "ПримерОтвета", "Ext", "Template.txt")
    with open(tpl, "rb") as f:
        bom = f.read(3) == b"\xef\xbb\xbf"
    with open(tpl, "w", encoding="utf-8-sig" if bom else "utf-8", newline="\r\n") as f:
        f.write(statement_xml(kind))
    # модули и формы копии совпадают с src_6_11, отличается только макет ПримерОтвета
    diff = filecmp.dircmp(SRC, target)
    changed = []

    def walk(d, rel=""):
        changed.extend(os.path.join(rel, x) for x in d.diff_files)
        for name, sub in d.subdirs.items():
            walk(sub, os.path.join(rel, name))
    walk(diff)
    print("отличия от src_6_11:", changed)
    usr, pwd = conn_parts()
    epf = os.path.join(OUT, f"stand_6_11_{kind}.epf")
    ps = ["powershell.exe", "-NoProfile", "-File", os.path.expanduser("~/.claude/skills/epf-build/scripts/epf-build.ps1"),
          "-V8Path", r"C:\Program Files\1cv8\8.3.27.2214\bin", "-InfoBaseServer", "localhost", "-InfoBaseRef", "WIM_DU",
          "-UserName", usr, "-Password", pwd, "-SourceFile", os.path.join(target, "ЗагрузкаВыписок.xml"),
          "-OutputFile", epf, "-Checks", "off"]
    res = subprocess.run(ps, capture_output=True, text=True, encoding="cp866", errors="replace")
    print("сборка:", "ok" if os.path.exists(epf) else "ОШИБКА", res.stdout.strip().splitlines()[-1:] if res.stdout else "")
    c = stand.connect()
    stand.register_epf(c, stand.CARD_609, "ЗагрузкаВыписок", epf, "6.11")
    stand.register_epf(c, stand.CARD_118, "ПоступленияНаРасчетныйСчет_РозничноеДУ", stand.EPF_118, "1.20")
    print("карточка выписки ->", epf, "| карточка поступлений ->", stand.EPF_118)


def cmd_data(scen):
    c = stand.connect()
    run.retire_old(c)
    stand.cmd_acc928(c, "1")
    if scen == "vvod":
        ref = run.make_input_order(c, 20, 1500.0)
        print("поручение ввода:", c.String(ref))
        return
    idx, amount = SCEN[scen]
    acc = run.make_accruals(c, "ui_" + scen, [(i, amount, DAY) for i in idx])
    print(f"начислений {len(acc)} по {amount} = {len(acc) * amount:.2f}")


def cmd_check(scen):
    c = stand.connect()
    if scen == "vvod":
        run.report_receipts(c, [20])
        return
    t = stand.query(c, "ВЫБРАТЬ Н.Ссылка КАК Ссылка ИЗ Документ.НачислениеВознаграждения КАК Н ГДЕ Н.Комментарий = &К "
                       "И НЕ Н.ПометкаУдаления", К="T8856 ui_" + scen)
    acc = [t.Получить(i).Ссылка for i in range(t.Количество())]
    run.summary_writeoffs(c, acc)


def cmd_measures(minutes):
    c = stand.connect()
    run.measurement_rows(c, dt.datetime.utcnow() - dt.timedelta(minutes=minutes))


def cmd_mock(kind, vuk_amount=2460.0):
    """Выписка, которую заглушка сервиса (mock_bank.py) вернет на следующее нажатие "Прочитать"."""
    mock = os.path.join(HERE, "mock")
    os.makedirs(mock, exist_ok=True)
    for k in ("A", "B"):
        with open(os.path.join(mock, f"statement_{k}.xml"), "w", encoding="utf-8") as f:
            f.write(statement_xml(k, vuk_amount))
    with open(os.path.join(mock, "current.txt"), "w", encoding="utf-8") as f:
        f.write(kind)
    print("заглушка вернет выписку", kind, "сумма строки ВУК", vuk_amount)


def cmd_cards():
    """Карточки T8856: выписка - поставляемая 6.11, поступления - 1.20 (файлы из Обработки без изменений)."""
    c = stand.connect()
    stand.register_epf(c, stand.CARD_609, "ЗагрузкаВыписок", stand.EPF_609, "6.11")
    stand.register_epf(c, stand.CARD_118, "ПоступленияНаРасчетныйСчет_РозничноеДУ", stand.EPF_118, "1.20")
    print("карточка выписки ->", stand.EPF_609)
    print("карточка поступлений ->", stand.EPF_118)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "mock":
        cmd_mock(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 2460.0)
    elif cmd == "cards":
        cmd_cards()
    elif cmd == "build":
        cmd_build(sys.argv[2])
    elif cmd == "data":
        cmd_data(sys.argv[2])
    elif cmd == "check":
        cmd_check(sys.argv[2])
    elif cmd == "measures":
        cmd_measures(int(sys.argv[2]))
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)

