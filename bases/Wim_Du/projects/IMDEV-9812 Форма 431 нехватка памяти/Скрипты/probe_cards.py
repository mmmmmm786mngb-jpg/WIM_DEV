import win32com.client, sys
sys.stdout.reconfigure(encoding="utf-8")
c = win32com.client.Dispatch("V83.COMConnector").Connect('Srvr="localhost";Ref="WIM_DU";')
q = c.NewObject("Запрос")
q.Текст = "ВЫБРАТЬ Д.Наименование КАК Наим, Д.ИмяОбъекта КАК ИмяОб, Д.Версия КАК Вер, Д.ПометкаУдаления КАК Пом ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д ГДЕ Д.ИмяОбъекта ПОДОБНО \"%0420431%\" ИЛИ Д.Наименование ПОДОБНО \"T431%\""
s = q.Выполнить().Выбрать()
while s.Следующий(): print(s.Наим, "|", s.ИмяОб, "|", s.Вер, "|", s.Пом)
print("done")
