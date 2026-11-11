# Проверка обработки 0420431 на dev WIM_DU через COM.
# python -I com_check.py compile <epf>  - создать объект обработки (компиляция модуля объекта на сервере)
# python -I com_check.py extbases      - список внешних ИБ (подключения к МО) в dev ДУ
import sys
import win32com.client

CONN = 'Srvr="localhost";Ref="WIM_DU";'


def connect():
    return win32com.client.Dispatch("V83.COMConnector").Connect(CONN)


def main():
    cmd = sys.argv[1]
    c = connect()
    if cmd == "compile":
        path = sys.argv[2]
        try:
            obj = c.ВнешниеОбработки.Создать(path, False)
            info = obj.СведенияОВнешнейОбработке()
            print("OK compile; версия", info.Версия, "|", info.Наименование)
        except Exception as e:
            print("FAIL", e)
    elif cmd == "extbases":
        q = c.NewObject("Запрос")
        q.Текст = "ВЫБРАТЬ Ссылка, Наименование, ПометкаУдаления ИЗ Справочник.ВнешниеИнформационныеБазы"
        sel = q.Выполнить().Выбрать()
        while sel.Следующий():
            print(sel.Наименование, sel.ПометкаУдаления)


if __name__ == "__main__":
    main()
