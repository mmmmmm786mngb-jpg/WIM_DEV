# Повторяет ЗаполнитьОтчет по документу T0000 и создает недостающие предопределенные элементы,
# на которые падают запросы разделов. Созданное пишется в ../Результаты/created_predefined.txt (для очистки).
import sys, os, re, time
sys.stdout.reconfigure(encoding="utf-8")
import stand
c = stand.connect()
log = os.path.join(stand.RES, "created_predefined.txt"); os.makedirs(stand.RES, exist_ok=True)
for attempt in range(30):
    o = stand.doc_by_number(c, "T0000").ПолучитьОбъект()
    try:
        t = time.time(); o.ЗаполнитьОтчет(); print("fill OK", round(time.time() - t, 1), "s"); break
    except Exception as e:
        msg = str(e)
        m = re.search(r"(Справочник|ПланВидовХарактеристик|ПланСчетов|ПланВидовРасчета)\.(\w+)\.(\w+)\. Предопределенный элемент отсутствует", msg)
        if not m:
            print("OTHER", msg[:800]); break
        kind, mgr, name = m.groups()
        coll = {"Справочник": c.Справочники, "ПланВидовХарактеристик": c.ПланыВидовХарактеристик,
                "ПланСчетов": c.ПланыСчетов, "ПланВидовРасчета": c.ПланыВидовРасчета}[kind]
        manager = getattr(coll, mgr)
        item = manager.СоздатьЭлемент() if kind != "ПланСчетов" else manager.СоздатьСчет()
        item.ИмяПредопределенныхДанных = name
        try:
            item.Наименование = name
        except Exception:
            pass
        if kind == "ПланСчетов":
            item.Код = name
        item.ОбменДанными.Загрузка = True
        item.Записать()
        line = f"{kind}.{mgr}.{name}\t{c.String(item.Ссылка.УникальныйИдентификатор())}"
        print("created", line)
        open(log, "a", encoding="utf-8").write(line + "\n")
sys.stdout.flush(); os._exit(0)
