import win32com.client, sys
sys.stdout.reconfigure(encoding="utf-8")
c = win32com.client.Dispatch("V83.COMConnector").Connect('Srvr="localhost";Ref="WIM_MO";')
for variant in ("load", "plain"):
    m = c.Справочники.Мандаты.СоздатьЭлемент()
    m.Наименование = "T431 проба"
    if variant == "load":
        m.ОбменДанными.Загрузка = True
    m.УстановитьНовыйКод()
    print(variant, "код", m.Код)
    try:
        m.Записать(); print(variant, "OK", c.XMLСтрока(m.Ссылка)); m.Удалить()
    except Exception as e:
        print(variant, "ERR", e.excepinfo[2] if hasattr(e, "excepinfo") and e.excepinfo else e)
        msgs = c.ПолучитьСообщенияПользователю(True)
        for i in range(msgs.Количество()): print("  msg:", msgs.Получить(i).Текст)
