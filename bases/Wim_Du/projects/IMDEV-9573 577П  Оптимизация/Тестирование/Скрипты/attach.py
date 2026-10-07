import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import stand
c = stand.connect()
t = stand.query(c, """ВЫБРАТЬ Ф.Наименование КАК Имя, Ф.ДатаСоздания КАК Создан, Ф.Размер КАК Размер, Ф.ПометкаУдаления КАК Пометка
ИЗ Справочник.ХранилищеПрисоединенныхФайлов КАК Ф ГДЕ Ф.ВладелецФайла = &Д УПОРЯДОЧИТЬ ПО Ф.ДатаСоздания""", Д=stand.doc_by_number(c, sys.argv[1]))
for r in stand.rows(c, t, ["Имя", "Создан", "Размер", "Пометка"]):
    print(r["Имя"], c.String(r["Создан"]), int(r["Размер"]), r["Пометка"])
sys.stdout.flush(); os._exit(0)
