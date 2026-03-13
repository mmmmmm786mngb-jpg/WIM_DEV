&НаКлиенте
Процедура Обновить(Команда)
	ОбновитьНаСервере();
КонецПроцедуры

&НаСервере
Процедура ОбновитьНаСервере()
	
	Объект.СписокОТС.Очистить();
	Если Не ЗначениеЗаполнено(Объект.ДатаНачала) Или Не ЗначениеЗаполнено(Объект.ДатаОкончания) Тогда Возврат; КонецЕсли;
	
	Если Объект.ТестовыйРежим Тогда
	
		SQL = Новый COMОбъект("ADODB.Connection");
		ServerName = "SMSK02DB56U\DBMAMSBL03";
		DSN = "Quik";
		UID = "rates_view";
		PWD = "DgsFaVqDSZQhORL7NrCm";
		ConnectString = "Provider=SQLOLEDB;" + "Data Source=" + ServerName + ";Initial Catalog=" + DSN + ";UID=" + UID + ";PWD=" + PWD;
		SQL.ConnectionString = ConnectString;
		SQL.ConnectionTimeOut = 15;
		SQL.CommandTimeout = 30;
		
	Иначе	
	
		SQL = Новый COMОбъект("ADODB.Connection");
		ServerName = "AMDBRATES\DBMVTBAM01";
		DSN = "Quik";
		UID = "rates_view";
		PWD = "DgsFaVqDSZQhORL7NrCm";
		ConnectString = "Provider=SQLOLEDB;" + "Data Source=" + ServerName + ";Initial Catalog=" + DSN + ";UID=" + UID + ";PWD=" + PWD;
		SQL.ConnectionString = ConnectString;
		SQL.ConnectionTimeOut = 15;
		SQL.CommandTimeout = 30;
		
	КонецЕсли;	
	
	Попытка
		SQL.Open();
	Исключение 
		Сообщить("Не могу подсоединиться к базе. " + ОписаниеОшибки());
		Возврат;
	КонецПопытки;
		
	RecordSet = Новый COMОбъект("ADODB.RecordSet");
	SQLText = "
	|select (case isnull(q.kod_klienta,'') when '' then q.CustodyAccount else q.kod_klienta end) + '_' + q.Currency as kod_klienta, 
	|       q.data,    
	|       convert(varchar(20),q.order_id) as order_id,
	|       q.Mandate,
	|       q.instrument_code,
	|       q.instrument_short,
	|       q.kolichestvo,
	|       q.objem,
	|       q.Couterparty,
	|       q.otc_as_agents,
	|       q.SettleType,
	|       q.kommentary
	|  from SdelkiQuik as q
	| where q.class_code = 'OTC'
	|   and q.data between '"+Формат(Объект.ДатаНачала,"ДФ=yyyy-MM-dd")+"' and '"+Формат(Объект.ДатаОкончания,"ДФ=yyyy-MM-dd")+"'
	| order by q.data, kod_klienta
	|";
	RecordSet = SQL.Execute(SQLText);
	Сообщить(SQLText);
	Пока RecordSet.EOF() = 0 Цикл
		НовСтр = Объект.СписокОТС.Добавить();
		НовСтр.КодКлиента = RecordSet.Fields("kod_klienta").Value;
		НовСтр.ДатаСделки = RecordSet.Fields("data").Value;
		НовСтр.НомерСделки = RecordSet.Fields("order_id").Value;
		НовСтр.Мандата = RecordSet.Fields("Mandate").Value;
		НовСтр.АктивКод = RecordSet.Fields("instrument_code").Value;
		НовСтр.АктивИмя = RecordSet.Fields("instrument_short").Value;
		НовСтр.Количество = RecordSet.Fields("kolichestvo").Value;
		НовСтр.Сумма = RecordSet.Fields("objem").Value;
		НовСтр.КодБрокера = RecordSet.Fields("Couterparty").Value;
		НовСтр.ОТСчерезБрокера = RecordSet.Fields("otc_as_agents").Value;
		НовСтр.ПлатежныеУсловия = RecordSet.Fields("SettleType").Value;
		НовСтр.Комментарий = RecordSet.Fields("kommentary").Value;
		RecordSet.MoveNext();
	КонецЦикла;
	
КонецПроцедуры
