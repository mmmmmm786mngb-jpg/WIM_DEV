import sys,os,time
sys.stdout.reconfigure(encoding="utf-8")
import stand
c=stand.connect()
ref=stand.doc_by_number(c,"T0000")
o=ref.ПолучитьОбъект(); t=time.time(); o.ЗаполнитьОтчет(); print("fill",round(time.time()-t,1)); t=time.time(); o.ОбменДанными.Загрузка=True; o.Записать(); print("write",round(time.time()-t,1))
print("Наим",o.НаименованиеПрофУчастника,"| ФИО",o.ФИООтветственного,"| Р7",o.Раздел7.Количество(),"| Р1",o.Раздел1.Количество())
sys.stdout.flush(); os._exit(0)
